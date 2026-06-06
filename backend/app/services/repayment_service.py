"""还款管理服务

提供还款的创建和查询功能。
"""
from decimal import Decimal
from datetime import datetime, timedelta
from app.models import db
from app.models.loan import Loan
from app.models.repayment import Repayment
from app.models.asset import VirtualAsset
from app.services import interest_service, risk_engine
from app.services.protocol_config import MONEY_QUANT, parse_positive_decimal


def create_repayment(user_id, loan_id, repayment_amount):
    """创建还款记录，并按先息后本顺序扣减债务。"""
    loan = Loan.query.get(loan_id)
    if not loan or loan.user_id != user_id:
        return None, "借贷记录不存在"
    if loan.repay_status == "paid":
        return None, "该借贷已还清"

    repayment_amount, err = parse_positive_decimal(repayment_amount, "还款金额")
    if err:
        return None, err

    interest_service.accrue_loan_interest(loan)
    total_due = interest_service.get_loan_total_due(loan)
    if repayment_amount > total_due:
        db.session.rollback()
        return None, "还款金额不能超过待还本息"

    remaining = repayment_amount
    interest_paid = min(loan.accrued_interest or Decimal("0"), remaining)
    if interest_paid > 0:
        loan.accrued_interest = ((loan.accrued_interest or Decimal("0")) - interest_paid).quantize(
            MONEY_QUANT
        )
        remaining -= interest_paid

    principal_paid = min(loan.remaining_principal, remaining)
    if principal_paid > 0:
        loan.remaining_principal = (loan.remaining_principal - principal_paid).quantize(
            MONEY_QUANT
        )
        remaining -= principal_paid

    if loan.remaining_principal <= 0 and (loan.accrued_interest or Decimal("0")) <= 0:
        loan.remaining_principal = Decimal("0")
        loan.accrued_interest = Decimal("0")
        loan.repay_status = "paid"
    else:
        loan.repay_status = "partial"

    # 还款类型判断规则：根据到期日判断
    due_date = loan.loan_time + timedelta(days=loan.loan_term)
    
    # 假设应用服务器使用的是系统当前时间进行比较
    if datetime.now() > due_date:
        assigned_repayment_type = "due"
    else:
        assigned_repayment_type = "early"

    repayment = Repayment(
        loan_id=loan_id,
        user_id=user_id,
        repayment_amount=repayment_amount,
        repayment_type=assigned_repayment_type,
    )
    
    db.session.add(repayment)
    risk_engine.sync_available_amounts(user_id)
    db.session.commit()
    result = repayment.to_dict()
    result["interest_paid"] = str(interest_paid)
    result["principal_paid"] = str(principal_paid)
    result["remaining_due"] = str(interest_service.get_loan_total_due(loan))
    return result, None


def get_repayments(user_id):
    """获取用户所有还款记录。"""
    repayments = (
        Repayment.query.filter_by(user_id=user_id)
        .order_by(Repayment.repayment_time.desc())
        .all()
    )
    result = []
    for r in repayments:
        item = r.to_dict()
        loan = Loan.query.get(r.loan_id)
        if loan:
            item["loan_amount"] = str(loan.loan_amount)
            asset = VirtualAsset.query.get(loan.asset_id)
            if asset:
                item["asset_name"] = asset.asset_name
        result.append(item)
    return result
