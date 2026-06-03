"""质押管理 Service

提供质押的创建、查询和解锁功能。
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from app.models import db
from app.models.pledge import Pledge
from app.models.loan import Loan
from app.models.asset import VirtualAsset
from app.models.user import User


## ==================== 统一风控数据联结表 ====================
# LTV: 借款上限（能借多少）
# LIQUIDATION_RATIO: 最低质押率门槛（跌破多少会爆仓）
ASSET_CONFIG = {
    'USDT': {
        'LTV': Decimal('0.90'),              # 质押 100U 最多借 90U (初始质押率 1.11)
        'LIQUIDATION_RATIO': Decimal('1.05')  # 质押率低于 1.05 时清算 (留有 5% 缓冲垫)
    },
    'ETH': {
        'LTV': Decimal('0.80'),              # 质押 100 刀 ETH 最多借 80 刀 (初始质押率 1.25)
        'LIQUIDATION_RATIO': Decimal('1.15')  # 质押率低于 1.15 时清算 (留有 10% 缓冲垫)
    },
    'BTC': {
        'LTV': Decimal('0.75'),              # 团队手册默认上限 0.75 (初始质押率 1.33)
        'LIQUIDATION_RATIO': Decimal('1.20')  # 原代码默认清算线 1.20 (留有 13% 缓冲垫)
    }
}
DEFAULT_CONFIG = {
    'LTV': Decimal('0.75'), 
    'LIQUIDATION_RATIO': Decimal('1.20')
}



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

    if not User.query.get(user_id):
        return None, "用户不存在"

    try:
        pledge_amount = Decimal(str(pledge_amount))
    except (InvalidOperation, ValueError):
        return None, "质押数量必须为有效数字"

    if pledge_amount <= 0:
        return None, "质押数量必须大于0"

    # TODO: 核心逻辑 - 质押率计算规则
    # 从统一配置表中获取该资产的借款上限 (LTV)
    config = ASSET_CONFIG.get(asset.asset_code, DEFAULT_CONFIG)
    pledge_rate = config['LTV']
    
    # 可借贷额度 = 质押价值 × 质押率上限
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
        db.session.commit()
        
        # 统一转为 str 传给前端，防止精度丢失
        result = pledge.to_dict()
        result['pledge_amount'] = str(result['pledge_amount'])
        result['pledge_rate'] = str(result['pledge_rate'])
        result['available_loan_amount'] = str(result['available_loan_amount'])
        return result, None

    except Exception as e:
        db.session.rollback()
        return None, f"数据库异常: {str(e)}"


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

        # TODO: 转为str传给前段
        item['pledge_amount'] = str(item['pledge_amount'])
        item['pledge_rate'] = str(item['pledge_rate'])
        item['available_loan_amount'] = str(item['available_loan_amount'])

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

    # TODO: 核心逻辑 - 解锁校验规则
    unpaid_loans = Loan.query.filter(Loan.user_id == user_id, Loan.repay_status != "paid").all()
    total_debt = sum(loan.remaining_principal for loan in unpaid_loans)

    # 如果有尚未还清的贷款，验证拔出这笔资产后，剩余的资产是不是还得起、拿得出
    if total_debt > Decimal('0'):
        active_pledges = Pledge.query.filter_by(user_id=user_id, pledge_status="active").all()
        
        # 模拟计算剔除当前这笔质押后，剩余资产所支持的【最高可借额度总和】
        remaining_max_borrow_power = Decimal('0')
        for p in active_pledges:
            if p.pledge_id == pledge_id:
                continue  # 模拟拔出
            ast = VirtualAsset.query.get(p.asset_id)
            if ast:
                config = ASSET_CONFIG.get(ast.asset_code, DEFAULT_CONFIG)
                remaining_max_borrow_power += (p.pledge_amount * ast.current_price * config['LTV'])

        # 如果目前的总负债已经大于了拔出后能支持的最大借款额度，说明会引发即时穿仓，拒绝提款
        if total_debt > remaining_max_borrow_power:
            return None, "拒绝解锁：提取该资产将导致您剩余的质押物不足以支撑当前债务，有即时清算风险"

    try:
        pledge.pledge_status = "unlocked"
        db.session.commit()
        
        result = pledge.to_dict()
        result['pledge_amount'] = str(result['pledge_amount'])
        result['pledge_rate'] = str(result['pledge_rate'])
        result['available_loan_amount'] = str(result['available_loan_amount'])
        return result, None
        
    except Exception as e:
        db.session.rollback()
        return None, f"数据库异常: {str(e)}"
