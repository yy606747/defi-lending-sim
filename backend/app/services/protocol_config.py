"""借贷协议参数配置。

本文件集中维护风险参数、利率参数和资金池规模，避免业务代码散落硬编码。
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


MONEY_QUANT = Decimal("0.0001")
RATE_QUANT = Decimal("0.0001")


ASSET_PARAMS = {
    "ETH": {
        "ltv": Decimal("0.8000"),
        "liquidation_threshold": Decimal("0.8695652174"),
        "liquidation_bonus": Decimal("0.0500"),
    },
    "BTC": {
        "ltv": Decimal("0.7500"),
        "liquidation_threshold": Decimal("0.8333333333"),
        "liquidation_bonus": Decimal("0.0600"),
    },
    "USDT": {
        "ltv": Decimal("0.9000"),
        "liquidation_threshold": Decimal("0.9523809524"),
        "liquidation_bonus": Decimal("0.0200"),
    },
}

DEFAULT_ASSET_PARAM = {
    "ltv": Decimal("0.7500"),
    "liquidation_threshold": Decimal("0.8333333333"),
    "liquidation_bonus": Decimal("0.0600"),
}


RATE_PARAMS = {
    "ETH": {
        "base_rate": Decimal("0.0200"),
        "slope1": Decimal("0.0400"),
        "slope2": Decimal("0.7500"),
        "optimal": Decimal("0.8000"),
    },
    "BTC": {
        "base_rate": Decimal("0.0200"),
        "slope1": Decimal("0.0300"),
        "slope2": Decimal("0.6000"),
        "optimal": Decimal("0.8000"),
    },
    "USDT": {
        "base_rate": Decimal("0.0400"),
        "slope1": Decimal("0.0400"),
        "slope2": Decimal("0.7500"),
        "optimal": Decimal("0.8000"),
    },
}

DEFAULT_RATE_PARAM = RATE_PARAMS["ETH"]


TERM_MULTIPLIERS = [
    (30, Decimal("0.9000"), "30天"),
    (60, Decimal("1.0000"), "60天"),
    (90, Decimal("1.0000"), "90天"),
    (180, Decimal("1.2000"), "180天"),
]


# 各借款市场的模拟美元流动性。本系统暂不建模 LP 存取款账本。
SIMULATED_POOL_LIQUIDITY = {
    "ETH": Decimal("500000.0000"),
    "BTC": Decimal("1000000.0000"),
    "USDT": Decimal("1000000.0000"),
}


DEFAULT_POOL_LIQUIDITY = Decimal("500000.0000")
FULL_LIQUIDATION_HEALTH_FACTOR = Decimal("0.9500")
PARTIAL_LIQUIDATION_CLOSE_FACTOR = Decimal("0.5000")
FULL_LIQUIDATION_CLOSE_FACTOR = Decimal("1.0000")


def money(value):
    return Decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def rate(value):
    return Decimal(value).quantize(RATE_QUANT, rounding=ROUND_HALF_UP)


def parse_positive_decimal(value, label):
    """解析必须大于 0 的数值参数。"""
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None, f"{label}必须为有效数字"
    if not amount.is_finite():
        return None, f"{label}必须为有限数字"
    if amount <= 0:
        return None, f"{label}必须大于0"
    return amount, None


def get_asset_param(asset_code):
    """按资产代码获取抵押率、清算阈值和清算罚金。"""
    return ASSET_PARAMS.get(str(asset_code or "").upper(), DEFAULT_ASSET_PARAM)


def get_rate_param(asset_code):
    """按资产代码获取利率模型参数。"""
    return RATE_PARAMS.get(str(asset_code or "").upper(), DEFAULT_RATE_PARAM)


def get_pool_liquidity(asset_code):
    """按资产代码获取模拟资金池规模。"""
    return SIMULATED_POOL_LIQUIDITY.get(str(asset_code or "").upper(), DEFAULT_POOL_LIQUIDITY)


def get_term_multiplier(loan_term):
    """按借款期限获取利率调整系数。"""
    for max_days, multiplier, _label in TERM_MULTIPLIERS:
        if loan_term <= max_days:
            return multiplier
    return Decimal("1.2000")
