"""清算管理 Service

提供清算风险检测、清算执行和清算记录查询功能。
"""
from decimal import Decimal, ROUND_HALF_UP
from app.models import db
from app.models.pledge import Pledge
from app.models.loan import Loan
from app.models.liquidation import Liquidation
from app.models.asset import VirtualAsset
# 直接引入 pledge_service 的统一资产配置，实现数据跨模块无缝联结
from app.services.pledge_service import ASSET_CONFIG, DEFAULT_CONFIG


def check_liquidation_risk(user_id):
    """检查用户所有 active 质押的清算风险

    Args:
        user_id (int): 用户ID

    Returns:
        list[dict]: 各质押的风险状态列表，每项包含质押信息 + risk_level + collateral_ratio

    # TODO: 核心逻辑 - 清算线和风险等级划分，后续需根据业务需求调整
    当前实现：
    - 质押率 = 当前质押价值 / 用户已借总额
    - 质押率 < 1.2 → 高风险（触发清算线）
    - 质押率 < 1.5 → 中风险
    - 质押率 >= 1.5 → 低风险
    """
    pledges = Pledge.query.filter_by(user_id=user_id, pledge_status="active").all()
    unpaid_loans = Loan.query.filter(
        Loan.user_id == user_id, Loan.repay_status != "paid"
    ).all()
    total_debt = sum(loan.remaining_principal for loan in unpaid_loans)

    # 1. 计算用户全局质押价值
    total_collateral_value = Decimal('0')
    weighted_liq_sum = Decimal('0')
    pledge_details = []
    for p in pledges:
        asset = VirtualAsset.query.get(p.asset_id)
        if not asset:
            continue
        config = ASSET_CONFIG.get(asset.asset_code, DEFAULT_CONFIG)

        current_value = p.pledge_amount * asset.current_price
        total_collateral_value += current_value
        # 资产价值 × 该资产特有的清算率门槛 (如 USDT 1.05, BTC 1.20)
        weighted_liq_sum += (current_value * config['LIQUIDATION_RATIO'])
        pledge_details.append((p, asset, current_value))

    # 2. 计算全局质押率与资产对应的动态风险切分线
    if total_debt > Decimal('0') and total_collateral_value > Decimal('0'):
        raw_collateral_ratio = total_collateral_value / total_debt
        collateral_ratio = raw_collateral_ratio.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        # 该账户当前的动态清算线 (加权平均值)
        raw_liquidation_threshold = weighted_liq_sum / total_collateral_value
        liquidation_threshold = raw_liquidation_threshold.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        # 预警线跟随清算线保持原有的 0.3 缓冲垫 (例如 1.2 -> 1.5, 1.05 -> 1.35)
        raw_warning_threshold = raw_liquidation_threshold + Decimal('0.30')
    else:
        raw_collateral_ratio = Decimal("9999.0000")
        raw_liquidation_threshold = Decimal("1.20")
        raw_warning_threshold = Decimal("1.50")
        collateral_ratio = Decimal("9999.0000")
        liquidation_threshold = Decimal("1.20")

    # 3. 根据全局质押率划分风险等级（因资产种类有动态阈值）
    if raw_collateral_ratio < raw_liquidation_threshold:
        risk_level = "high"
    elif raw_collateral_ratio < raw_warning_threshold:
        risk_level = "medium"
    else:
        risk_level = "low"

    # 4. 组装返回数据，转为float以兼容JSON
    result = []
    for p, asset, current_value in pledge_details:
        item = p.to_dict()
        item["asset_name"] = asset.asset_name
        item["asset_code"] = asset.asset_code
        item["current_price"] = str(asset.current_price)
        item["current_value"] = str(
            current_value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        )
        item["collateral_ratio"] = str(collateral_ratio)
        item["risk_level"] = risk_level
        item["total_debt"] = str(total_debt)
        result.append(item)
    
    return result


def execute_liquidation(pledge_id, user_id):
    """执行清算

    Args:
        pledge_id (int): 质押ID
        user_id (int): 用户ID（用于校验所有权）

    Returns:
        (dict|None, str|None): (清算记录, 错误消息)

    # TODO: 核心逻辑 - 清算执行流程，后续需完善（如部分清算、清算罚金等）
    当前实现：
    1. 将质押状态改为 liquidated
    2. 将该用户所有未还清借贷标记为 paid
    3. 创建清算记录
    """

    # 1. 基础存在性与状态检验
    pledge = Pledge.query.get(pledge_id)
    if not pledge or pledge.user_id != user_id:
        return None, "质押记录不存在或不属于该用户"
    if pledge.pledge_status != "active":
        return None, "该质押不处于活跃状态"

    # 2. 二次验证全局风险指标，确保合法触发清算
    unpaid_loans = Loan.query.filter(
        Loan.user_id == user_id, Loan.repay_status != "paid"
    ).all()
    total_debt = sum(loan.remaining_principal for loan in unpaid_loans)

    active_pledges = Pledge.query.filter_by(user_id=user_id, pledge_status="active").all()
    total_collateral_value = Decimal('0')
    weighted_liq_sum = Decimal('0')

    for p in active_pledges:
        ast = VirtualAsset.query.get(p.asset_id)
        if ast:
            config = ASSET_CONFIG.get(ast.asset_code, DEFAULT_CONFIG)
            current_value = p.pledge_amount * ast.current_price
            total_collateral_value += current_value
            weighted_liq_sum += (current_value * config['LIQUIDATION_RATIO'])
    
    if total_debt > Decimal('0') and total_collateral_value > Decimal('0'):
        current_ratio = total_collateral_value / total_debt
        liquidation_threshold = weighted_liq_sum / total_collateral_value
        if current_ratio >= liquidation_threshold:
            return None, "当前全局风险指标未达到清算线(1.2)，用户资金处于安全状态，拒绝清算"
    
    else:
        return None, "用户无未还借款，无需清算"
    
    # 3. 准备执行清算数据
    asset = VirtualAsset.query.get(pledge.asset_id)
    liquidation_price = asset.current_price if asset else Decimal("0")
    liquidation_amount = pledge.pledge_amount * liquidation_price

    # 4. 执行状态核心变更 (使用 try-except 确保原子性)
    try:
        pledge.pledge_status = "liquidated"

        """
        依照开发手册简化的强制清算逻辑：质押被清算，该用户全部贷款核销
        这属于“协议坏账处理”的极简模型，而非真实的清算机制，在实际业务中遵循“部分清算”原则：
            1. 清算激励 Bonus : 清算人 Liquidation Bot 代偿部分债务，并以折扣价（如 95 折）获得等值的抵押品。
            2. 清算因子 Close Factor : 一次最多只能清算债务的 50%。
            3. 目标：将健康因子 (质押率/清算线) 拉回到 $1.0$ 以上即可，尽量保护借款人的剩余头寸。
        但是因为实际业务逻辑中需要考虑坏账风险、资产换算、中间状态等，代码复杂度急剧增加，
        所以本次仿真只采用**全额清算模型**以保证系统偿付性
        """
        for loan in unpaid_loans:
            loan.repay_status = "paid"
            loan.remaining_principal = Decimal("0")

        liq = Liquidation(
            user_id = user_id,
            pledge_id = pledge_id,
            liquidation_price = liquidation_price,
            liquidation_amount = liquidation_amount.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
            liquidation_status="completed",
        )
        db.session.add(liq)
        db.session.commit()

        return liq.to_dict(), None

    except Exception as e:
        db.session.rollback()
        return None, f"执行清算时发生错误，已回滚: {str(e)}"


def get_liquidations(user_id):
    """获取用户所有清算记录

    Args:
        user_id (int): 用户ID

    Returns:
        list[dict]: 清算记录列表，每项额外包含 asset_name
    """
    liqs = Liquidation.query.filter_by(user_id=user_id).order_by(Liquidation.liquidation_time.desc()).all()
    result = []
    for liq in liqs:
        item = liq.to_dict()
        pledge = Pledge.query.get(liq.pledge_id)
        if pledge:
            asset = VirtualAsset.query.get(pledge.asset_id)
            if asset:
                item["asset_name"] = asset.asset_name
        result.append(item)
    return result
