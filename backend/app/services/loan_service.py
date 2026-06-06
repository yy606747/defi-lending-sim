"""借贷管理服务

提供借贷的创建、查询和动态利率计算功能。
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from app.models import db
from app.models.loan import Loan
from app.models.asset import VirtualAsset
from app.models.user import User
from app.services import interest_service, risk_engine
from app.services.protocol_config import RATE_QUANT, TERM_MULTIPLIERS, parse_positive_decimal

DEFAULT_RATE = Decimal("0.0600")

def get_current_rate(loan_term, asset_id=None):
    """获取指定期限的新借款利率。"""
    if asset_id:
        return str(interest_service.get_current_borrow_rate(asset_id, loan_term))
    return str(DEFAULT_RATE.quantize(RATE_QUANT, rounding=ROUND_HALF_UP))

def get_asset_rates(asset_id):
    """获取某个资产不同期限下的新借款利率报价。"""
    asset = VirtualAsset.query.get(asset_id)
    if not asset:
        return None, "资产不存在"

    base_rate = interest_service.get_current_borrow_rate(asset_id)
    rates = []
    for term, multiplier, label in TERM_MULTIPLIERS:
        current_rate = (base_rate * multiplier).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
        rates.append({
            "term": term,
            "rate": str(current_rate),
            "label": label,
        })

    return {
        "asset_name": asset.asset_name,
        "asset_code": asset.asset_code,
        "base_rate": str(base_rate),
        "rates": rates,
    }, None

def create_loan(user_id, asset_id, loan_amount, loan_term):
    """创建借款记录，并在写入前校验账户级可借额度和健康因子。"""
    asset = VirtualAsset.query.get(asset_id)
    if not asset:
        return None, "资产不存在"
    if not User.query.get(user_id):
        return None, "用户不存在"

    if loan_term <= 0:
        return None, "借贷期限必须大于0"

    loan_amount, err = parse_positive_decimal(loan_amount, "借贷金额")
    if err:
        return None, err

    # 1. 借款前先结算已有利息，再由账户级风险引擎计算实时可借额度。
    interest_service.accrue_user_interest(user_id, commit=False)
    snapshot = risk_engine.get_account_snapshot(user_id)
    if loan_amount > snapshot["available_to_borrow"]:
        db.session.rollback()
        return None, f"可借额度不足，当前可借: {snapshot['available_to_borrow']}"

    after_borrow = risk_engine.get_account_snapshot(user_id, extra_debt=loan_amount)
    if after_borrow["total_debt"] > after_borrow["borrow_power"] or after_borrow["health_factor"] < Decimal("1"):
        db.session.rollback()
        return None, "借款后账户健康因子不足，拒绝借贷"

    # 2. 动态利率：按当前市场利用率 + 期限系数确定借款利率。
    rate = interest_service.get_current_borrow_rate(asset_id, loan_term)

    try:
        now = datetime.now()
        loan = Loan(
            user_id=user_id,
            asset_id=asset_id,
            loan_amount=loan_amount,
            loan_rate=rate,
            loan_term=loan_term,
            repay_status="unpaid",
            remaining_principal=loan_amount,
            accrued_interest=Decimal("0"),
            loan_time=now,
            last_accrual_time=now,
        )
        db.session.add(loan)
        db.session.flush()
        risk_engine.sync_available_amounts(user_id)
        db.session.commit()
        return loan.to_dict(), None
    except Exception as e:
        db.session.rollback()
        return None, f"系统错误: {str(e)}"

def get_loans(user_id):
    """获取用户借款记录，并补充资产信息和当前应还总额。"""
    loans = Loan.query.filter_by(user_id=user_id).order_by(Loan.loan_time.desc()).all()
    result = []
    for loan in loans:
        item = loan.to_dict()
        asset = VirtualAsset.query.get(loan.asset_id)
        if asset:
            item["asset_name"] = asset.asset_name
            item["asset_code"] = asset.asset_code
            
        total_repay = loan.remaining_principal + (loan.accrued_interest or Decimal("0"))
        item["total_repay"] = str(total_repay.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))
        result.append(item)
    return result
