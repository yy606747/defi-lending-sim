from datetime import date
from decimal import Decimal

import pytest

from app.models import db
from app.models.asset import VirtualAsset
from app.services import asset_service, simulation_service


def test_get_all_assets_returns_seeded_assets(app):
    result = asset_service.get_all_assets()

    assert {asset["asset_code"] for asset in result} == {"ETH", "BTC", "USDT"}
    assert all(isinstance(asset["current_price"], str) for asset in result)


def test_get_asset_missing_returns_error(app):
    result, err = asset_service.get_asset(999999)

    assert result is None
    assert err == "资产不存在"


def test_simulate_price_change_quantizes_prices_and_keeps_usdt_bound(app, monkeypatch, assets):
    monkeypatch.setattr(asset_service.random, "gauss", lambda _mu, _sigma: 100)

    result = asset_service.simulate_price_change()

    by_code = {asset["asset_code"]: asset for asset in result}
    assert Decimal(by_code["ETH"]["current_price"]) > 0
    assert Decimal(by_code["BTC"]["current_price"]) > 0
    assert Decimal("0.9800") <= Decimal(by_code["USDT"]["current_price"]) <= Decimal("1.0200")
    assert Decimal(by_code["USDT"]["current_price"]).as_tuple().exponent == -4


def test_simulate_endpoint_requires_jwt(client):
    response = client.post("/api/asset/simulate")

    assert response.status_code == 401


@pytest.mark.financial
@pytest.mark.regression
@pytest.mark.parametrize("asset_code", ["ETH", "BTC", "USDT"])
def test_price_history_dates_and_prices_have_same_31_day_shape(app, assets, asset_code):
    result, err = simulation_service.get_price_history(assets[asset_code].asset_id)

    assert err is None
    assert len(result["dates"]) == 31
    assert len(result["prices"]) == 31
    assert len(result["dates"]) == len(result["prices"])
    assert result["dates"][-1] == date.today().isoformat()
    assert Decimal(str(result["prices"][-1])) == assets[asset_code].current_price


def test_price_history_is_deterministic_for_same_asset(app, assets):
    first, err1 = simulation_service.get_price_history(assets["ETH"].asset_id)
    second, err2 = simulation_service.get_price_history(assets["ETH"].asset_id)

    assert err1 is None
    assert err2 is None
    assert first["prices"] == second["prices"]
    assert first["dates"] == second["dates"]


@pytest.mark.financial
@pytest.mark.parametrize(
    "asset_code, utilization, expected",
    [
        ("ETH", Decimal("0"), Decimal("0.0200")),
        ("ETH", Decimal("0.80"), Decimal("0.0520")),
        ("ETH", Decimal("1.00"), Decimal("0.2020")),
        ("BTC", Decimal("0.80"), Decimal("0.0440")),
        ("USDT", Decimal("0.80"), Decimal("0.0720")),
    ],
)
def test_calculate_dynamic_rate_boundaries(asset_code, utilization, expected):
    assert simulation_service.calculate_dynamic_rate(asset_code, utilization) == expected


@pytest.mark.financial
@pytest.mark.regression
def test_calculate_dynamic_rate_never_goes_below_base_rate():
    rate = simulation_service.calculate_dynamic_rate("ETH", Decimal("-0.10"))

    assert rate >= Decimal("0.0200")


def test_statistics_empty_system_uses_zero_money_values(app):
    stats = simulation_service.get_statistics()

    assert stats["total_users"] == 0
    assert stats["total_pledge_value"] == "0.0000"
    assert stats["total_loan_amount"] == "0.0000"
    assert stats["total_liquidations"] == 0
    assert stats["utilization_rate"] == "0"
    assert stats["avg_dynamic_rate"] == "0"


@pytest.mark.financial
def test_statistics_counts_active_pledges_unpaid_loans_and_liquidations(
    app,
    make_user,
    assets,
    make_pledge,
    make_loan,
    make_liquidation,
):
    user = make_user()
    active = make_pledge(user, assets["ETH"], amount="2", available_loan_amount="1000")
    make_pledge(user, assets["BTC"], amount="1", status="unlocked")
    make_loan(user, assets["ETH"], amount="1000", remaining="400", status="partial")
    make_loan(user, assets["ETH"], amount="500", remaining="0", status="paid")
    make_liquidation(user, active, price="1000", amount="1000")

    stats = simulation_service.get_statistics()

    assert stats["total_users"] == 1
    assert stats["total_pledge_value"] == "6000.0000"
    assert stats["total_loan_amount"] == "400.0000"
    assert stats["total_liquidations"] == 1
    assert stats["utilization_rate"] == "0.0667"
    assert stats["avg_dynamic_rate"] == "0.0227"


@pytest.mark.integration
def test_price_history_api_rejects_unknown_asset(client, make_user, make_auth_headers):
    user = make_user()

    response = client.get("/api/simulation/price-history/9999", headers=make_auth_headers(user))

    assert response.status_code == 400
    assert response.get_json()["message"] == "资产不存在"


@pytest.mark.regression
def test_asset_code_is_not_unique_currently_exposed_by_data_model(app):
    duplicate = VirtualAsset(
        asset_name="Fake ETH",
        asset_code="ETH",
        current_price=Decimal("1"),
        price_volatility=Decimal("0.01"),
    )
    db.session.add(duplicate)
    db.session.commit()

    eth_assets = [asset for asset in asset_service.get_all_assets() if asset["asset_code"] == "ETH"]

    assert len(eth_assets) == 1
