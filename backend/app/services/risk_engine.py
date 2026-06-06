"""账户级风险计算。

风险引擎统一计算抵押价值、可借额度、健康因子和质押额度展示值。
"""
from decimal import Decimal, ROUND_HALF_UP

from app.models.asset import VirtualAsset
from app.models.loan import Loan
from app.models.pledge import Pledge
from app.services.protocol_config import MONEY_QUANT, get_asset_param


HF_SENTINEL = Decimal("9999.0000")


def _loan_interest(loan):
    return getattr(loan, "accrued_interest", None) or Decimal("0")


def _q(value):
    return Decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _active_pledges(user_id, exclude_pledge_id=None):
    pledges = Pledge.query.filter_by(user_id=user_id, pledge_status="active").all()
    if exclude_pledge_id is None:
        return pledges
    return [p for p in pledges if p.pledge_id != exclude_pledge_id]


def get_account_snapshot(user_id, exclude_pledge_id=None, extra_debt=Decimal("0")):
    """计算账户在当前价格和债务状态下的完整风险快照。

    参数 `exclude_pledge_id` 用于模拟解锁某笔质押后的状态；
    参数 `extra_debt` 用于模拟新增借款后的状态。
    """
    pledges = _active_pledges(user_id, exclude_pledge_id=exclude_pledge_id)
    total_collateral_value = Decimal("0")
    borrow_power = Decimal("0")
    liquidation_capacity = Decimal("0")
    pledge_rows = []

    for pledge in pledges:
        asset = VirtualAsset.query.get(pledge.asset_id)
        if not asset:
            continue
        params = get_asset_param(asset.asset_code)
        current_value = pledge.pledge_amount * asset.current_price
        pledge_borrow_power = current_value * params["ltv"]
        pledge_liquidation_capacity = current_value * params["liquidation_threshold"]

        total_collateral_value += current_value
        borrow_power += pledge_borrow_power
        liquidation_capacity += pledge_liquidation_capacity
        pledge_rows.append(
            {
                "pledge": pledge,
                "asset": asset,
                "params": params,
                "current_value": current_value,
                "borrow_power": pledge_borrow_power,
                "liquidation_capacity": pledge_liquidation_capacity,
            }
        )

    loans = Loan.query.filter(Loan.user_id == user_id, Loan.repay_status != "paid").all()
    total_debt = Decimal(str(extra_debt))
    for loan in loans:
        total_debt += loan.remaining_principal + _loan_interest(loan)

    available_to_borrow = max(Decimal("0"), borrow_power - total_debt)
    if total_debt > 0:
        health_factor = liquidation_capacity / total_debt
        collateral_ratio = (
            total_collateral_value / total_debt
            if total_collateral_value > 0
            else Decimal("0")
        )
    else:
        health_factor = HF_SENTINEL
        collateral_ratio = HF_SENTINEL

    if total_debt <= 0:
        risk_level = "low"
    elif health_factor < Decimal("1"):
        risk_level = "high"
    elif health_factor < Decimal("1.2000"):
        risk_level = "medium"
    else:
        risk_level = "low"

    allocations = {}
    if borrow_power > 0 and available_to_borrow > 0:
        for row in pledge_rows:
            allocations[row["pledge"].pledge_id] = (
                available_to_borrow * row["borrow_power"] / borrow_power
            ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    else:
        for row in pledge_rows:
            allocations[row["pledge"].pledge_id] = Decimal("0")

    return {
        "total_collateral_value": _q(total_collateral_value),
        "borrow_power": _q(borrow_power),
        "liquidation_capacity": _q(liquidation_capacity),
        "total_debt": _q(total_debt),
        "available_to_borrow": _q(available_to_borrow),
        "health_factor": health_factor.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP),
        "collateral_ratio": collateral_ratio.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP),
        "risk_level": risk_level,
        "pledges": pledge_rows,
        "available_allocations": allocations,
    }


def get_pledge_available(snapshot, pledge_id):
    """从账户快照中读取单笔质押分摊到的可借额度。"""
    return snapshot["available_allocations"].get(pledge_id, Decimal("0.0000"))


def sync_available_amounts(user_id):
    """把实时风险快照同步回质押表，供旧页面字段展示。"""
    snapshot = get_account_snapshot(user_id)
    active_ids = set()
    for row in snapshot["pledges"]:
        pledge = row["pledge"]
        active_ids.add(pledge.pledge_id)
        pledge.available_loan_amount = get_pledge_available(snapshot, pledge.pledge_id)

    pledges = Pledge.query.filter_by(user_id=user_id).all()
    for pledge in pledges:
        if pledge.pledge_id not in active_ids:
            pledge.available_loan_amount = Decimal("0")
    return snapshot
