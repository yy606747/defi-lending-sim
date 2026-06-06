# DeFi Lending Sim 后端测试计划

## 当前状态

本测试计划对应当前 `main` 分支的后端实现。后端测试集中在 `tests/backend/`，当前收集到 108 个 pytest 用例，最近一次验证结果为：

```bash
pytest tests/backend -q
# 108 passed
```

说明：测试运行时仍会出现 SQLAlchemy `Query.get()` 的 legacy warning，这是兼容性警告，不影响当前功能正确性。后续可把旧式 `Model.query.get()` 逐步替换为 `db.session.get()`。

## 测试依据

- 课程测试要求：pytest、`pytest.raises`、参数化、fixture、monkeypatch、金额精度、边界条件、金融不变量、清算边界、覆盖率和回归测试。
- 测试基础：单元测试、集成测试、系统/场景测试、自动化测试、回归测试。
- 黑盒与白盒方法：等价类、边界值、错误推测、因果组合；语句、分支、条件和路径覆盖。

## 测试文件分布

| 文件 | 重点覆盖内容 |
| :--- | :--- |
| `conftest.py` | Flask 测试应用、临时数据库、资产和用户 fixture、JWT 请求头 |
| `test_user_api_and_service.py` | 注册、登录、密码散列、JWT 保护、用户信息更新 |
| `test_asset_and_simulation.py` | 资产查询、价格模拟、价格历史、动态利率边界、统计数据 |
| `test_pledge_loan_repayment_services.py` | 质押、借款、固定利率、单利计息、时间快进、还款 |
| `test_liquidation_and_invariants.py` | 健康因子、清算边界、清算状态迁移、债务不变量 |
| `test_oracle_service.py` | 预言机喂价、全局风险扫描、自动清算、确定性抵押物选择 |
| `test_api_scenarios.py` | 完整用户流程、鉴权、接口空字段校验、时间快进 API |

## 测试分层

### 单元测试

单元测试直接调用 service 函数或小范围 API，重点验证核心公式和状态变化：

- `risk_engine`：抵押价值、可借额度、总债务、健康因子、风险等级。
- `interest_service`：kink 分段利率、固定利率存量贷款、单利计息、时间快进。
- `pledge_service`：多资产 LTV、非法金额、解锁约束。
- `loan_service`：账户级额度检查、借款后健康因子检查、失败回滚。
- `repayment_service`：先息后本、超额还款拒绝、提前/到期类型。
- `liquidation_service`：清算触发条件、close factor、抵押物扣押、坏账。
- `oracle_service`：价格输入校验、风险账户扫描、自动清算。
- `simulation_service`：GBM/OU 合成价格历史、统计指标、时间快进。

### 集成测试

集成测试通过 Flask test client 覆盖路由层、JWT 鉴权和跨模块工作流：

- 未登录用户访问金融接口应被拒绝。
- 登录后创建质押、借款、还款、查询统计形成闭环。
- `/api/simulation/advance-time` 能推进计息时间。
- `/api/oracle/feed` 能触发全局喂价和清算结果返回。
- API 返回统一成功/失败 envelope，方便前端消费。

### 场景测试

场景测试模拟真实 DeFi 操作链路：

1. 用户注册并登录。
2. 查询资产。
3. 质押 ETH/BTC/USDT。
4. 创建借款。
5. 时间快进后产生利息。
6. 部分还款或全额还款。
7. 价格暴跌后健康因子下降。
8. 预言机全局扫描并触发清算。
9. 清算记录、债务余额和抵押物状态保持一致。

### 回归测试

回归测试锁定之前发现过或高概率出现的问题：

- 非数字金额不能导致服务崩溃。
- 0、负数、空字段必须被拒绝。
- 失败借款不能扣减可借额度或创建贷款。
- 查询借款列表不能偷偷计息或写库。
- 时间快进不能覆盖贷款签约利率。
- 还款金额不能超过待还本息。
- 健康因子等于边界值时不能被误清算。
- 清算前必须二次校验健康因子。
- 预言机不允许未知资产或重复资产喂价。
- 多抵押物清算选择必须确定，便于复现。
- USDT 合成历史价格必须保持长度一致并限制在合理区间。

## 黑盒用例设计

- 等价类：合法金额、0、负数、非数字字符串、缺失字段、未知资产、未知用户、未授权请求。
- 边界值：`amount == 0`、最小正数、`loan_term == 30/31/90/91`、`health_factor == 1`、刚低于 1、刚高于 1。
- 错误推测：重复注册、借款超过可借额度、失败请求误改数据库、还款超过待还本息、预言机喂价格式错误。
- 因果组合：有无活跃质押、有无未还贷款、质押是否属于当前用户、质押状态是否 `active`，共同决定是否允许解锁或清算。

## 白盒覆盖目标

- 用户模块：注册成功/重复、登录成功/失败、JWT 保护、信息更新。
- 资产模块：资产查询、显式价格模拟、稳定币价格边界、历史价格生成。
- 质押模块：资产存在性、金额合法性、LTV 计算、解锁状态和债务约束。
- 借贷模块：额度检查、账户级健康因子、期限利率分支、失败请求回滚。
- 利息模块：kink 利率边界、固定利率锁定、单利计息、时间快进。
- 还款模块：部分还款、还清、先息后本、提前/到期类型、非本人贷款。
- 清算模块：风险等级、严格边界、close factor、坏账、状态不变量。
- 预言机模块：批量喂价、全局扫描、自动清算、确定性选择抵押物。
- 仿真统计：用户数、质押价值、未还借款、清算次数、利用率、动态平均利率。

## 金融不变量

测试重点保护以下不变量：

1. 账户可借额度不得小于 0。
2. 借款创建后总债务不得超过账户借款能力。
3. 健康因子大于等于 1 时拒绝清算。
4. 清算扣押抵押物不得超过该笔质押余额。
5. 清算偿还债务后，贷款本金和利息必须同步更新。
6. 还款必须先扣利息再扣本金。
7. 查询接口不得修改贷款利率或偷偷累计利息。
8. 固定随机种子下的价格历史应可复现。

## 运行方式

推荐运行全部后端测试：

```bash
pytest tests/backend -q
```

按文件运行：

```bash
pytest tests/backend/test_oracle_service.py -q
pytest tests/backend/test_liquidation_and_invariants.py -q
pytest tests/backend/test_pledge_loan_repayment_services.py -q
```

按 marker 运行：

```bash
pytest -m financial
pytest -m integration
pytest -m regression
```

覆盖率运行需要先安装 `pytest-cov`：

```bash
python -m pip install -r tests/requirements-test.txt
pytest --cov=backend/app --cov-report=term-missing tests/backend
```

## 复现实验脚本

技术报告中的“固定利率 vs Kink 动态利率”对比实验由以下脚本复现：

```bash
python scripts/experiment_rate_comparison.py
python scripts/experiment_rate_comparison.py --asset BTC --fixed-rate 0.06 --utilizations 0.2 0.8 0.95
```

该脚本直接调用 `interest_service.calculate_dynamic_rate`，因此报告中的对比表和系统真实利率引擎保持一致。
