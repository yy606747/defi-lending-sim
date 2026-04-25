"""虚拟资产管理 Service

提供虚拟资产的查询和价格模拟功能。
"""
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

    # TODO: 核心逻辑 - 价格模拟算法，后续可替换为更复杂的模型（如几何布朗运动）
    当前实现：new_price = current_price * (1 + random.uniform(-volatility, volatility))

    Returns:
        list[dict]: 模拟后的资产列表（含更新后的价格）
    """
    assets = VirtualAsset.query.all()
    for asset in assets:
        volatility = float(asset.price_volatility)
        change = Decimal(str(random.uniform(-volatility, volatility)))
        # TODO: 核心逻辑 - 价格波动计算公式，后续需根据业务需求调整
        new_price = asset.current_price * (1 + change)
        asset.current_price = new_price.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    db.session.commit()
    return [a.to_dict() for a in assets]
