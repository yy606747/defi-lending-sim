"""借贷管理 Service

提供借贷的创建、查询和利率计算功能。
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from app.models import db
from app.models.loan import Loan
from app.models.pledge import Pledge
from app.models.asset import VirtualAsset

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
    return BASE_RATES.get(asset_code, DEFAULT_RATE)

def _calc_rate(base_rate, loan_term):
    if loan_term <= 30:
        rate = base_rate * Decimal('0.9')
    elif loan_term <= 90:
        rate = base_rate
    else:
        rate = base_rate * Decimal('1.2')
    return rate.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)

def get_current_rate(loan_term, asset_id=None):
    base_rate = DEFAULT_RATE
    if asset_id:
        asset = VirtualAsset.query.get(asset_id)
        if asset:
            base_rate = _get_base_rate(asset.asset_code)
    return str(_calc_rate(base_rate, loan_term))

def get_asset_rates(asset_id):
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
    asset = VirtualAsset.query.get(asset_id)
    if not asset:
        return None, "资产不存在"

    loan_amount = Decimal(str(loan_amount))
    if loan_amount <= 0:
        return None, "借贷金额必须大于0"

    # 1. 校验可借额度是否充足
    pledges = Pledge.query.filter_by(user_id=user_id, pledge_status="active").all()
    total_available = sum(p.available_loan_amount for p in pledges)
    if loan_amount > total_available:
        return None, f"可借额度不足，当前可借: {total_available}"

    # 2. 真实扣减用户的可借额度，防止重复借贷同一笔质押额度
    remaining_to_deduct = loan_amount
    for pledge in pledges:
        if remaining_to_deduct <= 0:
            break
        if pledge.available_loan_amount >= remaining_to_deduct:
            pledge.available_loan_amount -= remaining_to_deduct
            remaining_to_deduct = Decimal('0')
        else:
            remaining_to_deduct -= pledge.available_loan_amount
            pledge.available_loan_amount = Decimal('0')

    # 3. 计算利率并创建记录
    rate = Decimal(get_current_rate(loan_term, asset_id))

    try:
        loan = Loan(
            user_id=user_id,
            asset_id=asset_id,
            loan_amount=loan_amount,
            loan_rate=rate,
            loan_term=loan_term,
            repay_status="unpaid",
            remaining_principal=loan_amount,
            loan_time=datetime.now()
        )
        db.session.add(loan)
        db.session.commit()
        return loan.to_dict(), None
    except Exception as e:
        db.session.rollback()
        return None, f"系统错误: {str(e)}"

def get_loans(user_id):
    loans = Loan.query.filter_by(user_id=user_id).order_by(Loan.loan_time.desc()).all()
    result = []
    for loan in loans:
        item = loan.to_dict()
        asset = VirtualAsset.query.get(loan.asset_id)
        if asset:
            item["asset_name"] = asset.asset_name
            item["asset_code"] = asset.asset_code
            
        # 根据团队手册实现单利复原计算：利息 = 借款总额 * 年化利率 * (期限 / 365)
        interest = loan.loan_amount * loan.loan_rate * Decimal(str(loan.loan_term)) / Decimal("365")
        
        # 应还总额 = 剩余本金 + 固定的单利总利息
        total_repay = loan.remaining_principal + interest
        item["total_repay"] = str(total_repay.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))
        result.append(item)
    return result