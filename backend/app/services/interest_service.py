"""利息结算与借款利率计算。"""
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from app.models import db
from app.models.asset import VirtualAsset
from app.models.loan import Loan
from app.services.protocol_config import (
    MONEY_QUANT,
    RATE_QUANT,
    get_pool_liquidity,
    get_rate_param,
    get_term_multiplier,
)


SECONDS_PER_YEAR = Decimal(365 * 24 * 60 * 60)


def _loan_interest(loan):
    return getattr(loan, "accrued_interest", None) or Decimal("0")


def calculate_dynamic_rate(asset_code, utilization):
    """按分段利率模型计算指定资产市场的当前借款年化利率。"""
    params = get_rate_param(asset_code)
    u = max(Decimal("0"), min(Decimal(str(utilization)), Decimal("1")))
    if u <= params["optimal"]:
        current_rate = params["base_rate"] + params["slope1"] * u
    else:
        rate_at_optimal = params["base_rate"] + params["slope1"] * params["optimal"]
        current_rate = rate_at_optimal + params["slope2"] * (u - params["optimal"])
    return current_rate.quantize(RATE_QUANT, rounding=ROUND_HALF_UP)


def get_market_utilization(asset_id):
    """计算某个借款市场的资金利用率。"""
    asset = VirtualAsset.query.get(asset_id)
    if not asset:
        return Decimal("0")

    total_debt = Decimal("0")
    loans = Loan.query.filter(Loan.asset_id == asset_id, Loan.repay_status != "paid").all()
    for loan in loans:
        total_debt += loan.remaining_principal + _loan_interest(loan)

    pool_liquidity = get_pool_liquidity(asset.asset_code)
    if pool_liquidity <= 0:
        return Decimal("1")
    return max(Decimal("0"), min(total_debt / pool_liquidity, Decimal("1")))


def get_current_borrow_rate(asset_id, loan_term=None):
    """获取新借款报价；已创建贷款的利率不会被重新定价。"""
    asset = VirtualAsset.query.get(asset_id)
    if not asset:
        return Decimal("0.0600")

    utilization = get_market_utilization(asset_id)
    current_rate = calculate_dynamic_rate(asset.asset_code, utilization)
    if loan_term is not None:
        current_rate *= get_term_multiplier(int(loan_term))
    return current_rate.quantize(RATE_QUANT, rounding=ROUND_HALF_UP)


def accrue_loan_interest(loan, now=None):
    """按单利模型结算单笔贷款从上次结息到当前时刻的利息。"""
    if loan.repay_status == "paid" or loan.remaining_principal <= 0:
        loan.last_accrual_time = now or datetime.now()
        return Decimal("0")

    now = now or datetime.now()
    last_accrual_time = getattr(loan, "last_accrual_time", None) or loan.loan_time or now
    elapsed_seconds = Decimal(str(max((now - last_accrual_time).total_seconds(), 0)))
    if elapsed_seconds <= 0:
        return Decimal("0")

    current_rate = loan.loan_rate or get_current_borrow_rate(loan.asset_id, loan.loan_term)
    interest = (
        loan.remaining_principal
        * current_rate
        * elapsed_seconds
        / SECONDS_PER_YEAR
    ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

    if interest > 0:
        loan.accrued_interest = (_loan_interest(loan) + interest).quantize(
            MONEY_QUANT, rounding=ROUND_HALF_UP
        )
    loan.last_accrual_time = now
    return interest


def accrue_user_interest(user_id, now=None, commit=False):
    """结算指定用户所有未还贷款的利息。"""
    loans = Loan.query.filter(Loan.user_id == user_id, Loan.repay_status != "paid").all()
    total_interest = Decimal("0")
    for loan in loans:
        total_interest += accrue_loan_interest(loan, now=now)
    if commit:
        db.session.commit()
    return total_interest


def accrue_all_interest(now=None, commit=False):
    """结算全系统所有未还贷款的利息。"""
    loans = Loan.query.filter(Loan.repay_status != "paid").all()
    total_interest = Decimal("0")
    for loan in loans:
        total_interest += accrue_loan_interest(loan, now=now)
    if commit:
        db.session.commit()
    return total_interest


def advance_user_time(user_id, days, commit=True):
    """按指定天数推进单个用户的借款计息时间。"""
    delta = timedelta(days=float(days))
    loans = Loan.query.filter(Loan.user_id == user_id, Loan.repay_status != "paid").all()
    total_interest = Decimal("0")
    for loan in loans:
        base_time = loan.last_accrual_time or loan.loan_time or datetime.now()
        total_interest += accrue_loan_interest(loan, now=base_time + delta)
    if commit:
        db.session.commit()
    return total_interest


def advance_all_time(days, commit=True):
    """按指定天数推进全系统借款计息时间。"""
    delta = timedelta(days=float(days))
    loans = Loan.query.filter(Loan.repay_status != "paid").all()
    total_interest = Decimal("0")
    for loan in loans:
        base_time = loan.last_accrual_time or loan.loan_time or datetime.now()
        total_interest += accrue_loan_interest(loan, now=base_time + delta)
    if commit:
        db.session.commit()
    return total_interest


def get_loan_total_due(loan):
    """返回单笔贷款当前应还总额。"""
    return (loan.remaining_principal + _loan_interest(loan)).quantize(
        MONEY_QUANT, rounding=ROUND_HALF_UP
    )


def apply_debt_repayment(user_id, amount):
    """按先息后本顺序，把一笔还款金额分配到用户的未还贷款。"""
    remaining = Decimal(str(amount))
    repaid_interest = Decimal("0")
    repaid_principal = Decimal("0")

    loans = (
        Loan.query.filter(Loan.user_id == user_id, Loan.repay_status != "paid")
        .order_by(Loan.loan_time.asc())
        .all()
    )
    for loan in loans:
        if remaining <= 0:
            break

        accrued_interest = _loan_interest(loan)
        interest_paid = min(accrued_interest, remaining)
        if interest_paid > 0:
            loan.accrued_interest = (accrued_interest - interest_paid).quantize(
                MONEY_QUANT, rounding=ROUND_HALF_UP
            )
            remaining -= interest_paid
            repaid_interest += interest_paid

        principal_paid = min(loan.remaining_principal, remaining)
        if principal_paid > 0:
            loan.remaining_principal = (loan.remaining_principal - principal_paid).quantize(
                MONEY_QUANT, rounding=ROUND_HALF_UP
            )
            remaining -= principal_paid
            repaid_principal += principal_paid

        if loan.remaining_principal <= 0 and _loan_interest(loan) <= 0:
            loan.remaining_principal = Decimal("0")
            loan.accrued_interest = Decimal("0")
            loan.repay_status = "paid"
        else:
            loan.repay_status = "partial"

    return {
        "requested": Decimal(str(amount)),
        "used": Decimal(str(amount)) - remaining,
        "unused": remaining,
        "interest": repaid_interest,
        "principal": repaid_principal,
    }
