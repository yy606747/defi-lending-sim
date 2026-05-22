"""借贷管理 Service

提供借贷的创建、查询和利率计算功能。
"""
from decimal import Decimal, ROUND_HALF_UP
from app.models import db
from app.models.loan import Loan
from app.models.pledge import Pledge
from app.models.asset import VirtualAsset
"""借贷管理 Service

提供借贷的创建、查询和利率计算功能。
"""
from decimal import Decimal, ROUND_HALF_UP
from app.models import db
from app.models.loan import Loan
from app.models.pledge import Pledge
from app.models.asset import VirtualAsset

# 核心逻辑 - 各资产基准利率配置
BASE_RATES = {
    'ETH': Decimal('0.05'),
    'BTC': Decimal('0.04'),
    'USDT': Decimal('0.08'),
}
DEFAULT_RATE = Decimal('0.06')

TERM_MULTIPLIERS = [
    (30, Decimal('0.9'), '30天'),
    (60, Decimal('1.0'), '60天'),
    (90, Decimal('1.0'), '90天'),
    (180, Decimal('1.2'), '180天'),
]


def _get_base_rate(asset_code):
    """获取资产的基准年化利率"""
    return BASE_RATES.get(asset_code, DEFAULT_RATE)


def _calc_rate(base_rate, loan_term):
    """根据基准利率和期限计算最终利率"""
    if loan_term <= 30:
        rate = base_rate * Decimal('0.9')
    elif loan_term <= 90:
        rate = base_rate
    else:
        rate = base_rate * Decimal('1.2')
    return rate.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


def get_current_rate(loan_term, asset_id=None):
    """根据借贷期限和资产计算利率"""
    base_rate = DEFAULT_RATE
    if asset_id:
        asset = VirtualAsset.query.get(asset_id)
        if asset:
            base_rate = _get_base_rate(asset.asset_code)
    return str(_calc_rate(base_rate, loan_term))


def get_asset_rates(asset_id):
    """获取指定资产在各期限下的利率列表"""
    asset = VirtualAsset.query.get(asset_id)
    if not asset:
        return None, "资产不存在"

    base_rate = _get_base_rate(asset.asset_code)
    rates = []
    for term, multiplier, label in TERM_MULTIPLIERS:
        rate = (base_rate * multiplier).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
        rates.append({
            "term": term,
            "rate": str(rate),
            "label": label,
        })

    return {
        "asset_name": asset.asset_name,
        "asset_code": asset.asset_code,
        "base_rate": str(base_rate),
        "rates": rates,
    }, None


def create_loan(user_id, asset_id, loan_amount, loan_term):
    """创建借贷记录"""
    asset = VirtualAsset.query.get(asset_id)
    if not asset:
        return None, "资产不存在"

    loan_amount = Decimal(str(loan_amount))
    if loan_amount <= 0:
        return None, "借贷金额必须大于0"

    # 额度校验规则：借贷金额 <= 用户所有 active 质押的可借额度之和
    pledges = Pledge.query.filter_by(user_id=user_id, pledge_status="active").all()
    total_available = sum(p.available_loan_amount for p in pledges)
    if loan_amount > total_available:
        return None, f"可借额度不足，当前可借: {total_available}"

    rate = Decimal(get_current_rate(loan_term, asset_id))

    loan = Loan(
        user_id=user_id,
        asset_id=asset_id,
        loan_amount=loan_amount,
        loan_rate=rate,
        loan_term=loan_term,
        repay_status="unpaid",
        remaining_principal=loan_amount,
    )
    db.session.add(loan)
    db.session.commit()
    return loan.to_dict(), None


def get_loans(user_id):
    """获取用户所有借贷记录，附带应还本息"""
    loans = Loan.query.filter_by(user_id=user_id).order_by(Loan.loan_time.desc()).all()
    result = []
    for loan in loans:
        item = loan.to_dict()
        asset = VirtualAsset.query.get(loan.asset_id)
        if asset:
            item["asset_name"] = asset.asset_name
            item["asset_code"] = asset.asset_code
            
        # 应还本息计算（单利模型）: repay_total = loan_amount * (1 + annual_rate * loan_term / 365)
        rate_factor = loan.loan_rate * Decimal(str(loan.loan_term)) / Decimal("365")
        total_repay = loan.loan_amount * (Decimal('1') + rate_factor)
        
        item["total_repay"] = str(total_repay.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))
        result.append(item)
    return result
# TODO: 核心逻辑 - 各资产基准利率配置，后续可改为从数据库读取
BASE_RATES = {
    'ETH': Decimal('0.05'),
    'BTC': Decimal('0.04'),
    'USDT': Decimal('0.08'),
}
DEFAULT_RATE = Decimal('0.06')

TERM_MULTIPLIERS = [
    (30, Decimal('0.9'), '30天'),
    (60, Decimal('1.0'), '60天'),
    (90, Decimal('1.0'), '90天'),
    (180, Decimal('1.2'), '180天'),
]


def _get_base_rate(asset_code):
    """获取资产的基准年化利率

    Args:
        asset_code (str): 资产代码，如 'ETH', 'BTC', 'USDT'

    Returns:
        Decimal: 基准年化利率
    """
    return BASE_RATES.get(asset_code, DEFAULT_RATE)


def _calc_rate(base_rate, loan_term):
    """根据基准利率和期限计算最终利率

    Args:
        base_rate (Decimal): 基准年化利率
        loan_term (int): 借贷期限（天）

    Returns:
        Decimal: 最终年化利率
    """
    if loan_term <= 30:
        rate = base_rate * Decimal('0.9')
    elif loan_term <= 90:
        rate = base_rate
    else:
        rate = base_rate * Decimal('1.2')
    return rate.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


def get_current_rate(loan_term, asset_id=None):
    """根据借贷期限和资产计算利率

    Args:
        loan_term (int): 借贷期限（天）
        asset_id (int|None): 资产ID，为空时使用默认利率

    Returns:
        str: 年化利率（Decimal 字符串）
    """
    base_rate = DEFAULT_RATE
    if asset_id:
        asset = VirtualAsset.query.get(asset_id)
        if asset:
            base_rate = _get_base_rate(asset.asset_code)
    return str(_calc_rate(base_rate, loan_term))


def get_asset_rates(asset_id):
    """获取指定资产在各期限下的利率列表

    Args:
        asset_id (int): 资产ID

    Returns:
        (dict|None, str|None): (利率信息, 错误消息)

    返回格式：
        {
            "asset_name": "ETH",
            "asset_code": "ETH",
            "base_rate": "0.05",
            "rates": [
                {"term": 30, "rate": "0.0450", "label": "30天"},
                ...
            ]
        }
    """
    asset = VirtualAsset.query.get(asset_id)
    if not asset:
        return None, "资产不存在"

    base_rate = _get_base_rate(asset.asset_code)
    rates = []
    for term, multiplier, label in TERM_MULTIPLIERS:
        rate = (base_rate * multiplier).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
        rates.append({
            "term": term,
            "rate": str(rate),
            "label": label,
        })

    return {
        "asset_name": asset.asset_name,
        "asset_code": asset.asset_code,
        "base_rate": str(base_rate),
        "rates": rates,
    }, None


def create_loan(user_id, asset_id, loan_amount, loan_term):
    """创建借贷记录

    Args:
        user_id (int): 用户ID
        asset_id (int): 借贷资产ID
        loan_amount (Decimal|str): 借贷金额
        loan_term (int): 借贷期限（天）

    Returns:
        (dict|None, str|None): (借贷记录, 错误消息)

    业务流程：
    1. 校验借贷额度是否充足
    2. 根据资产和期限计算利率
    3. 创建借贷记录
    """
    asset = VirtualAsset.query.get(asset_id)
    if not asset:
        return None, "资产不存在"

    loan_amount = Decimal(str(loan_amount))
    if loan_amount <= 0:
        return None, "借贷金额必须大于0"

    # TODO: 核心逻辑 - 额度校验规则，后续需根据业务需求调整
    # 当前实现：借贷金额 <= 用户所有 active 质押的可借额度之和
    pledges = Pledge.query.filter_by(user_id=user_id, pledge_status="active").all()
    total_available = sum(p.available_loan_amount for p in pledges)
    if loan_amount > total_available:
        return None, f"可借额度不足，当前可借: {total_available}"

    rate = Decimal(get_current_rate(loan_term, asset_id))

    loan = Loan(
        user_id=user_id,
        asset_id=asset_id,
        loan_amount=loan_amount,
        loan_rate=rate,
        loan_term=loan_term,
        repay_status="unpaid",
        remaining_principal=loan_amount,
    )
    db.session.add(loan)
    db.session.commit()
    return loan.to_dict(), None


def get_loans(user_id):
    """获取用户所有借贷记录，附带应还本息

    Args:
        user_id (int): 用户ID

    Returns:
        list[dict]: 借贷记录列表，每项额外包含 asset_name, asset_code, total_repay（应还本息）

    # TODO: 核心逻辑 - 本息计算公式，后续需根据业务需求调整（如复利计算）
    当前实现：应还 = 借贷金额 * (1 + 年化利率 * 期限天数 / 365) — 单利
    """
    loans = Loan.query.filter_by(user_id=user_id).order_by(Loan.loan_time.desc()).all()
    result = []
    for loan in loans:
        item = loan.to_dict()
        asset = VirtualAsset.query.get(loan.asset_id)
        if asset:
            item["asset_name"] = asset.asset_name
            item["asset_code"] = asset.asset_code
        # TODO: 核心逻辑 - 应还本息计算，后续需实现复利 / 分期还款计划
        interest = loan.loan_amount * loan.loan_rate * Decimal(str(loan.loan_term)) / Decimal("365")
        total_repay = loan.loan_amount + interest
        item["total_repay"] = str(total_repay.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))
        result.append(item)
    return result
