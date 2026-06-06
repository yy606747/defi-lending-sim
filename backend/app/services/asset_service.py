"""虚拟资产管理服务

提供虚拟资产的查询和价格模拟功能。
"""
import math
import random
from decimal import Decimal, ROUND_HALF_UP
from app.models import db
from app.models.asset import VirtualAsset
from app.models.pledge import Pledge
from app.services.protocol_config import parse_positive_decimal


def get_all_assets():
    """获取所有虚拟资产列表。"""
    assets = VirtualAsset.query.order_by(VirtualAsset.asset_id).all()
    return [a.to_dict() for a in assets]


def get_asset(asset_id):
    """获取单个虚拟资产信息。"""
    asset = db.session.get(VirtualAsset, asset_id)
    if not asset:
        return None, "资产不存在"
    return asset.to_dict(), None


def _sync_all_impacted_accounts():
    """价格变化后同步所有受影响账户的可借额度。"""
    from app.services import risk_engine

    user_ids = {
        pledge.user_id
        for pledge in Pledge.query.filter_by(pledge_status="active").all()
    }
    for user_id in sorted(user_ids):
        risk_engine.sync_available_amounts(user_id)


def _apply_price_overrides(price_updates):
    """处理显式喂价请求；传入列表时必须完整合法，不能退回随机模拟。"""
    if price_updates is None:
        return None
    if not isinstance(price_updates, list):
        raise ValueError("价格列表格式错误")
    if not price_updates:
        raise ValueError("请提供要更新的资产价格")

    updated_assets = []
    seen_asset_ids = set()
    for item in price_updates:
        if not isinstance(item, dict):
            raise ValueError("价格更新项格式错误")
        asset_id = item.get("asset_id")
        price_value = item.get("current_price", item.get("price"))
        if asset_id is None or price_value is None:
            raise ValueError("资产ID和价格不能为空")

        try:
            asset_id = int(asset_id)
        except (TypeError, ValueError):
            raise ValueError("资产ID必须为整数")
        if asset_id in seen_asset_ids:
            raise ValueError("同一资产不能重复喂价")
        seen_asset_ids.add(asset_id)

        asset = db.session.get(VirtualAsset, asset_id)
        if not asset:
            raise ValueError("资产不存在")
        price, err = parse_positive_decimal(price_value, "资产价格")
        if err:
            raise ValueError(err)
        asset.current_price = price.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        updated_assets.append(asset)

    if not updated_assets:
        raise ValueError("请提供要更新的资产价格")

    _sync_all_impacted_accounts()
    db.session.commit()
    return [a.to_dict() for a in VirtualAsset.query.order_by(VirtualAsset.asset_id).all()]


def simulate_price_change(price_updates=None):
    """执行资产价格模拟或显式喂价。

    随机模拟算法（每步 = 1 天，price_volatility 为日波动参数）：
    - ETH / BTC：几何布朗运动（GBM），S = S × exp((μ - σ²/2) + σ × Z)
    - USDT：Ornstein-Uhlenbeck 均值回归，向锚定价 1.0 回归
    """
    override_result = _apply_price_overrides(price_updates)
    if override_result is not None:
        return override_result

    mu = 0.0  # 漂移率（零漂移）

    assets = VirtualAsset.query.all()
    for asset in assets:
        sigma = float(asset.price_volatility)  # 日波动参数
        current_price = float(asset.current_price)

        if asset.asset_code == "USDT":
            # 均值回归模型：价格向锚定均值 1.0 靠拢。
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
            # 几何布朗运动：sigma 为日波动参数，价格天然大于 0。
            z = random.gauss(0, 1)
            factor = math.exp((mu - 0.5 * sigma ** 2) + sigma * z)
            new_price_f = current_price * factor
            new_price = Decimal(str(round(new_price_f, 8)))

        asset.current_price = new_price.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    _sync_all_impacted_accounts()
    db.session.commit()
    return [a.to_dict() for a in assets]
