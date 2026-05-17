"""数据仿真与展示 Service

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


# ---------------------------------------------------------------------------
# Kink Model 利率参数（Aave/Compound 标准分段线性模型）
# 利用率低于 optimal 时利率平缓上升，高于 optimal 时急剧上升
# ---------------------------------------------------------------------------
RATE_PARAMS = {
    "ETH": {
        "base_rate": Decimal("0.02"),
        "slope1": Decimal("0.04"),
        "slope2": Decimal("0.75"),
        "optimal": Decimal("0.80"),
    },
    "BTC": {
        "base_rate": Decimal("0.02"),
        "slope1": Decimal("0.03"),
        "slope2": Decimal("0.60"),
        "optimal": Decimal("0.80"),
    },
    "USDT": {
        "base_rate": Decimal("0.04"),
        "slope1": Decimal("0.04"),
        "slope2": Decimal("0.75"),
        "optimal": Decimal("0.80"),
    },
}

DEFAULT_RATE_PARAMS = RATE_PARAMS["ETH"]


def calculate_dynamic_rate(asset_code, utilization):
    """根据资产类型和利用率计算当前动态利率（Kink Model）

    Args:
        asset_code (str): 资产代码（ETH/BTC/USDT）
        utilization (Decimal): 利用率（0~1）

    Returns:
        Decimal: 动态年化利率
    """
    params = RATE_PARAMS.get(asset_code, DEFAULT_RATE_PARAMS)
    u = min(utilization, Decimal("1.0"))

    if u <= params["optimal"]:
        # 低利用率区间：利率缓慢上升，鼓励借款
        rate = params["base_rate"] + u * params["slope1"]
    else:
        # 高利用率区间：利率急剧上升，抑制借款、保护流动性
        rate_at_optimal = params["base_rate"] + params["optimal"] * params["slope1"]
        rate = rate_at_optimal + (u - params["optimal"]) * params["slope2"]
        rate = min(rate, Decimal("2.0"))  # 封顶 200%

    return rate.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def get_price_history(asset_id):
    """获取资产最近 30 天的模拟历史价格

    历史价格生成算法：
    以当前真实价格为终点，反向模拟 30 天的价格路径。
    使用固定随机种子（asset_id）确保同一资产每次返回相同的历史曲线，
    模拟"真实历史数据存储"的可复现效果。

    模型选择（每步 = 1 天，price_volatility 为日波动参数）：
    - ETH / BTC：几何布朗运动（GBM）反向生成
    - USDT：Ornstein-Uhlenbeck 均值回归反向生成

    Args:
        asset_id (int): 资产ID

    Returns:
        (dict|None, str|None): (包含 dates 和 prices 的字典, 错误消息)
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
        # USDT：稳定币，正向 OU 模拟（从锚定价出发，向 1.0 回归）
        # 不使用反向 OU（反向会放大偏离，导致价格发散）
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
        # 正向生成无需 reverse，直接替换最后一个点为当前真实价格
        prices[-1] = current_price if abs(current_price - 1.0) < 0.02 else prices[-1]
        prices.append(current_price)
    else:
        # ETH / BTC：GBM 反向生成，sigma 为日波动参数
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
    - avg_dynamic_rate: 加权平均动态利率（Kink Model，按借贷金额加权）

    Returns:
        dict: 统计数据
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

    # --- 新增：资金利用率 ---
    if total_pledge_value > 0:
        utilization_rate = (total_loan_amount / total_pledge_value).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )
    else:
        utilization_rate = Decimal("0")

    # --- 新增：动态平均利率（按资产分别计算利用率 → Kink Model → 加权平均）---
    weighted_rate_sum = Decimal("0")
    weighted_loan_sum = Decimal("0")

    for asset in VirtualAsset.query.all():
        # 该资产的未还清借贷总额
        asset_loan = sum(
            loan.remaining_principal
            for loan in loans
            if loan.asset_id == asset.asset_id
        )
        if asset_loan <= 0:
            continue

        # 该资产的活跃质押总价值
        asset_pledge = Decimal("0")
        for p in active_pledges:
            if p.asset_id == asset.asset_id:
                asset_pledge += p.pledge_amount * asset.current_price

        if asset_pledge > 0:
            asset_util = asset_loan / asset_pledge
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
        # 新增指标
        "utilization_rate": str(utilization_rate),
        "avg_dynamic_rate": str(avg_dynamic_rate),
    }
