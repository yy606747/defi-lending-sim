from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.models import db
from app.models.loan import Loan
from app.models.pledge import Pledge
from app.services import asset_service, loan_service, pledge_service, repayment_service, simulation_service


@pytest.mark.financial
@pytest.mark.parametrize(
    "asset_code, amount, expected_ltv, expected_available",
    [
        ("ETH", "1.5", "0.8000", "3600.0000"),
        ("BTC", "0.25", "0.7500", "11250.0000"),
        ("USDT", "1000", "0.9000", "900.0000"),
    ],
)
def test_create_pledge_calculates_borrow_power_by_asset_ltv(
    app,
    make_user,
    assets,
    asset_code,
    amount,
    expected_ltv,
    expected_available,
):
    user = make_user()

    result, err = pledge_service.create_pledge(user.user_id, assets[asset_code].asset_id, amount)

    assert err is None
    assert result["pledge_rate"] == expected_ltv
    assert result["available_loan_amount"] == expected_available
    assert result["pledge_status"] == "active"


@pytest.mark.parametrize("amount", ["0", "-0.0001"])
def test_create_pledge_rejects_zero_and_negative_amount(app, make_user, assets, amount):
    user = make_user()

    result, err = pledge_service.create_pledge(user.user_id, assets["ETH"].asset_id, amount)

    assert result is None
    assert err == "质押数量必须大于0"


@pytest.mark.regression
def test_create_pledge_rejects_non_numeric_amount_without_crashing(app, make_user, assets):
    user = make_user()

    result, err = pledge_service.create_pledge(user.user_id, assets["ETH"].asset_id, "not-a-number")

    assert result is None
    assert "质押数量" in err


@pytest.mark.regression
def test_create_pledge_rejects_unknown_user_id(app, assets):
    result, err = pledge_service.create_pledge(999999, assets["ETH"].asset_id, "1")

    assert result is None
    assert err == "用户不存在"


def test_get_pledges_includes_asset_metadata_and_current_value(app, make_user, assets, make_pledge):
    user = make_user()
    make_pledge(user, assets["ETH"], amount="2", pledge_rate="0.80", available_loan_amount="100")

    result = pledge_service.get_pledges(user.user_id)

    assert len(result) == 1
    assert result[0]["asset_name"] == "Ethereum"
    assert result[0]["asset_code"] == "ETH"
    assert result[0]["current_price"] == "3000.0000"
    assert result[0]["current_value"] == "6000.0000"


def test_unlock_pledge_without_debt_succeeds(app, make_user, assets, make_pledge):
    user = make_user()
    pledge = make_pledge(user, assets["ETH"], amount="1")

    result, err = pledge_service.unlock_pledge(pledge.pledge_id, user.user_id)

    assert err is None
    assert result["pledge_status"] == "unlocked"


def test_unlock_pledge_rejects_other_user(app, make_user, assets, make_pledge):
    owner = make_user()
    other = make_user()
    pledge = make_pledge(owner, assets["ETH"], amount="1")

    result, err = pledge_service.unlock_pledge(pledge.pledge_id, other.user_id)

    assert result is None
    assert err == "质押记录不存在"


@pytest.mark.financial
def test_unlock_pledge_rejects_if_remaining_collateral_cannot_cover_debt(
    app,
    make_user,
    assets,
    make_pledge,
    make_loan,
):
    user = make_user()
    pledge = make_pledge(user, assets["ETH"], amount="1", available_loan_amount="2400")
    make_pledge(user, assets["USDT"], amount="100", available_loan_amount="90")
    make_loan(user, assets["ETH"], amount="1000", remaining="1000")

    result, err = pledge_service.unlock_pledge(pledge.pledge_id, user.user_id)

    assert result is None
    assert "剩余的质押物不足" in err


@pytest.mark.financial
def test_unlock_pledge_allows_when_remaining_collateral_covers_debt(
    app,
    make_user,
    assets,
    make_pledge,
    make_loan,
):
    user = make_user()
    pledge = make_pledge(user, assets["USDT"], amount="100", available_loan_amount="90")
    make_pledge(user, assets["ETH"], amount="1", available_loan_amount="2400")
    make_loan(user, assets["ETH"], amount="1000", remaining="1000")

    result, err = pledge_service.unlock_pledge(pledge.pledge_id, user.user_id)

    assert err is None
    assert result["pledge_status"] == "unlocked"


@pytest.mark.financial
@pytest.mark.parametrize(
    "term, expected",
    [
        (30, "0.0180"),
        (31, "0.0200"),
        (90, "0.0200"),
        (91, "0.0240"),
    ],
)
def test_get_current_rate_term_boundaries(app, assets, term, expected):
    assert loan_service.get_current_rate(term, assets["ETH"].asset_id) == expected


@pytest.mark.financial
def test_create_loan_deducts_available_amount_across_pledges(app, make_user, assets, make_pledge):
    user = make_user()
    first = make_pledge(user, assets["ETH"], amount="1", available_loan_amount="100")
    second = make_pledge(user, assets["ETH"], amount="1", available_loan_amount="200")

    result, err = loan_service.create_loan(user.user_id, assets["ETH"].asset_id, "250", 30)

    assert err is None
    assert result["remaining_principal"] == "250.0000"
    db.session.refresh(first)
    db.session.refresh(second)
    assert first.available_loan_amount == Decimal("2275.0000")
    assert second.available_loan_amount == Decimal("2275.0000")


@pytest.mark.financial
def test_create_loan_rejects_amount_above_available_without_mutating(
    app,
    make_user,
    assets,
    make_pledge,
):
    user = make_user()
    pledge = make_pledge(user, assets["ETH"], amount="1", available_loan_amount="100")

    result, err = loan_service.create_loan(user.user_id, assets["ETH"].asset_id, "2400.0001", 30)

    assert result is None
    assert "可借额度不足" in err
    db.session.refresh(pledge)
    assert pledge.available_loan_amount == Decimal("100.0000")
    assert Loan.query.count() == 0


@pytest.mark.financial
@pytest.mark.regression
def test_create_loan_uses_live_oracle_price_after_price_drop(app, make_user, assets):
    user = make_user()
    pledge_service.create_pledge(user.user_id, assets["ETH"].asset_id, "1")
    asset_service.simulate_price_change(
        [{"asset_id": assets["ETH"].asset_id, "current_price": "1000"}]
    )

    result, err = loan_service.create_loan(user.user_id, assets["ETH"].asset_id, "800.0001", 30)

    assert result is None
    assert "可借额度不足" in err


@pytest.mark.parametrize("amount", ["0", "-1"])
def test_create_loan_rejects_zero_and_negative_amount(app, make_user, assets, amount):
    user = make_user()

    result, err = loan_service.create_loan(user.user_id, assets["ETH"].asset_id, amount, 30)

    assert result is None
    assert err == "借贷金额必须大于0"


@pytest.mark.regression
@pytest.mark.parametrize("term", [0, -1])
def test_create_loan_rejects_zero_and_negative_terms(app, make_user, assets, make_pledge, term):
    user = make_user()
    make_pledge(user, assets["ETH"], amount="1", available_loan_amount="100")

    result, err = loan_service.create_loan(user.user_id, assets["ETH"].asset_id, "10", term)

    assert result is None
    assert err == "借贷期限必须大于0"


@pytest.mark.regression
def test_create_loan_rejects_non_numeric_amount_without_crashing(app, make_user, assets):
    user = make_user()

    result, err = loan_service.create_loan(user.user_id, assets["ETH"].asset_id, "NaN yuan", 30)

    assert result is None
    assert "借贷金额" in err


@pytest.mark.financial
def test_get_loans_uses_accrued_interest_total_repay(app, make_user, assets, make_loan):
    user = make_user()
    make_loan(
        user,
        assets["ETH"],
        amount="1000",
        rate="0.05",
        term=365,
        remaining="400",
        accrued_interest="50",
        status="partial",
    )

    result = loan_service.get_loans(user.user_id)

    assert result[0]["total_repay"] == "450.0000"
    assert result[0]["asset_code"] == "ETH"


@pytest.mark.financial
@pytest.mark.regression
def test_get_loans_is_read_only_and_does_not_accrue_interest(app, make_user, assets, make_loan):
    user = make_user()
    fixed_time = datetime.now() - timedelta(days=30)
    loan = make_loan(
        user,
        assets["ETH"],
        amount="1000",
        rate="0.05",
        term=365,
        remaining="1000",
        loan_time=fixed_time,
        last_accrual_time=fixed_time,
    )

    loan_service.get_loans(user.user_id)

    db.session.refresh(loan)
    assert loan.accrued_interest == Decimal("0.0000")
    assert loan.last_accrual_time == fixed_time


@pytest.mark.financial
@pytest.mark.regression
def test_advance_time_accrues_interest_without_overwriting_loan_rate(app, make_user, assets, make_loan):
    user = make_user()
    loan = make_loan(
        user,
        assets["ETH"],
        amount="1000",
        rate="0.05",
        term=365,
        remaining="1000",
    )

    result, err = simulation_service.advance_time(user.user_id, "30")

    assert err is None
    assert result["interest_accrued"] == "4.1096"
    db.session.refresh(loan)
    assert loan.accrued_interest == Decimal("4.1096")
    assert loan.loan_rate == Decimal("0.050000")


@pytest.mark.parametrize("days", ["3650.0001", "10000000"])
def test_advance_time_rejects_days_above_limit_without_mutating_loan(
    app, make_user, assets, make_loan, days
):
    user = make_user()
    loan = make_loan(user, assets["ETH"], amount="1000", rate="0.05")
    original_accrual_time = loan.last_accrual_time

    result, err = simulation_service.advance_time(user.user_id, days)

    assert result is None
    assert err == "单次快进天数不能超过3650天"
    db.session.refresh(loan)
    assert loan.accrued_interest == Decimal("0.0000")
    assert loan.last_accrual_time == original_accrual_time


def test_create_repayment_partial_and_paid_status(app, make_user, assets, make_loan):
    user = make_user()
    loan = make_loan(user, assets["ETH"], amount="100", remaining="100")

    first, err1 = repayment_service.create_repayment(user.user_id, loan.loan_id, "40")
    second, err2 = repayment_service.create_repayment(user.user_id, loan.loan_id, "60")

    assert err1 is None
    assert err2 is None
    assert first["repayment_amount"] == "40.0000"
    assert second["repayment_amount"] == "60.0000"
    db.session.refresh(loan)
    assert loan.remaining_principal == Decimal("0.0000")
    assert loan.repay_status == "paid"


@pytest.mark.financial
def test_create_repayment_pays_interest_before_principal(app, make_user, assets, make_loan):
    user = make_user()
    loan = make_loan(user, assets["ETH"], amount="100", remaining="100", accrued_interest="10")

    result, err = repayment_service.create_repayment(user.user_id, loan.loan_id, "10")

    assert err is None
    assert result["interest_paid"] == "10.0000"
    assert result["principal_paid"] == "0.0000"
    db.session.refresh(loan)
    assert loan.accrued_interest == Decimal("0.0000")
    assert loan.remaining_principal == Decimal("100.0000")
    assert loan.repay_status == "partial"


@pytest.mark.regression
@pytest.mark.financial
def test_create_repayment_rejects_overpayment(app, make_user, assets, make_loan):
    user = make_user()
    loan = make_loan(user, assets["ETH"], amount="100", remaining="50")

    result, err = repayment_service.create_repayment(user.user_id, loan.loan_id, "50.0001")

    assert result is None
    assert err == "还款金额不能超过待还本息"


@pytest.mark.parametrize(
    "loan_time, expected_type",
    [
        (datetime.now(), "early"),
        (datetime.now() - timedelta(days=31), "due"),
    ],
)
def test_create_repayment_assigns_early_or_due_type(
    app,
    make_user,
    assets,
    make_loan,
    loan_time,
    expected_type,
):
    user = make_user()
    loan = make_loan(user, assets["ETH"], amount="100", term=30, loan_time=loan_time)

    result, err = repayment_service.create_repayment(user.user_id, loan.loan_id, "1")

    assert err is None
    assert result["repayment_type"] == expected_type


@pytest.mark.financial
@pytest.mark.regression
def test_repayment_uses_advanced_virtual_time_for_due_type(
    app, make_user, assets, make_loan
):
    user = make_user()
    loan = make_loan(user, assets["ETH"], amount="100", rate="0.05", term=30)

    advance_result, advance_err = simulation_service.advance_time(user.user_id, "60")
    advanced_time = loan.last_accrual_time
    repayment_result, repayment_err = repayment_service.create_repayment(
        user.user_id, loan.loan_id, "1"
    )

    assert advance_err is None
    assert advance_result["interest_accrued"] == "0.8219"
    assert repayment_err is None
    assert repayment_result["repayment_type"] == "due"
    assert loan.last_accrual_time == advanced_time


def test_create_repayment_rejects_other_users_loan(app, make_user, assets, make_loan):
    owner = make_user()
    other = make_user()
    loan = make_loan(owner, assets["ETH"], amount="100")

    result, err = repayment_service.create_repayment(other.user_id, loan.loan_id, "1")

    assert result is None
    assert err == "借贷记录不存在"


@pytest.mark.regression
def test_create_repayment_rejects_non_numeric_amount_without_crashing(app, make_user, assets, make_loan):
    user = make_user()
    loan = make_loan(user, assets["ETH"], amount="100")

    result, err = repayment_service.create_repayment(user.user_id, loan.loan_id, "ten")

    assert result is None
    assert "还款金额" in err


@pytest.mark.integration
@pytest.mark.regression
def test_loan_create_api_rejects_non_numeric_term(client, make_user, make_auth_headers, assets, make_pledge):
    user = make_user()
    make_pledge(user, assets["ETH"], amount="1", available_loan_amount="100")

    response = client.post(
        "/api/loan/create",
        json={"asset_id": assets["ETH"].asset_id, "loan_amount": "10", "loan_term": "abc"},
        headers=make_auth_headers(user),
    )

    assert response.status_code == 400
    assert response.get_json()["code"] == 400
