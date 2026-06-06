from datetime import datetime
from decimal import Decimal
from itertools import count
from pathlib import Path
import sys

import pytest
from flask_jwt_extended import create_access_token

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.config import Config
from app.models import db
from app.models.asset import VirtualAsset
from app.models.liquidation import Liquidation
from app.models.loan import Loan
from app.models.pledge import Pledge
from app.models.repayment import Repayment
from app.models.user import User


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(
        Config,
        "SQLALCHEMY_DATABASE_URI",
        f"sqlite:///{tmp_path / 'defi-test.db'}",
    )
    monkeypatch.setattr(Config, "JWT_SECRET_KEY", "test-secret")
    monkeypatch.setattr(Config, "JWT_ACCESS_TOKEN_EXPIRES", 3600)

    application = create_app()
    application.config.update(TESTING=True)

    with application.app_context():
        db.create_all()
        seed_assets()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def seed_assets():
    assets = [
        VirtualAsset(
            asset_name="Ethereum",
            asset_code="ETH",
            current_price=Decimal("3000.0000"),
            price_volatility=Decimal("0.050000"),
        ),
        VirtualAsset(
            asset_name="Bitcoin",
            asset_code="BTC",
            current_price=Decimal("60000.0000"),
            price_volatility=Decimal("0.030000"),
        ),
        VirtualAsset(
            asset_name="Tether",
            asset_code="USDT",
            current_price=Decimal("1.0000"),
            price_volatility=Decimal("0.001000"),
        ),
    ]
    db.session.add_all(assets)
    db.session.commit()


@pytest.fixture()
def assets(app):
    return {asset.asset_code: asset for asset in VirtualAsset.query.all()}


@pytest.fixture()
def make_user(app):
    seq = count(1)

    def _make_user(
        user_name=None,
        virtual_address=None,
        password="abc12345",
        total_asset=Decimal("10000"),
    ):
        n = next(seq)
        user = User(
            user_name=user_name or f"user-{n}",
            virtual_address=virtual_address or f"0xUSER{n:04d}",
            total_asset=Decimal(str(total_asset)),
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    return _make_user


@pytest.fixture()
def make_auth_headers(app):
    def _headers(user):
        token = create_access_token(identity=str(user.user_id))
        return {"Authorization": f"Bearer {token}"}

    return _headers


@pytest.fixture()
def make_pledge(app):
    def _make_pledge(
        user,
        asset,
        amount="1",
        pledge_rate="0.80",
        available_loan_amount="0",
        status="active",
    ):
        pledge = Pledge(
            user_id=user.user_id,
            asset_id=asset.asset_id,
            pledge_amount=Decimal(str(amount)),
            pledge_rate=Decimal(str(pledge_rate)),
            available_loan_amount=Decimal(str(available_loan_amount)),
            pledge_status=status,
        )
        db.session.add(pledge)
        db.session.commit()
        return pledge

    return _make_pledge


@pytest.fixture()
def make_loan(app):
    def _make_loan(
        user,
        asset,
        amount="100",
        rate="0.05",
        term=30,
        remaining=None,
        accrued_interest="0",
        status="unpaid",
        loan_time=None,
        last_accrual_time=None,
    ):
        amount_dec = Decimal(str(amount))
        effective_loan_time = loan_time or datetime.now()
        loan = Loan(
            user_id=user.user_id,
            asset_id=asset.asset_id,
            loan_amount=amount_dec,
            loan_rate=Decimal(str(rate)),
            loan_term=term,
            repay_status=status,
            remaining_principal=Decimal(str(remaining)) if remaining is not None else amount_dec,
            accrued_interest=Decimal(str(accrued_interest)),
            loan_time=effective_loan_time,
            last_accrual_time=last_accrual_time or effective_loan_time,
        )
        db.session.add(loan)
        db.session.commit()
        return loan

    return _make_loan


@pytest.fixture()
def make_repayment(app):
    def _make_repayment(user, loan, amount="1", repayment_type="early"):
        repayment = Repayment(
            loan_id=loan.loan_id,
            user_id=user.user_id,
            repayment_amount=Decimal(str(amount)),
            repayment_type=repayment_type,
        )
        db.session.add(repayment)
        db.session.commit()
        return repayment

    return _make_repayment


@pytest.fixture()
def make_liquidation(app):
    def _make_liquidation(user, pledge, price="1", amount="1", status="completed"):
        liquidation = Liquidation(
            user_id=user.user_id,
            pledge_id=pledge.pledge_id,
            liquidation_price=Decimal(str(price)),
            liquidation_amount=Decimal(str(amount)),
            liquidation_status=status,
        )
        db.session.add(liquidation)
        db.session.commit()
        return liquidation

    return _make_liquidation
