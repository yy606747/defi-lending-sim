from datetime import datetime
from app.models import db


class Liquidation(db.Model):
    __tablename__ = "liquidation"

    liquidation_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"), nullable=False)
    pledge_id = db.Column(db.Integer, db.ForeignKey("pledge.pledge_id"), nullable=False)
    liquidation_price = db.Column(db.Numeric(precision=20, scale=4), nullable=False)
    liquidation_amount = db.Column(db.Numeric(precision=20, scale=4), nullable=False)
    liquidation_time = db.Column(db.DateTime, default=datetime.now)
    liquidation_status = db.Column(db.String(16), nullable=False)

    def to_dict(self):
        return {
            "liquidation_id": self.liquidation_id,
            "user_id": self.user_id,
            "pledge_id": self.pledge_id,
            "liquidation_price": str(self.liquidation_price),
            "liquidation_amount": str(self.liquidation_amount),
            "liquidation_time": self.liquidation_time.isoformat() if self.liquidation_time else None,
            "liquidation_status": self.liquidation_status,
        }
