"""质押管理服务

提供质押的创建、查询和解锁功能。
"""
from decimal import Decimal, ROUND_HALF_UP
from app.models import db
from app.models.pledge import Pledge
from app.models.asset import VirtualAsset
from app.models.user import User
from app.services import interest_service, risk_engine
from app.services.protocol_config import get_asset_param, parse_positive_decimal


# 资产风控参数的展示视图，业务计算以协议配置和风险引擎为准。
ASSET_CONFIG = {
    code: {
        "LTV": params["ltv"],
        "LIQUIDATION_RATIO": (Decimal("1") / params["liquidation_threshold"]).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        ),
    }
    for code, params in {
        "USDT": get_asset_param("USDT"),
        "ETH": get_asset_param("ETH"),
        "BTC": get_asset_param("BTC"),
    }.items()
}
DEFAULT_CONFIG = {
    "LTV": get_asset_param("DEFAULT")["ltv"],
    "LIQUIDATION_RATIO": (Decimal("1") / get_asset_param("DEFAULT")["liquidation_threshold"]).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    ),
}



def create_pledge(user_id, asset_id, pledge_amount):
    """创建质押记录。

    业务流程：
    1. 校验用户、资产与质押数量；
    2. 按资产参数写入质押基础信息；
    3. 通过风险引擎同步账户级可借额度。
    """
    asset = VirtualAsset.query.get(asset_id)
    if not asset:
        return None, "资产不存在"

    if not User.query.get(user_id):
        return None, "用户不存在"

    pledge_amount, err = parse_positive_decimal(pledge_amount, "质押数量")
    if err:
        return None, err

    params = get_asset_param(asset.asset_code)
    pledge_rate = params["ltv"]
    
    # 首次写入展示额度；真实借款控制会在价格或债务变化后由风险引擎重算。
    pledge_value = pledge_amount * asset.current_price
    available_loan_amount = (pledge_value * pledge_rate).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    )

    try:
        pledge = Pledge(
            user_id=user_id,
            asset_id=asset_id,
            pledge_amount=pledge_amount,
            pledge_rate=pledge_rate,
            available_loan_amount=available_loan_amount,
            pledge_status="active",
        )
        db.session.add(pledge)
        db.session.flush()
        snapshot = risk_engine.sync_available_amounts(user_id)
        db.session.commit()
        
        # 统一转为 str 传给前端，防止精度丢失
        result = pledge.to_dict()
        result['pledge_amount'] = str(result['pledge_amount'])
        result['pledge_rate'] = str(result['pledge_rate'])
        result['available_loan_amount'] = str(
            risk_engine.get_pledge_available(snapshot, pledge.pledge_id)
        )
        result["health_factor"] = str(snapshot["health_factor"])
        result["available_to_borrow"] = str(snapshot["available_to_borrow"])
        return result, None

    except Exception as e:
        db.session.rollback()
        return None, f"数据库异常: {str(e)}"


def get_pledges(user_id):
    """获取用户所有质押记录，并补充资产信息和实时风险数据。"""
    snapshot = risk_engine.get_account_snapshot(user_id)

    pledges = Pledge.query.filter_by(user_id=user_id).all()
    result = []
    for p in pledges:
        item = p.to_dict()
        asset = VirtualAsset.query.get(p.asset_id)

        # 金额字段统一转为字符串，避免前端浮点数精度损失。
        item['pledge_amount'] = str(item['pledge_amount'])
        item['pledge_rate'] = str(item['pledge_rate'])
        item['available_loan_amount'] = str(
            risk_engine.get_pledge_available(snapshot, p.pledge_id)
            if p.pledge_status == "active"
            else Decimal("0.0000")
        )

        if asset:
            item["asset_name"] = asset.asset_name
            item["asset_code"] = asset.asset_code
            item["current_price"] = str(asset.current_price)
            current_value = p.pledge_amount * asset.current_price
            item["current_value"] = str(
                current_value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            )
            item["health_factor"] = str(snapshot["health_factor"])
            item["available_to_borrow"] = str(snapshot["available_to_borrow"])
        result.append(item)
    return result


def unlock_pledge(pledge_id, user_id):
    """解锁质押。

    校验规则：
    - 质押必须属于当前用户；
    - 质押状态必须为 active；
    - 解锁后剩余抵押物仍需覆盖当前债务。
    """
    pledge = Pledge.query.get(pledge_id)
    if not pledge or pledge.user_id != user_id:
        return None, "质押记录不存在"
    if pledge.pledge_status != "active":
        return None, "该质押状态不允许解锁"

    interest_service.accrue_user_interest(user_id, commit=False)
    after_unlock = risk_engine.get_account_snapshot(user_id, exclude_pledge_id=pledge_id)
    if after_unlock["total_debt"] > Decimal("0"):
        if after_unlock["total_debt"] > after_unlock["borrow_power"] or after_unlock["health_factor"] < Decimal("1"):
            db.session.rollback()
            return None, "拒绝解锁：提取该资产将导致您剩余的质押物不足以支撑当前债务，有即时清算风险"

    try:
        pledge.pledge_status = "unlocked"
        pledge.available_loan_amount = Decimal("0")
        risk_engine.sync_available_amounts(user_id)
        db.session.commit()
        
        result = pledge.to_dict()
        result['pledge_amount'] = str(result['pledge_amount'])
        result['pledge_rate'] = str(result['pledge_rate'])
        result['available_loan_amount'] = str(result['available_loan_amount'])
        return result, None
        
    except Exception as e:
        db.session.rollback()
        return None, f"数据库异常: {str(e)}"
