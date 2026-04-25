"""数据仿真与展示 Service

提供价格历史生成和系统统计功能。
"""
import random
from decimal import Decimal, ROUND_HALF_UP
from app.models import db
from app.models.asset import VirtualAsset
from app.models.user import User
from app.models.pledge import Pledge
from app.models.loan import Loan
from app.models.liquidation import Liquidation


def get_price_history(asset_id):
    """获取资产最近 30 天的模拟历史价格

    Args:
        asset_id (int): 资产ID

    Returns:
        (dict|None, str|None): (包含 dates 和 prices 的字典, 错误消息)

    # TODO: 核心逻辑 - 历史价格生成算法，后续需替换为真实历史数据存储
    当前实现：基于当前价格和波动率，从30天前反向模拟生成价格序列
    """
    asset = VirtualAsset.query.get(asset_id)
    if not asset:
        return None, "资产不存在"

    current_price = float(asset.current_price)
    volatility = float(asset.price_volatility)
    prices = []
    price = current_price

    # TODO: 核心逻辑 - 模拟价格路径生成，后续需使用更精确的金融模型
    # 当前实现：从当前价格反向随机游走 30 天
    for _ in range(30):
        price = price / (1 + random.uniform(-volatility, volatility))
        prices.append(round(price, 4))
    prices.reverse()
    prices.append(current_price)

    from datetime import datetime, timedelta

    today = datetime.now().date()
    dates = [(today - timedelta(days=30 - i)).isoformat() for i in range(31)]

    return {
        "asset_id": asset.asset_id,
        "asset_name": asset.asset_name,
        "asset_code": asset.asset_code,
        "dates": dates,
        "prices": prices,
    }, None


def get_statistics():
    """获取系统全局统计数据

    Returns:
        dict: 包含 total_users, total_pledge_value, total_loan_amount, total_liquidations

    # TODO: 核心逻辑 - 统计指标计算，后续可添加更多维度（如日活、平均利率等）
    """
    total_users = User.query.count()

    active_pledges = Pledge.query.filter_by(pledge_status="active").all()
    total_pledge_value = Decimal("0")
    for p in active_pledges:
        asset = VirtualAsset.query.get(p.asset_id)
        if asset:
            total_pledge_value += p.pledge_amount * asset.current_price

    loans = Loan.query.filter(Loan.repay_status != "paid").all()
    total_loan_amount = sum(loan.remaining_principal for loan in loans)

    total_liquidations = Liquidation.query.count()

    return {
        "total_users": total_users,
        "total_pledge_value": str(
            total_pledge_value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        ),
        "total_loan_amount": str(
            total_loan_amount.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            if total_loan_amount
            else "0.0000"
        ),
        "total_liquidations": total_liquidations,
    }
