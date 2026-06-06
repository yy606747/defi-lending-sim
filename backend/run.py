import os
from decimal import Decimal
from app import create_app
from app.models import db
from app.models.asset import VirtualAsset

app = create_app()


def ensure_sqlite_schema():
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


with app.app_context():
    db.create_all()
    ensure_sqlite_schema()

    if VirtualAsset.query.count() == 0:
        assets = [
            VirtualAsset(asset_name="Ethereum", asset_code="ETH",
                         current_price=Decimal("3000"), price_volatility=Decimal("0.05")),
            VirtualAsset(asset_name="Bitcoin", asset_code="BTC",
                         current_price=Decimal("60000"), price_volatility=Decimal("0.03")),
            VirtualAsset(asset_name="Tether", asset_code="USDT",
                         current_price=Decimal("1"), price_volatility=Decimal("0.001")),
        ]
        db.session.add_all(assets)
        db.session.commit()
        print("初始资产数据已插入")

if __name__ == "__main__":
    host = os.environ.get("BACKEND_HOST", "127.0.0.1")
    port = int(os.environ.get("BACKEND_PORT", "5000"))
    debug = os.environ.get("BACKEND_DEBUG", "1") not in {"0", "false", "False"}
    app.run(debug=debug, host=host, port=port)
