from datetime import datetime
from app.models import db


class Repayment(db.Model):
    __tablename__ = "repayment"

    repayment_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    loan_id = db.Column(db.Integer, db.ForeignKey("loan.loan_id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"), nullable=False)
    repayment_amount = db.Column(db.Numeric(precision=20, scale=4), nullable=False)
    repayment_time = db.Column(db.DateTime, default=datetime.now)
    repayment_type = db.Column(db.String(16), nullable=False)  # early / due

    def to_dict(self):
        return {
            "repayment_id": self.repayment_id,
            "loan_id": self.loan_id,
            "user_id": self.user_id,
            "repayment_amount": str(self.repayment_amount),
            "repayment_time": self.repayment_time.isoformat() if self.repayment_time else None,
            "repayment_type": self.repayment_type,
        }
