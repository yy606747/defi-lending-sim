"""项目演示启动入口。

用法：
    python main.py --config demo.yaml

该脚本负责读取演示配置、初始化可复现实验数据，并同时启动后端与前端。
"""
from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime
from decimal import Decimal
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
DEFAULT_CONFIG = {
    "reset_database": True,
    "seed_demo_data": True,
    "backend_host": "127.0.0.1",
    "backend_port": 5000,
    "frontend_host": "127.0.0.1",
    "frontend_port": 5173,
    "auto_select_free_ports": True,
    "install_frontend_dependencies": False,
}


def parse_scalar(value: str):
    """解析 demo.yaml 中的简单标量值。"""
    text = value.strip()
    lowered = text.lower()
    if lowered in {"true", "yes", "on"}:
        return True
    if lowered in {"false", "no", "off"}:
        return False
    try:
        return int(text)
    except ValueError:
        return text


def load_config(config_path: Path) -> dict:
    """读取只包含 key: value 的演示配置文件。"""
    config = dict(DEFAULT_CONFIG)
    if not config_path.exists():
        raise SystemExit(f"配置文件不存在: {config_path}")

    lines = config_path.read_text(encoding="utf-8").splitlines()
    for line_no, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise SystemExit(f"配置文件第 {line_no} 行格式错误，应为 key: value")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.split("#", 1)[0].strip()
        if not key:
            raise SystemExit(f"配置文件第 {line_no} 行缺少配置名")
        config[key] = parse_scalar(value)

    return config


def ensure_backend_importable() -> None:
    """把后端目录加入模块搜索路径，并给缺失依赖提供清晰提示。"""
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))
    try:
        import flask  # noqa: F401
        import flask_sqlalchemy  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "后端依赖未安装，请先执行: python -m pip install -r backend/requirements.txt"
        ) from exc


def ensure_sqlite_schema(db) -> None:
    """兼容旧 SQLite 数据库，补齐新增字段。"""
    if not db.engine.url.drivername.startswith("sqlite"):
        return

    column_specs = {
        "loan": {
            "accrued_interest": "NUMERIC(20,4) NOT NULL DEFAULT 0",
            "last_accrual_time": "DATETIME",
        },
        "liquidation": {
            "debt_repaid": "NUMERIC(20,4) NOT NULL DEFAULT 0",
            "collateral_seized": "NUMERIC(20,4) NOT NULL DEFAULT 0",
            "liquidation_bonus": "NUMERIC(10,4) NOT NULL DEFAULT 0",
            "health_factor_before": "NUMERIC(20,4) NOT NULL DEFAULT 0",
            "health_factor_after": "NUMERIC(20,4) NOT NULL DEFAULT 0",
            "bad_debt": "NUMERIC(20,4) NOT NULL DEFAULT 0",
        },
    }

    with db.engine.begin() as conn:
        for table, specs in column_specs.items():
            existing = {
                row[1]
                for row in conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
            }
            for column, spec in specs.items():
                if column not in existing:
                    conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {spec}")


def seed_demo_database(reset_database: bool) -> None:
    """初始化一套稳定的演示数据，便于现场复现清算流程。"""
    ensure_backend_importable()

    from app import create_app
    from app.models import db
    from app.models.asset import VirtualAsset
    from app.models.loan import Loan
    from app.models.pledge import Pledge
    from app.models.user import User
    from app.services import risk_engine
    from app.services.interest_service import get_current_borrow_rate
    from app.services.protocol_config import get_asset_param

    app = create_app()
    with app.app_context():
        if reset_database:
            db.drop_all()
        db.create_all()
        ensure_sqlite_schema(db)

        assets = [
            ("Ethereum", "ETH", Decimal("3000"), Decimal("0.050000")),
            ("Bitcoin", "BTC", Decimal("60000"), Decimal("0.030000")),
            ("Tether", "USDT", Decimal("1"), Decimal("0.001000")),
        ]
        for name, code, price, volatility in assets:
            asset = VirtualAsset.query.filter_by(asset_code=code).first()
            if asset is None:
                db.session.add(
                    VirtualAsset(
                        asset_name=name,
                        asset_code=code,
                        current_price=price,
                        price_volatility=volatility,
                    )
                )
            else:
                asset.asset_name = name
                asset.current_price = price
                asset.price_volatility = volatility
        db.session.flush()

        users = [
            ("Alice", "0xDEMOALICE", "abc12345"),
            ("Bob", "0xDEMOBOB", "abc12345"),
            ("Carol", "0xDEMOCAROL", "abc12345"),
        ]
        user_map = {}
        for name, address, password in users:
            user = User.query.filter_by(virtual_address=address).first()
            if user is None:
                user = User(
                    user_name=name,
                    virtual_address=address,
                    total_asset=Decimal("10000"),
                )
                user.set_password(password)
                db.session.add(user)
                db.session.flush()
            else:
                user.user_name = name
                user.set_password(password)
            user_map[address] = user

        asset_map = {
            asset.asset_code: asset
            for asset in VirtualAsset.query.filter(
                VirtualAsset.asset_code.in_(["ETH", "BTC", "USDT"])
            ).all()
        }

        demo_user_ids = [user.user_id for user in user_map.values()]
        has_demo_positions = (
            Pledge.query.filter(Pledge.user_id.in_(demo_user_ids)).count() > 0
            or Loan.query.filter(Loan.user_id.in_(demo_user_ids)).count() > 0
        )

        # 缺少演示头寸时补入协议侧数据；已有数据则不重复插入。
        if reset_database or not has_demo_positions:
            now = datetime.now()
            demo_positions = [
                ("0xDEMOALICE", "ETH", Decimal("1.0000"), Decimal("1000.0000"), 90),
                ("0xDEMOBOB", "BTC", Decimal("0.0500"), Decimal("1500.0000"), 60),
                ("0xDEMOCAROL", "USDT", Decimal("1500.0000"), Decimal("400.0000"), 30),
            ]
            for address, asset_code, collateral, debt, term in demo_positions:
                user = user_map[address]
                asset = asset_map[asset_code]
                params = get_asset_param(asset_code)
                pledge = Pledge(
                    user_id=user.user_id,
                    asset_id=asset.asset_id,
                    pledge_amount=collateral,
                    pledge_time=now,
                    pledge_rate=params["ltv"],
                    available_loan_amount=Decimal("0"),
                    pledge_status="active",
                )
                db.session.add(pledge)
                db.session.flush()

                rate = get_current_borrow_rate(asset.asset_id, term)
                loan = Loan(
                    user_id=user.user_id,
                    asset_id=asset.asset_id,
                    loan_amount=debt,
                    loan_rate=rate,
                    loan_term=term,
                    loan_time=now,
                    repay_status="unpaid",
                    remaining_principal=debt,
                    accrued_interest=Decimal("0"),
                    last_accrual_time=now,
                )
                db.session.add(loan)

        for user in user_map.values():
            risk_engine.sync_available_amounts(user.user_id)
        db.session.commit()


def npm_command() -> str:
    """返回当前平台可执行的 npm 命令名。"""
    return "npm.cmd" if os.name == "nt" else "npm"


def is_port_available(host: str, port: int) -> bool:
    """检查指定 host/port 是否可以被当前进程绑定。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, int(port)))
        except OSError:
            return False
    return True


def select_available_port(host: str, preferred_port: int, label: str) -> int:
    """优先使用配置端口；被占用时向后寻找可用端口。"""
    port = int(preferred_port)
    for candidate in range(port, port + 50):
        if is_port_available(host, candidate):
            if candidate != port:
                print(f"{label}端口 {port} 已被占用，改用 {candidate}")
            return candidate
    raise RuntimeError(f"{label}端口从 {port} 到 {port + 49} 都不可用")


def prepare_ports(config: dict, start_backend_service: bool, start_frontend_service: bool) -> None:
    """根据配置处理端口冲突，并把最终端口写回配置。"""
    if not config.get("auto_select_free_ports", True):
        return
    if start_backend_service:
        config["backend_port"] = select_available_port(
            str(config["backend_host"]),
            int(config["backend_port"]),
            "后端",
        )
    if start_frontend_service:
        config["frontend_port"] = select_available_port(
            str(config["frontend_host"]),
            int(config["frontend_port"]),
            "前端",
        )


def ensure_frontend_ready(auto_install: bool) -> None:
    """检查前端依赖是否可用，必要时执行 npm install。"""
    if shutil.which(npm_command()) is None:
        raise SystemExit("未找到 npm，请先安装 Node.js 和 npm。")

    node_modules = FRONTEND_DIR / "node_modules"
    if node_modules.exists():
        return

    if not auto_install:
        raise SystemExit("前端依赖未安装，请先执行: cd frontend 后运行 npm install")

    print("正在安装前端依赖...")
    subprocess.run([npm_command(), "install"], cwd=FRONTEND_DIR, check=True)


def start_backend(config: dict) -> subprocess.Popen:
    """启动 Flask 后端服务。"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND_DIR)
    env["BACKEND_HOST"] = str(config["backend_host"])
    env["BACKEND_PORT"] = str(config["backend_port"])
    env["BACKEND_DEBUG"] = "0"
    return subprocess.Popen([sys.executable, "run.py"], cwd=BACKEND_DIR, env=env)


def start_frontend(config: dict) -> subprocess.Popen:
    """启动 Vite 前端开发服务。"""
    env = os.environ.copy()
    env["VITE_BACKEND_URL"] = f"http://{config['backend_host']}:{config['backend_port']}"
    env["NO_PROXY"] = "127.0.0.1,localhost"
    env["no_proxy"] = "127.0.0.1,localhost"
    return subprocess.Popen(
        [
            npm_command(),
            "run",
            "dev",
            "--",
            "--host",
            str(config["frontend_host"]),
            "--port",
            str(config["frontend_port"]),
        ],
        cwd=FRONTEND_DIR,
        env=env,
    )


def wait_process_started(
    process: subprocess.Popen,
    service_name: str,
    delay: float = 1.0,
) -> None:
    """等待子进程完成初始启动，若立即退出则认为启动失败。"""
    time.sleep(delay)
    if process.poll() is not None:
        raise RuntimeError(f"{service_name}启动失败，退出码: {process.returncode}")


def print_demo_guide(config: dict) -> None:
    """输出答辩现场可直接照着操作的演示说明。"""
    frontend_url = f"http://{config['frontend_host']}:{config['frontend_port']}"
    backend_url = f"http://{config['backend_host']}:{config['backend_port']}"
    print()
    print("演示服务已启动")
    print(f"- 前端: {frontend_url}")
    print(f"- 后端: {backend_url}")
    print("- 账号: 0xDEMOALICE / abc12345")
    print("- 账号: 0xDEMOBOB / abc12345")
    print("- 账号: 0xDEMOCAROL / abc12345")
    print()
    print("推荐演示步骤")
    print("1. 登录 0xDEMOALICE，查看首页、质押、借款和清算风险。")
    print("2. 进入预言机页面，把 ETH 价格从 3000 改为 1000 并执行全局喂价。")
    print("3. 观察系统自动扫描风险账户、执行清算，并在清算页面查看记录。")
    print("4. 如需第二轮演示，可重启脚本恢复初始数据，或把 BTC 从 60000 改为 30000。")
    print()
    print("按 Ctrl+C 停止前后端服务。")


def terminate_processes(processes: list[subprocess.Popen]) -> None:
    """停止由本脚本启动的子进程。"""
    for process in processes:
        if process.poll() is None:
            process.terminate()
    for process in processes:
        if process.poll() is None:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


def main() -> int:
    parser = argparse.ArgumentParser(description="DeFi 借贷仿真系统演示启动器")
    parser.add_argument("--config", default="demo.yaml", help="演示配置文件路径")
    parser.add_argument("--seed-only", action="store_true", help="只初始化演示数据，不启动服务")
    parser.add_argument("--no-backend", action="store_true", help="不启动后端服务")
    parser.add_argument("--no-frontend", action="store_true", help="不启动前端服务")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = ROOT_DIR / config_path
    config = load_config(config_path)

    if config.get("seed_demo_data", True):
        seed_demo_database(bool(config.get("reset_database", True)))
        print("演示数据已初始化")

    if args.seed_only:
        return 0

    processes: list[subprocess.Popen] = []
    try:
        prepare_ports(config, not args.no_backend, not args.no_frontend)
        if not args.no_backend:
            backend_process = start_backend(config)
            processes.append(backend_process)
            wait_process_started(backend_process, "后端服务")
        if not args.no_frontend:
            ensure_frontend_ready(bool(config.get("install_frontend_dependencies", False)))
            frontend_process = start_frontend(config)
            processes.append(frontend_process)
            wait_process_started(frontend_process, "前端服务")
        if processes:
            print_demo_guide(config)
            while all(process.poll() is None for process in processes):
                time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在停止演示服务...")
    except RuntimeError as exc:
        print(str(exc))
        return 1
    finally:
        terminate_processes(processes)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
