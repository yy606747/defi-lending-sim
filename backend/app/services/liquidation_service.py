"""清算管理服务

提供清算风险检测、清算执行和清算记录查询功能。
"""
from decimal import Decimal, ROUND_HALF_UP
from app.models import db
from app.models.pledge import Pledge
from app.models.liquidation import Liquidation
from app.models.asset import VirtualAsset
from app.services import interest_service, risk_engine
from app.services.protocol_config import (
    FULL_LIQUIDATION_CLOSE_FACTOR,
    FULL_LIQUIDATION_HEALTH_FACTOR,
    MONEY_QUANT,
    PARTIAL_LIQUIDATION_CLOSE_FACTOR,
    get_asset_param,
)


def check_liquidation_risk(user_id):
    """返回账户级清算风险，并附带每笔活跃质押的明细。

    每一行展示一笔质押物，但健康因子和风险等级都是账户级结果。
    """
    snapshot = risk_engine.get_account_snapshot(user_id)

    # 组装返回数据。每一行展示抵押物明细，但风险等级是账户级健康因子。
    result = []
    for row in snapshot["pledges"]:
        p = row["pledge"]
        asset = row["asset"]
        current_value = row["current_value"]
        item = p.to_dict()
        item["asset_name"] = asset.asset_name
        item["asset_code"] = asset.asset_code
        item["current_price"] = str(asset.current_price)
        item["current_value"] = str(
            current_value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        )
        item["collateral_ratio"] = str(snapshot["collateral_ratio"])
        item["health_factor"] = str(snapshot["health_factor"])
        item["risk_level"] = snapshot["risk_level"]
        item["total_debt"] = str(snapshot["total_debt"])
        item["borrow_power"] = str(snapshot["borrow_power"])
        item["available_to_borrow"] = str(snapshot["available_to_borrow"])
        result.append(item)
    
    return result


def execute_liquidation(pledge_id, user_id):
    """执行账户级部分清算。

    清算流程按账户健康因子判断是否可清算，再按 close factor 和清算罚金
    计算本轮偿还债务与扣押抵押物数量。
    """

    # 1. 基础存在性与状态检验
    pledge = Pledge.query.get(pledge_id)
    if not pledge or pledge.user_id != user_id:
        return None, "质押记录不存在或不属于该用户"
    if pledge.pledge_status != "active":
        return None, "该质押不处于活跃状态"

    # 2. 二次验证账户健康因子，确保合法触发清算
    interest_service.accrue_user_interest(user_id, commit=False)
    before = risk_engine.get_account_snapshot(user_id)
    total_debt = before["total_debt"]
    if total_debt <= Decimal("0"):
        db.session.rollback()
        return None, "用户无未还借款，无需清算"
    if before["health_factor"] >= Decimal("1"):
        db.session.rollback()
        return None, "当前账户健康因子未低于1，用户资金处于安全状态，拒绝清算"
    
    # 3. 准备执行清算数据
    asset = VirtualAsset.query.get(pledge.asset_id)
    if not asset:
        db.session.rollback()
        return None, "质押资产不存在，无法清算"
    liquidation_price = asset.current_price
    params = get_asset_param(asset.asset_code)
    liquidation_bonus = params["liquidation_bonus"]

    close_factor = (
        FULL_LIQUIDATION_CLOSE_FACTOR
        if before["health_factor"] <= FULL_LIQUIDATION_HEALTH_FACTOR
        else PARTIAL_LIQUIDATION_CLOSE_FACTOR
    )
    target_debt_to_cover = (total_debt * close_factor).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    max_debt_by_collateral = (
        pledge.pledge_amount * liquidation_price / (Decimal("1") + liquidation_bonus)
    ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    debt_repaid = min(target_debt_to_cover, max_debt_by_collateral, total_debt)
    if debt_repaid <= 0:
        db.session.rollback()
        return None, "该质押物价值不足，无法执行有效清算"

    collateral_seized = (
        debt_repaid * (Decimal("1") + liquidation_bonus) / liquidation_price
    ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    if collateral_seized > pledge.pledge_amount:
        collateral_seized = pledge.pledge_amount
    liquidation_amount = (collateral_seized * liquidation_price).quantize(
        MONEY_QUANT, rounding=ROUND_HALF_UP
    )

    # 4. 执行状态核心变更，异常时整体回滚。
    try:
        pledge.pledge_amount = (pledge.pledge_amount - collateral_seized).quantize(
            MONEY_QUANT, rounding=ROUND_HALF_UP
        )
        if pledge.pledge_amount <= 0:
            pledge.pledge_amount = Decimal("0")
            pledge.pledge_status = "liquidated"

        repay_result = interest_service.apply_debt_repayment(user_id, debt_repaid)
        after = risk_engine.sync_available_amounts(user_id)
        bad_debt = max(Decimal("0"), after["total_debt"] - after["total_collateral_value"])

        liq = Liquidation(
            user_id = user_id,
            pledge_id = pledge_id,
            liquidation_price = liquidation_price,
            liquidation_amount = liquidation_amount,
            liquidation_status="completed",
            debt_repaid=repay_result["used"].quantize(MONEY_QUANT, rounding=ROUND_HALF_UP),
            collateral_seized=collateral_seized,
            liquidation_bonus=liquidation_bonus,
            health_factor_before=before["health_factor"],
            health_factor_after=after["health_factor"],
            bad_debt=bad_debt.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP),
        )
        db.session.add(liq)
        db.session.commit()

        return liq.to_dict(), None

    except Exception as e:
        db.session.rollback()
        return None, f"执行清算时发生错误，已回滚: {str(e)}"


def get_liquidations(user_id):
    """获取用户所有清算记录，并补充资产名称。"""
    liqs = Liquidation.query.filter_by(user_id=user_id).order_by(Liquidation.liquidation_time.desc()).all()
    result = []
    for liq in liqs:
        item = liq.to_dict()
        pledge = Pledge.query.get(liq.pledge_id)
        if pledge:
            asset = VirtualAsset.query.get(pledge.asset_id)
            if asset:
                item["asset_name"] = asset.asset_name
        result.append(item)
    return result
