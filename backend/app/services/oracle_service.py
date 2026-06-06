"""预言机喂价与全局清算扫描服务。

本模块负责把显式喂价、风险扫描和清算执行串联起来；具体价格更新、
健康因子计算和清算金额计算仍复用各自的业务服务。
"""
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from app.models import db
from app.models.asset import VirtualAsset
from app.models.liquidation import Liquidation
from app.models.loan import Loan
from app.models.pledge import Pledge
from app.models.user import User
from app.services import (
    asset_service,
    interest_service,
    liquidation_service,
    risk_engine,
    simulation_service,
)
from app.services.protocol_config import MONEY_QUANT, parse_positive_decimal


WARNING_HF = Decimal("1.1500")
LIQUIDATABLE_HF = Decimal("1.0000")
MAX_LIQ_PASSES = 8


def _fmt_money(value):
    return str(Decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP))


def _candidate_user_ids():
    """返回存在活跃质押或未还债务的用户 ID，排序后保证扫描顺序稳定。"""
    pledge_rows = (
        Pledge.query.filter_by(pledge_status="active")
        .with_entities(Pledge.user_id)
        .distinct()
        .all()
    )
    loan_rows = (
        Loan.query.filter(Loan.repay_status != "paid")
        .with_entities(Loan.user_id)
        .distinct()
        .all()
    )
    return sorted({row[0] for row in pledge_rows + loan_rows})


def _settle_interest_for_users(user_ids):
    """在全局扫描前统一结息，保证风险快照与清算依据一致。"""
    if not user_ids:
        return
    now = datetime.now()
    for user_id in user_ids:
        interest_service.accrue_user_interest(user_id, now=now, commit=False)
    db.session.commit()


def _normalize_price_updates(price_updates):
    """校验并标准化喂价请求。"""
    if not isinstance(price_updates, list) or not price_updates:
        return None, "请提供要喂价的资产价格列表"

    normalized = []
    seen_asset_ids = set()
    for item in price_updates:
        if not isinstance(item, dict):
            return None, "价格更新项格式错误"

        raw_asset_id = item.get("asset_id")
        price_value = item.get("current_price", item.get("price"))
        if raw_asset_id is None or price_value is None:
            return None, "资产ID和价格不能为空"

        try:
            asset_id = int(raw_asset_id)
        except (TypeError, ValueError):
            return None, "资产ID必须为整数"

        if asset_id in seen_asset_ids:
            return None, "同一资产不能重复喂价"
        seen_asset_ids.add(asset_id)

        asset = db.session.get(VirtualAsset, asset_id)
        if not asset:
            return None, "资产不存在"

        price, err = parse_positive_decimal(price_value, "资产价格")
        if err:
            return None, err

        normalized.append({
            "asset_id": asset_id,
            "current_price": str(price),
        })

    return normalized, None


def _scan_at_risk(user_ids=None, threshold=WARNING_HF):
    """扫描高危账户，并按抵押物展开为前端表格行。"""
    at_risk = []
    for user_id in (user_ids if user_ids is not None else _candidate_user_ids()):
        snap = risk_engine.get_account_snapshot(user_id)
        if snap["total_debt"] <= 0 or snap["health_factor"] >= threshold:
            continue

        user = db.session.get(User, user_id)
        base = {
            "user_id": user_id,
            "user_name": user.user_name if user else str(user_id),
            "health_factor": str(snap["health_factor"]),
            "total_debt": str(snap["total_debt"]),
            "risk_level": snap["risk_level"],
            "will_liquidate": snap["health_factor"] < LIQUIDATABLE_HF,
        }

        if not snap["pledges"]:
            at_risk.append({
                **base,
                "pledge_id": None,
                "asset_id": None,
                "asset_name": "无抵押坏账",
                "asset_code": "BAD-DEBT",
                "pledge_amount": "0.0000",
                "current_value": "0.0000",
            })
            continue

        for row in snap["pledges"]:
            pledge = row["pledge"]
            asset = row["asset"]
            at_risk.append({
                **base,
                "pledge_id": pledge.pledge_id,
                "asset_id": asset.asset_id,
                "asset_name": asset.asset_name,
                "asset_code": asset.asset_code,
                "pledge_amount": str(pledge.pledge_amount),
                "current_value": _fmt_money(row["current_value"]),
            })

    at_risk.sort(
        key=lambda item: (
            Decimal(item["health_factor"]),
            item["user_id"],
            item["asset_code"],
            item["pledge_id"] or 0,
        )
    )
    return at_risk


def feed_prices(price_updates):
    """执行显式喂价，并对全系统低健康因子账户发起清算扫描。"""
    normalized_updates, err = _normalize_price_updates(price_updates)
    if err:
        return None, err

    try:
        updated_assets = asset_service.simulate_price_change(normalized_updates)
    except ValueError as e:
        return None, str(e)

    user_ids = _candidate_user_ids()
    _settle_interest_for_users(user_ids)
    at_risk_before = _scan_at_risk(user_ids=user_ids)

    executed = []
    for user_id in user_ids:
        for _ in range(MAX_LIQ_PASSES):
            snap = risk_engine.get_account_snapshot(user_id)
            if snap["total_debt"] <= 0 or snap["health_factor"] >= LIQUIDATABLE_HF:
                break
            if not snap["pledges"]:
                break

            target_row = sorted(
                snap["pledges"],
                key=lambda row: (-row["current_value"], row["pledge"].pledge_id),
            )[0]
            result, err = liquidation_service.execute_liquidation(
                target_row["pledge"].pledge_id, user_id
            )
            if err:
                break
            executed.append(result)

    overview = get_global_overview()
    return {
        "assets": updated_assets,
        "at_risk_before": at_risk_before,
        "liquidations": executed,
        "at_risk": overview["at_risk"],
        "stats": overview["stats"],
        "recent_liquidations": overview["recent_liquidations"],
    }, None


def get_global_overview():
    """获取全局风控看板所需的只读数据。"""
    stats = simulation_service.get_statistics()
    recent = []
    for liq in Liquidation.query.order_by(Liquidation.liquidation_time.desc()).limit(10).all():
        item = liq.to_dict()
        user = db.session.get(User, liq.user_id)
        item["user_name"] = user.user_name if user else str(liq.user_id)

        pledge = db.session.get(Pledge, liq.pledge_id)
        if pledge:
            asset = db.session.get(VirtualAsset, pledge.asset_id)
            if asset:
                item["asset_id"] = asset.asset_id
                item["asset_name"] = asset.asset_name
                item["asset_code"] = asset.asset_code
        recent.append(item)

    return {
        "stats": stats,
        "at_risk": _scan_at_risk(),
        "recent_liquidations": recent,
    }
