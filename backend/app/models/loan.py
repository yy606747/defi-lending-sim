from datetime import datetime
from decimal import Decimal
from app.models import db


class Loan(db.Model):
    __tablename__ = "loan"

    loan_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"), nullable=False)
    asset_id = db.Column(db.Integer, db.ForeignKey("virtual_asset.asset_id"), nullable=False)
    loan_amount = db.Column(db.Numeric(precision=20, scale=4), nullable=False)
    loan_rate = db.Column(db.Numeric(precision=10, scale=6), nullable=False)
    loan_term = db.Column(db.Integer, nullable=False)  # 借款期限，单位：天
    loan_time = db.Column(db.DateTime, default=datetime.now)
    repay_status = db.Column(db.String(16), default="unpaid")  # 未还、部分还款、已还清
    remaining_principal = db.Column(db.Numeric(precision=20, scale=4), nullable=False)
    accrued_interest = db.Column(
        db.Numeric(precision=20, scale=4), nullable=False, default=Decimal("0")
    )
    last_accrual_time = db.Column(db.DateTime, default=datetime.now)

    repayments = db.relationship("Repayment", backref="loan", lazy=True)

    def to_dict(self):
        return {
            "loan_id": self.loan_id,
            "user_id": self.user_id,
            "asset_id": self.asset_id,
            "loan_amount": str(self.loan_amount),
            "loan_rate": str(self.loan_rate),
            "loan_term": self.loan_term,
            "loan_time": self.loan_time.isoformat() if self.loan_time else None,
            "repay_status": self.repay_status,
            "remaining_principal": str(self.remaining_principal),
            "accrued_interest": str(self.accrued_interest or Decimal("0")),
            "last_accrual_time": self.last_accrual_time.isoformat() if self.last_accrual_time else None,
        }
