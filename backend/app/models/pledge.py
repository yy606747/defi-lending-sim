from datetime import datetime
from decimal import Decimal
from app.models import db


class Pledge(db.Model):
    __tablename__ = "pledge"

    pledge_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"), nullable=False)
    asset_id = db.Column(db.Integer, db.ForeignKey("virtual_asset.asset_id"), nullable=False)
    pledge_amount = db.Column(db.Numeric(precision=20, scale=4), nullable=False)
    pledge_time = db.Column(db.DateTime, default=datetime.now)
    pledge_rate = db.Column(db.Numeric(precision=10, scale=4), nullable=False)
    available_loan_amount = db.Column(db.Numeric(precision=20, scale=4), default=Decimal("0"))
    pledge_status = db.Column(db.String(16), default="active")  # 活跃 / 已清算 / 已解锁

    liquidation = db.relationship("Liquidation", backref="pledge", uselist=False, lazy=True)

    def to_dict(self):
        return {
            "pledge_id": self.pledge_id,
            "user_id": self.user_id,
            "asset_id": self.asset_id,
            "pledge_amount": str(self.pledge_amount),
            "pledge_time": self.pledge_time.isoformat() if self.pledge_time else None,
            "pledge_rate": str(self.pledge_rate),
            "available_loan_amount": str(self.available_loan_amount),
            "pledge_status": self.pledge_status,
        }
