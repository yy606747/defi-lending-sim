"""清算管理 Service

提供清算风险检测、清算执行和清算记录查询功能。
"""
from decimal import Decimal, ROUND_HALF_UP
from app.models import db
from app.models.pledge import Pledge
from app.models.loan import Loan
from app.models.liquidation import Liquidation
from app.models.asset import VirtualAsset


def check_liquidation_risk(user_id):
    """检查用户所有 active 质押的清算风险

    Args:
        user_id (int): 用户ID

    Returns:
        list[dict]: 各质押的风险状态列表，每项包含质押信息 + risk_level + collateral_ratio

    # TODO: 核心逻辑 - 清算线和风险等级划分，后续需根据业务需求调整
    当前实现：
    - 质押率 = 当前质押价值 / 用户已借总额
    - 质押率 < 1.2 → 高风险（触发清算线）
    - 质押率 < 1.5 → 中风险
    - 质押率 >= 1.5 → 低风险
    """
    pledges = Pledge.query.filter_by(user_id=user_id, pledge_status="active").all()
    unpaid_loans = Loan.query.filter(
        Loan.user_id == user_id, Loan.repay_status != "paid"
    ).all()
    total_debt = sum(loan.remaining_principal for loan in unpaid_loans)

    result = []
    for p in pledges:
        asset = VirtualAsset.query.get(p.asset_id)
        if not asset:
            continue
        current_value = p.pledge_amount * asset.current_price

        # TODO: 核心逻辑 - 质押率计算和清算线判定，后续需根据业务需求调整
        if total_debt > 0:
            ratio = (current_value / total_debt).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_UP
            )
        else:
            ratio = Decimal("9999.0000")

        # TODO: 核心逻辑 - 风险等级划分标准，后续需根据业务需求调整
        if ratio < Decimal("1.2"):
            risk_level = "high"
        elif ratio < Decimal("1.5"):
            risk_level = "medium"
        else:
            risk_level = "low"

        item = p.to_dict()
        item["asset_name"] = asset.asset_name
        item["asset_code"] = asset.asset_code
        item["current_price"] = str(asset.current_price)
        item["current_value"] = str(
            current_value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        )
        item["collateral_ratio"] = str(ratio)
        item["risk_level"] = risk_level
        item["total_debt"] = str(total_debt)
        result.append(item)
    return result


def execute_liquidation(pledge_id, user_id):
    """执行清算

    Args:
        pledge_id (int): 质押ID
        user_id (int): 用户ID（用于校验所有权）

    Returns:
        (dict|None, str|None): (清算记录, 错误消息)

    # TODO: 核心逻辑 - 清算执行流程，后续需完善（如部分清算、清算罚金等）
    当前实现：
    1. 将质押状态改为 liquidated
    2. 将该用户所有未还清借贷标记为 paid
    3. 创建清算记录
    """
    pledge = Pledge.query.get(pledge_id)
    if not pledge or pledge.user_id != user_id:
        return None, "质押记录不存在"
    if pledge.pledge_status != "active":
        return None, "该质押不处于活跃状态"

    asset = VirtualAsset.query.get(pledge.asset_id)
    liquidation_price = asset.current_price if asset else Decimal("0")
    liquidation_amount = pledge.pledge_amount * liquidation_price

    pledge.pledge_status = "liquidated"

    # TODO: 核心逻辑 - 清算关联借贷处理，后续需精确关联具体借贷而非全部标记
    unpaid_loans = Loan.query.filter(
        Loan.user_id == user_id, Loan.repay_status != "paid"
    ).all()
    for loan in unpaid_loans:
        loan.repay_status = "paid"
        loan.remaining_principal = Decimal("0")

    liq = Liquidation(
        user_id=user_id,
        pledge_id=pledge_id,
        liquidation_price=liquidation_price,
        liquidation_amount=liquidation_amount.quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        ),
        liquidation_status="completed",
    )
    db.session.add(liq)
    db.session.commit()
    return liq.to_dict(), None


def get_liquidations(user_id):
    """获取用户所有清算记录

    Args:
        user_id (int): 用户ID

    Returns:
        list[dict]: 清算记录列表，每项额外包含 asset_name
    """
    liqs = (
        Liquidation.query.filter_by(user_id=user_id)
        .order_by(Liquidation.liquidation_time.desc())
        .all()
    )
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
