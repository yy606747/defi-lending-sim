"""数据仿真与展示服务

提供价格历史生成和系统统计功能。
"""
import math
import random
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from app.models import db
from app.models.asset import VirtualAsset
from app.models.user import User
from app.models.pledge import Pledge
from app.models.loan import Loan
from app.models.liquidation import Liquidation
from app.services import interest_service
from app.services.protocol_config import (
    SIMULATED_POOL_LIQUIDITY,
    get_pool_liquidity,
)


def calculate_dynamic_rate(asset_code, utilization):
    """根据资产类型和利用率计算当前分段年化利率。"""
    return interest_service.calculate_dynamic_rate(asset_code, utilization)


def get_price_history(asset_id):
    """获取资产最近 30 天的模拟历史价格

    历史价格生成算法：
    以当前真实价格为终点，反向模拟 30 天的价格路径。
    使用固定随机种子（asset_id）生成可复现的合成历史曲线。
    该曲线不是持久化市场日志，只用于图表展示和实验复现。

    模型选择（每步 = 1 天，price_volatility 为日波动参数）：
    - ETH / BTC：几何布朗运动（GBM）反向生成
    - USDT：Ornstein-Uhlenbeck 均值回归反向生成

    返回结果包含日期序列和价格序列；曲线只用于展示和实验复现。
    """
    asset = VirtualAsset.query.get(asset_id)
    if not asset:
        return None, "资产不存在"

    current_price = float(asset.current_price)
    volatility = float(asset.price_volatility)
    prices = []
    price = current_price

    # 固定随机种子：同一资产每次返回一致的历史价格曲线
    rng = random.Random(asset_id)
    sigma = volatility  # 日波动参数
    mu = 0.0

    if asset.asset_code == "USDT":
        # 稳定币使用正向均值回归模拟，从锚定价出发并向 1.0 回归。
        # 不使用反向均值回归，避免偏离被持续放大。
        theta = 0.5
        mean_price = 1.0
        price = mean_price  # 从锚定价出发
        for _ in range(30):
            z = rng.gauss(0, 1)
            change = theta * (mean_price - price) + sigma * z
            price = price + change
            # USDT 硬性约束：锚定价 ±2%
            price = max(0.98, min(1.02, price))
            prices.append(round(price, 4))
        prices.append(current_price)
    else:
        # ETH / BTC 使用几何布朗运动反向生成，sigma 为日波动参数。
        for _ in range(30):
            z = rng.gauss(0, 1)
            factor = math.exp((mu - 0.5 * sigma ** 2) + sigma * z)
            price = price / factor  # 反向：除以因子
            prices.append(round(price, 4))
        prices.reverse()
        prices.append(current_price)  # 第 31 个点 = 当前真实价格

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

    统计指标：
    - total_users: 总用户数
    - total_pledge_value: 活跃质押总价值
    - total_loan_amount: 未还清借贷总额
    - total_liquidations: 清算总次数
    - utilization_rate: 资金利用率（借贷额/质押价值）
    - avg_dynamic_rate: 加权平均动态利率（分段利率模型，按借贷金额加权）
    """
    total_users = User.query.count()

    active_pledges = Pledge.query.filter_by(pledge_status="active").all()
    total_pledge_value = Decimal("0")
    for p in active_pledges:
        asset = VirtualAsset.query.get(p.asset_id)
        if asset:
            total_pledge_value += p.pledge_amount * asset.current_price

    loans = Loan.query.filter(Loan.repay_status != "paid").all()
    total_loan_amount = sum(
        loan.remaining_principal + (loan.accrued_interest or Decimal("0"))
        for loan in loans
    )

    total_liquidations = Liquidation.query.count()

    total_pool_liquidity = sum(SIMULATED_POOL_LIQUIDITY.values(), Decimal("0"))
    if total_pool_liquidity > 0:
        utilization_rate = (total_loan_amount / total_pool_liquidity).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )
    else:
        utilization_rate = Decimal("0")

    # 按资产分别计算利用率和借款利率，再用未还债务做加权平均。
    weighted_rate_sum = Decimal("0")
    weighted_loan_sum = Decimal("0")

    for asset in VirtualAsset.query.all():
        # 该资产的未还清借贷总额为本金加已计息。
        asset_loan = sum(
            loan.remaining_principal + (loan.accrued_interest or Decimal("0"))
            for loan in loans
            if loan.asset_id == asset.asset_id
        )
        if asset_loan <= 0:
            continue

        pool_liquidity = get_pool_liquidity(asset.asset_code)
        if pool_liquidity > 0:
            asset_util = asset_loan / pool_liquidity
            rate = calculate_dynamic_rate(asset.asset_code, asset_util)
            weighted_rate_sum += rate * asset_loan
            weighted_loan_sum += asset_loan

    if weighted_loan_sum > 0:
        avg_dynamic_rate = (weighted_rate_sum / weighted_loan_sum).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )
    else:
        avg_dynamic_rate = Decimal("0")

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
        "utilization_rate": str(utilization_rate),
        "avg_dynamic_rate": str(avg_dynamic_rate),
    }


MAX_ADVANCE_DAYS = Decimal("3650")


def advance_time(user_id, days):
    """按固定天数推进指定用户的计息时间，便于复现实验结果。"""
    try:
        days_dec = Decimal(str(days))
    except Exception:
        return None, "快进天数必须为有效数字"
    if not days_dec.is_finite() or days_dec <= 0:
        return None, "快进天数必须大于0"
    if days_dec > MAX_ADVANCE_DAYS:
        return None, "单次快进天数不能超过3650天"

    interest = interest_service.advance_user_time(user_id, days_dec, commit=True)
    return {
        "days": str(days_dec),
        "interest_accrued": str(interest.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)),
    }, None
