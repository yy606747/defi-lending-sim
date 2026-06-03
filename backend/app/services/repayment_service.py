"""还款管理 Service

提供还款的创建和查询功能。
"""
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
from app.models import db
from app.models.loan import Loan
from app.models.repayment import Repayment
from app.models.asset import VirtualAsset


def create_repayment(user_id, loan_id, repayment_amount):
    """创建还款记录"""
    loan = Loan.query.get(loan_id)
    if not loan or loan.user_id != user_id:
        return None, "借贷记录不存在"
    if loan.repay_status == "paid":
        return None, "该借贷已还清"

    try:
        repayment_amount = Decimal(str(repayment_amount))
    except (InvalidOperation, ValueError):
        return None, "还款金额必须为有效数字"

    if repayment_amount <= 0:
        return None, "还款金额必须大于0"
    if repayment_amount > loan.remaining_principal:
        return None, "还款金额不能超过待还本金"

    # 还款处理规则：直接从剩余本金中扣减（符合当前仿真系统的简化模型）
    loan.remaining_principal -= repayment_amount
    if loan.remaining_principal <= 0:
        loan.remaining_principal = Decimal("0")
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
    db.session.commit()
    return repayment.to_dict(), None


def get_repayments(user_id):
    """获取用户所有还款记录"""
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
