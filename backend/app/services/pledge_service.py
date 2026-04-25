"""质押管理 Service

提供质押的创建、查询和解锁功能。
"""
from decimal import Decimal, ROUND_HALF_UP
from app.models import db
from app.models.pledge import Pledge
from app.models.loan import Loan
from app.models.asset import VirtualAsset


def create_pledge(user_id, asset_id, pledge_amount):
    """创建质押记录

    Args:
        user_id (int): 用户ID
        asset_id (int): 质押资产ID
        pledge_amount (Decimal|str): 质押数量

    Returns:
        (dict|None, str|None): (质押记录, 错误消息)

    业务流程：
    1. 查询资产当前价格
    2. 计算质押价值和可借额度
    3. 创建质押记录
    """
    asset = VirtualAsset.query.get(asset_id)
    if not asset:
        return None, "资产不存在"

    pledge_amount = Decimal(str(pledge_amount))
    if pledge_amount <= 0:
        return None, "质押数量必须大于0"

    # TODO: 核心逻辑 - 质押率计算规则，后续需根据业务需求调整
    # 当前实现：固定质押率上限 0.75，可借额度 = 质押价值 * 质押率
    pledge_rate = Decimal("0.75")
    pledge_value = pledge_amount * asset.current_price
    available_loan_amount = (pledge_value * pledge_rate).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    )

    pledge = Pledge(
        user_id=user_id,
        asset_id=asset_id,
        pledge_amount=pledge_amount,
        pledge_rate=pledge_rate,
        available_loan_amount=available_loan_amount,
        pledge_status="active",
    )
    db.session.add(pledge)
    db.session.commit()
    return pledge.to_dict(), None


def get_pledges(user_id):
    """获取用户所有质押记录，关联资产名称和当前价值

    Args:
        user_id (int): 用户ID

    Returns:
        list[dict]: 质押记录列表，每项额外包含 asset_name, asset_code, current_price, current_value
    """
    pledges = Pledge.query.filter_by(user_id=user_id).all()
    result = []
    for p in pledges:
        item = p.to_dict()
        asset = VirtualAsset.query.get(p.asset_id)
        if asset:
            item["asset_name"] = asset.asset_name
            item["asset_code"] = asset.asset_code
            item["current_price"] = str(asset.current_price)
            current_value = p.pledge_amount * asset.current_price
            item["current_value"] = str(
                current_value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            )
        result.append(item)
    return result


def unlock_pledge(pledge_id, user_id):
    """解锁质押

    Args:
        pledge_id (int): 质押ID
        user_id (int): 用户ID（用于校验所有权）

    Returns:
        (dict|None, str|None): (更新后的质押记录, 错误消息)

    校验规则：
    - 质押必须属于当前用户
    - 质押状态必须为 active
    - 该用户不能有未还清的借贷（简化逻辑）
    """
    pledge = Pledge.query.get(pledge_id)
    if not pledge or pledge.user_id != user_id:
        return None, "质押记录不存在"
    if pledge.pledge_status != "active":
        return None, "该质押状态不允许解锁"

    # TODO: 核心逻辑 - 解锁校验规则，后续需完善（如只校验与该质押关联的借贷）
    # 当前简化实现：检查用户是否有未还清借贷
    unpaid = Loan.query.filter(
        Loan.user_id == user_id, Loan.repay_status != "paid"
    ).first()
    if unpaid:
        return None, "存在未还清的借贷，无法解锁质押"

    pledge.pledge_status = "unlocked"
    db.session.commit()
    return pledge.to_dict(), None
