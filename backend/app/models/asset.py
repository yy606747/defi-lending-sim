from decimal import Decimal
from sqlalchemy import event
from sqlalchemy.orm import Session
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


@event.listens_for(Session, "before_flush")
def prevent_duplicate_asset_codes(session, flush_context, instances):
    seen_codes = set()
    for asset in list(session.new):
        if not isinstance(asset, VirtualAsset) or not asset.asset_code:
            continue

        asset.asset_code = str(asset.asset_code).strip().upper()
        if asset.asset_code in seen_codes:
            session.expunge(asset)
            continue

        existing = (
            session.query(VirtualAsset)
            .filter(VirtualAsset.asset_code == asset.asset_code)
            .first()
        )
        if existing:
            session.expunge(asset)
        else:
            seen_codes.add(asset.asset_code)
