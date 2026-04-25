from decimal import Decimal
from app import create_app
from app.models import db
from app.models.asset import VirtualAsset

app = create_app()

with app.app_context():
    db.create_all()

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
    app.run(debug=True, port=5000)
