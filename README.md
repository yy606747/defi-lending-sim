# DeFi 借贷仿真系统快速启动

## 环境要求

- Python 3.8+
- Node.js 18+ 和 npm

## 首次安装依赖

Linux / macOS:

```bash
python3 -m pip install -r backend/requirements.txt -r tests/requirements-test.txt
cd frontend
npm install
cd ..
```

Windows PowerShell:

```powershell
py -3 -m pip install -r backend/requirements.txt -r tests/requirements-test.txt
cd frontend
npm install
cd ..
```

## 一键启动演示

Linux / macOS:

```bash
./scripts/start_demo.sh
```

Windows PowerShell:

```powershell
.\scripts\start_demo.ps1
```

Windows CMD:

```bat
scripts\start_demo.bat
```

也可以直接运行：

```bash
python main.py --config demo.yaml
```

启动后访问：

- 前端页面：`http://127.0.0.1:5173`
- 后端接口：`http://127.0.0.1:5000`

如果默认端口已被占用，启动脚本会自动顺延到下一个可用端口，实际地址以终端输出为准。

`demo.yaml` 默认会在每次启动时重置数据库并写入演示数据；需要保留本地数据时，把 `reset_database` 改为 `false`。

## 演示账号

| 用户 | 登录地址 | 密码 |
| :--- | :--- | :--- |
| Alice | `0xDEMOALICE` | `abc12345` |
| Bob | `0xDEMOBOB` | `abc12345` |
| Carol | `0xDEMOCAROL` | `abc12345` |

## 推荐演示流程

1. 登录 `0xDEMOALICE`，查看首页、质押、借款和清算风险。
2. 进入预言机页面，把 ETH 价格从 `3000` 改为 `1000`，执行全局喂价。
3. 查看系统自动扫描风险账户、执行清算，并在清算页面看到记录。
4. 需要重新演示时，停止服务后再次运行启动脚本，数据库会恢复到初始演示状态。

也可以把 BTC 从 `60000` 改为 `30000`，触发 Bob 的清算场景。

## 只初始化演示数据

```bash
python main.py --config demo.yaml --seed-only
```

## 运行测试

后端：

```bash
pytest tests/backend -q
```

前端单元测试：

```bash
cd frontend
npm test -- --run
```

前端 E2E 测试：

```bash
cd frontend
NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost npm run test:e2e
```

## 运行对比实验（固定利率 vs Kink 动态利率）

复现技术报告 5.5 节的利率对比表，数据直接由系统利率引擎计算得出：

```bash
python scripts/experiment_rate_comparison.py
```

可选参数：`--asset ETH|BTC|USDT` 切换市场、`--fixed-rate 0.06` 调整对比基准、`--utilizations 0.2 0.8 0.95` 自定义利用率点。脚本会输出纯文本表与可直接粘贴进报告的 Markdown 表。
