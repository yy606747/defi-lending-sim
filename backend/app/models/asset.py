from decimal import Decimal
from app.models import db


class VirtualAsset(db.Model):
    __tablename__ = "virtual_asset"

    asset_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    asset_name = db.Column(db.String(64), nullable=False)
    asset_code = db.Column(db.String(16), nullable=False)
    current_price = db.Column(db.Numeric(precision=20, scale=4), nullable=False)
    price_volatility = db.Column(db.Numeric(precision=10, scale=6), default=Decimal("0.01"))

    pledges = db.relationship("Pledge", backref="asset", lazy=True)
    loans = db.relationship("Loan", backref="asset", lazy=True)

    def to_dict(self):
        return {
            "asset_id": self.asset_id,
            "asset_name": self.asset_name,
            "asset_code": self.asset_code,
            "current_price": str(self.current_price),
            "price_volatility": str(self.price_volatility),
        }
