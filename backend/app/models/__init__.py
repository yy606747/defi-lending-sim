from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from app.models.user import User
from app.models.asset import VirtualAsset
from app.models.pledge import Pledge
from app.models.loan import Loan
from app.models.repayment import Repayment
from app.models.liquidation import Liquidation
