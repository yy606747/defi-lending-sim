from decimal import Decimal

import pytest

from app.models import db
from app.models.liquidation import Liquidation
from app.models.loan import Loan
from app.models.pledge import Pledge
from app.services import liquidation_service


@pytest.mark.financial
def test_risk_without_debt_is_low_and_uses_sentinel_ratio(app, make_user, assets, make_pledge):
    user = make_user()
    make_pledge(user, assets["ETH"], amount="1")

    result = liquidation_service.check_liquidation_risk(user.user_id)

    assert len(result) == 1
    assert result[0]["risk_level"] == "low"
    assert result[0]["collateral_ratio"] == "9999.0000"
    assert result[0]["total_debt"] == "0.0000"


@pytest.mark.financial
def test_risk_at_eth_liquidation_threshold_is_not_high(app, make_user, assets, make_pledge, make_loan):
    user = make_user()
    assets["ETH"].current_price = Decimal("1150.0000")
    db.session.commit()
    make_pledge(user, assets["ETH"], amount="1")
    make_loan(user, assets["ETH"], amount="1000", remaining="1000")

    result = liquidation_service.check_liquidation_risk(user.user_id)

    assert result[0]["collateral_ratio"] == "1.1500"
    assert result[0]["risk_level"] != "high"


@pytest.mark.financial
@pytest.mark.regression
def test_risk_just_below_liquidation_threshold_is_high_before_rounding(
    app,
    make_user,
    assets,
    make_pledge,
    make_loan,
):
    user = make_user()
    assets["ETH"].current_price = Decimal("1149.9900")
    db.session.commit()
    make_pledge(user, assets["ETH"], amount="1")
    make_loan(user, assets["ETH"], amount="1000", remaining="1000")

    result = liquidation_service.check_liquidation_risk(user.user_id)

    assert result[0]["risk_level"] == "high"


@pytest.mark.financial
def test_execute_liquidation_refuses_safe_position_at_boundary(
    app,
    make_user,
    assets,
    make_pledge,
    make_loan,
):
    user = make_user()
    assets["ETH"].current_price = Decimal("1150.0000")
    db.session.commit()
    pledge = make_pledge(user, assets["ETH"], amount="1")
    loan = make_loan(user, assets["ETH"], amount="1000", remaining="1000")

    result, err = liquidation_service.execute_liquidation(pledge.pledge_id, user.user_id)

    assert result is None
    assert "健康因子未低于1" in err
    db.session.refresh(pledge)
    db.session.refresh(loan)
    assert pledge.pledge_status == "active"
    assert loan.repay_status == "unpaid"


@pytest.mark.financial
def test_execute_liquidation_marks_pledge_loans_and_record_when_unsafe(
    app,
    make_user,
    assets,
    make_pledge,
    make_loan,
):
    user = make_user()
    assets["ETH"].current_price = Decimal("1000.0000")
    db.session.commit()
    pledge = make_pledge(user, assets["ETH"], amount="1")
    loan = make_loan(user, assets["ETH"], amount="1000", remaining="1000")

    result, err = liquidation_service.execute_liquidation(pledge.pledge_id, user.user_id)

    assert err is None
    assert result["liquidation_price"] == "1000.0000"
    assert result["liquidation_amount"] == "1000.0000"
    assert result["debt_repaid"] == "952.3810"
    assert result["bad_debt"] == "47.6190"
    db.session.refresh(pledge)
    db.session.refresh(loan)
    assert pledge.pledge_status == "liquidated"
    assert loan.repay_status == "partial"
    assert loan.remaining_principal == Decimal("47.6190")
    assert Liquidation.query.count() == 1


def test_execute_liquidation_rejects_other_user(app, make_user, assets, make_pledge):
    owner = make_user()
    other = make_user()
    pledge = make_pledge(owner, assets["ETH"], amount="1")

    result, err = liquidation_service.execute_liquidation(pledge.pledge_id, other.user_id)

    assert result is None
    assert err == "质押记录不存在或不属于该用户"


def test_execute_liquidation_rejects_inactive_pledge(app, make_user, assets, make_pledge):
    user = make_user()
    pledge = make_pledge(user, assets["ETH"], amount="1", status="unlocked")

    result, err = liquidation_service.execute_liquidation(pledge.pledge_id, user.user_id)

    assert result is None
    assert err == "该质押不处于活跃状态"


def test_execute_liquidation_rejects_user_without_debt(app, make_user, assets, make_pledge):
    user = make_user()
    pledge = make_pledge(user, assets["ETH"], amount="1")

    result, err = liquidation_service.execute_liquidation(pledge.pledge_id, user.user_id)

    assert result is None
    assert err == "用户无未还借款，无需清算"


@pytest.mark.financial
def test_borrowing_exact_available_amount_never_makes_available_negative(
    app,
    make_user,
    assets,
    make_pledge,
):
    from app.services import loan_service

    user = make_user()
    pledge = make_pledge(user, assets["ETH"], amount="1", available_loan_amount="100")

    result, err = loan_service.create_loan(user.user_id, assets["ETH"].asset_id, "100", 30)

    assert err is None
    assert result["loan_amount"] == "100.0000"
    db.session.refresh(pledge)
    assert pledge.available_loan_amount == Decimal("2300.0000")


@pytest.mark.financial
def test_failed_overborrow_preserves_total_available_and_loan_count(
    app,
    make_user,
    assets,
    make_pledge,
):
    from app.services import loan_service

    user = make_user()
    make_pledge(user, assets["ETH"], amount="1", available_loan_amount="100")

    result, err = loan_service.create_loan(user.user_id, assets["ETH"].asset_id, "2400.0001", 30)

    assert result is None
    assert "可借额度不足" in err
    pledges = Pledge.query.filter_by(user_id=user.user_id).all()
    assert sum(p.available_loan_amount for p in pledges) == Decimal("100.0000")
    assert Loan.query.count() == 0


@pytest.mark.financial
def test_completed_liquidation_global_debt_invariant(app, make_user, assets, make_pledge, make_loan):
    user = make_user()
    assets["ETH"].current_price = Decimal("1000.0000")
    db.session.commit()
    pledge = make_pledge(user, assets["ETH"], amount="1")
    make_loan(user, assets["ETH"], amount="600", remaining="600")
    make_loan(user, assets["ETH"], amount="400", remaining="400")

    result, err = liquidation_service.execute_liquidation(pledge.pledge_id, user.user_id)

    assert err is None
    assert result["liquidation_status"] == "completed"
    remaining_debt = sum(loan.remaining_principal for loan in Loan.query.filter_by(user_id=user.user_id))
    assert remaining_debt == Decimal("47.6190")
