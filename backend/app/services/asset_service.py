"""虚拟资产管理 Service

提供虚拟资产的查询和价格模拟功能。
"""
import math
import random
from decimal import Decimal, ROUND_HALF_UP
from app.models import db
from app.models.asset import VirtualAsset


def get_all_assets():
    """获取所有虚拟资产列表

    Returns:
        list[dict]: 资产信息列表，每项包含 asset_id, asset_name, asset_code, current_price, price_volatility
    """
    assets = VirtualAsset.query.all()
    return [a.to_dict() for a in assets]


def get_asset(asset_id):
    """获取单个虚拟资产信息

    Args:
        asset_id (int): 资产ID

    Returns:
        (dict|None, str|None): (资产信息, 错误消息)
    """
    asset = VirtualAsset.query.get(asset_id)
    if not asset:
        return None, "资产不存在"
    return asset.to_dict(), None


def simulate_price_change():
    """对所有资产执行一次价格随机波动模拟

    价格模拟算法（每步 = 1 天，price_volatility 为日波动参数）：
    - ETH / BTC：几何布朗运动（GBM），S = S × exp((μ - σ²/2) + σ × Z)
    - USDT：Ornstein-Uhlenbeck 均值回归，向锚定价 1.0 回归

    Returns:
        list[dict]: 模拟后的资产列表（含更新后的价格）
    """
    mu = 0.0  # 漂移率（零漂移）

    assets = VirtualAsset.query.all()
    for asset in assets:
        sigma = float(asset.price_volatility)  # 日波动参数
        current_price = float(asset.current_price)

        if asset.asset_code == "USDT":
            # 均值回归模型（Ornstein-Uhlenbeck）：价格向锚定均值 1.0 靠拢
            theta = 0.5       # 回归速度
            mean_price = 1.0  # 锚定均值
            z = random.gauss(0, 1)
            change = theta * (mean_price - current_price) + sigma * z
            new_price_f = current_price + change
            # USDT 价格硬性约束：锚定价 ±2%，确保稳定币特性
            if new_price_f < 0.98:
                new_price_f = 0.98
            elif new_price_f > 1.02:
                new_price_f = 1.02
            new_price = Decimal(str(round(new_price_f, 8)))
        else:
            # 几何布朗运动（GBM）：sigma 为日波动参数，价格天然 > 0
            z = random.gauss(0, 1)
            factor = math.exp((mu - 0.5 * sigma ** 2) + sigma * z)
            new_price_f = current_price * factor
            new_price = Decimal(str(round(new_price_f, 8)))

        asset.current_price = new_price.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    db.session.commit()
    return [a.to_dict() for a in assets]
