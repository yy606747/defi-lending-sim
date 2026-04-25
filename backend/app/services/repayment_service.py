"""还款管理 Service

提供还款的创建和查询功能。
"""
from decimal import Decimal
from app.models import db
from app.models.loan import Loan
from app.models.repayment import Repayment
from app.models.asset import VirtualAsset


def create_repayment(user_id, loan_id, repayment_amount):
    """创建还款记录

    Args:
        user_id (int): 用户ID
        loan_id (int): 借贷ID
        repayment_amount (Decimal|str): 还款金额

    Returns:
        (dict|None, str|None): (还款记录, 错误消息)

    业务流程：
    1. 校验借贷属于当前用户且未还清
    2. 更新剩余本金
    3. 判断是否全额还清，更新借贷状态
    4. 创建还款记录
    """
    loan = Loan.query.get(loan_id)
    if not loan or loan.user_id != user_id:
        return None, "借贷记录不存在"
    if loan.repay_status == "paid":
        return None, "该借贷已还清"

    repayment_amount = Decimal(str(repayment_amount))
    if repayment_amount <= 0:
        return None, "还款金额必须大于0"

    # TODO: 核心逻辑 - 还款处理规则，后续需根据业务需求调整
    # 当前实现：直接从剩余本金中扣减（未区分本金和利息）
    loan.remaining_principal -= repayment_amount
    if loan.remaining_principal <= 0:
        loan.remaining_principal = Decimal("0")
        loan.repay_status = "paid"
    else:
        loan.repay_status = "partial"

    # TODO: 核心逻辑 - 还款类型判断规则，后续需根据到期日判断
    # 当前简化实现：统一标记为 early
    repayment = Repayment(
        loan_id=loan_id,
        user_id=user_id,
        repayment_amount=repayment_amount,
        repayment_type="early",
    )
    db.session.add(repayment)
    db.session.commit()
    return repayment.to_dict(), None


def get_repayments(user_id):
    """获取用户所有还款记录

    Args:
        user_id (int): 用户ID

    Returns:
        list[dict]: 还款记录列表，每项额外包含 loan_amount, asset_name
    """
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
