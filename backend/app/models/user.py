from datetime import datetime
from decimal import Decimal
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import db


class User(db.Model):
    __tablename__ = "user"

    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_name = db.Column(db.String(64), nullable=False)
    virtual_address = db.Column(db.String(128), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    register_time = db.Column(db.DateTime, default=datetime.now)
    total_asset = db.Column(db.Numeric(precision=20, scale=4), default=Decimal("10000"))

    pledges = db.relationship("Pledge", backref="user", lazy=True)
    loans = db.relationship("Loan", backref="user", lazy=True)
    repayments = db.relationship("Repayment", backref="user", lazy=True)
    liquidations = db.relationship("Liquidation", backref="user", lazy=True)

    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password, raw_password)

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "virtual_address": self.virtual_address,
            "register_time": self.register_time.isoformat() if self.register_time else None,
            "total_asset": str(self.total_asset),
        }
