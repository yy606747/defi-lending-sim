"""利率模型对比实验：固定利率 vs Kink 动态利率。

本脚本直接调用系统真实的利率引擎 interest_service.calculate_dynamic_rate
（与借款时给新贷款定价用的是同一个函数），在不同市场利用率下，
对比"固定年化利率"与"Kink 分段利率"对应的协议年化利息收入。

用法：
    python scripts/experiment_rate_comparison.py
    python scripts/experiment_rate_comparison.py --asset ETH --fixed-rate 0.06

输出同时给出纯文本表与可直接粘进技术报告 5.5 节的 Markdown 表。
"""
from __future__ import annotations

import argparse
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

# 让脚本能 import 后端代码（与 main.py 相同做法）。
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.interest_service import calculate_dynamic_rate  # noqa: E402
from app.services.protocol_config import RATE_PARAMS, get_pool_liquidity  # noqa: E402


# 默认对比的利用率点：含报告 5.5 节的 20% / 80% / 95%，另加几个点便于画曲线。
DEFAULT_UTILIZATIONS = ["0.20", "0.40", "0.60", "0.80", "0.90", "0.95", "1.00"]


def _q2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def build_rows(asset_code: str, fixed_rate: Decimal, utilizations):
    pool = get_pool_liquidity(asset_code)  # 该市场的模拟资金池规模（美元）
    rows = []
    for u_str in utilizations:
        u = Decimal(u_str)
        debt = pool * u
        kink_rate = calculate_dynamic_rate(asset_code, u)  # 真实利率引擎
        rows.append({
            "utilization": u,
            "debt": _q2(debt),
            "fixed_income": _q2(debt * fixed_rate),
            "kink_rate": kink_rate,
            "kink_income": _q2(debt * kink_rate),
        })
    return pool, rows


def parse_decimal_list(raw_values):
    """解析并校验利用率列表，保证实验输入可解释。"""
    values = []
    for raw_value in raw_values:
        value = Decimal(str(raw_value))
        if value < 0 or value > 1:
            raise argparse.ArgumentTypeError("利用率必须在 0 到 1 之间")
        values.append(value)
    return values


def _pct(value: Decimal) -> str:
    return f"{(value * 100).quantize(Decimal('0.01'))}%"


def print_text_table(asset_code, pool, fixed_rate, rows):
    print(f"\n资产市场: {asset_code}    模拟资金池: ${pool:,.2f}    固定利率基准: {_pct(fixed_rate)}")
    header = f"{'利用率':>8} | {'未还债务':>14} | {'固定收入':>14} | {'Kink利率':>10} | {'Kink收入':>14}"
    print(header)
    print("-" * len(header))
    for r in rows:
        print(
            f"{_pct(r['utilization']):>8} | {r['debt']:>14,.2f} | {r['fixed_income']:>14,.2f} | "
            f"{_pct(r['kink_rate']):>10} | {r['kink_income']:>14,.2f}"
        )


def print_markdown_table(asset_code, fixed_rate, rows):
    print("\n--- 可直接粘进报告 5.5 节的 Markdown 表 ---\n")
    print(f"| 利用率 | 未还债务 | 固定 {_pct(fixed_rate)} 利率收入 | Kink 模型利率 | Kink 模型收入 |")
    print("| ---: | ---: | ---: | ---: | ---: |")
    for r in rows:
        print(
            f"| {_pct(r['utilization'])} | {r['debt']:,.2f} | {r['fixed_income']:,.2f} | "
            f"{_pct(r['kink_rate'])} | {r['kink_income']:,.2f} |"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="固定利率 vs Kink 动态利率对比实验")
    parser.add_argument("--asset", default="ETH", choices=sorted(RATE_PARAMS.keys()),
                        help="资产代码，如 ETH / BTC / USDT")
    parser.add_argument("--fixed-rate", type=str, default="0.06", help="对比用的固定年化利率")
    parser.add_argument("--utilizations", nargs="*", default=DEFAULT_UTILIZATIONS,
                        help="利用率列表，如 0.20 0.80 0.95")
    args = parser.parse_args()

    asset_code = args.asset.upper()
    fixed_rate = Decimal(args.fixed_rate)
    if fixed_rate < 0:
        parser.error("--fixed-rate 不能为负数")
    utilizations = parse_decimal_list(args.utilizations)
    pool, rows = build_rows(asset_code, fixed_rate, utilizations)

    print_text_table(asset_code, pool, fixed_rate, rows)
    print_markdown_table(asset_code, fixed_rate, rows)
    print(
        "\n结论：低利用率时 Kink 利率低于固定利率、鼓励借款；超过最优利用率(80%)后 Kink 利率"
        "快速抬升，显著高于固定利率，抑制流动性枯竭。本项目用 Kink 模型为新贷款定价。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
