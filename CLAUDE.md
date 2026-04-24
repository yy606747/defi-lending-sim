# DeFi 借贷协议核心逻辑仿真系统

## 项目简介
金融软件工程课程大作业。仿真 DeFi 借贷协议核心逻辑（质押、借贷、还款、清算、利率调整）。
不涉及真实区块链和真实资金，底层为集中式架构，使用传统数据库存储。

## 技术栈
- 前端：Vue 3 + Vite + Vue Router + Pinia + Axios + Element Plus
- 后端：Python Flask + Flask-RESTful + SQLAlchemy + Flask-JWT-Extended + Flask-CORS
- 数据库：SQLite（开发阶段），可切换 MySQL
- 图表：ECharts

## 架构分层
表现层(Vue 3) → API层(Flask Blueprint) → Service层(业务逻辑) → Model层(SQLAlchemy) → SQLite

## 7 个子系统
1. 用户管理 — 注册/登录/JWT鉴权/个人信息
2. 虚拟资产管理 — 资产信息CRUD/价格模拟（随机波动）
3. 质押管理 — 质押操作/质押率计算/可借贷额度核算
4. 借贷管理 — 借贷请求/利率计算/额度审核
5. 还款管理 — 还款处理/本息计算/状态更新
6. 清算管理 — 质押率监控/清算触发/清算执行
7. 数据仿真与展示 — 价格趋势/统计分析/图表报表

## 6 张核心数据表
- user: user_id(PK), user_name, virtual_address(唯一), password(哈希), register_time, total_asset(Decimal,默认10000)
- virtual_asset: asset_id(PK), asset_name, asset_code, current_price(Decimal), price_volatility
- pledge: pledge_id(PK), user_id(FK→user), asset_id(FK→virtual_asset), pledge_amount, pledge_time, pledge_rate, available_loan_amount, pledge_status(active/liquidated/unlocked)
- loan: loan_id(PK), user_id(FK), asset_id(FK), loan_amount, loan_rate, loan_term(天), loan_time, repay_status(unpaid/partial/paid), remaining_principal
- repayment: repayment_id(PK), loan_id(FK→loan), user_id(FK), repayment_amount, repayment_time, repayment_type(early/due)
- liquidation: liquidation_id(PK), user_id(FK), pledge_id(FK→pledge), liquidation_price, liquidation_amount, liquidation_time, liquidation_status

## 数据关系
- user → pledge/loan/repayment/liquidation: 一对多
- virtual_asset → pledge/loan: 一对多
- loan → repayment: 一对多
- pledge → liquidation: 一对一

## 编码规范
- 后端 API 统一返回：{"code": 200, "message": "success", "data": {...}}
- 前端 API 封装在 src/api/ 目录，按模块分文件（user.js, asset.js, pledge.js...）
- Service 层包含所有业务逻辑，Route 层只做参数校验 + 调用 Service
- 所有金额用 Decimal，不用 float
- 前端代理：vite.config.js 把 /api 代理到 Flask 的 5000 端口

## 当前进度
- [ ] 阶段一：骨架 + 用户管理跑通
- [ ] 阶段二：所有模块接口层 + 前端页面（Service 层用简单mock逻辑）
- [ ] 阶段三：填充各模块真实业务逻辑（团队分工）
