from decimal import Decimal

import pytest

from app.models import db
from app.models.liquidation import Liquidation
from app.models.pledge import Pledge
from app.services import oracle_service


@pytest.mark.financial
@pytest.mark.regression
def test_oracle_rejects_unknown_asset_without_random_price_fallback(app, assets):
    old_prices = {code: asset.current_price for code, asset in assets.items()}

    result, err = oracle_service.feed_prices([
        {"asset_id": 999999, "current_price": "1234.0000"}
    ])

    assert result is None
    assert err == "资产不存在"
    for code, asset in assets.items():
        db.session.refresh(asset)
        assert asset.current_price == old_prices[code]


@pytest.mark.financial
def test_oracle_feed_triggers_global_liquidation_for_unhealthy_account(
    app,
    make_user,
    assets,
    make_pledge,
    make_loan,
):
    user = make_user(user_name="alice")
    pledge = make_pledge(user, assets["ETH"], amount="1")
    loan = make_loan(user, assets["ETH"], amount="1000", remaining="1000")

    result, err = oracle_service.feed_prices([
        {"asset_id": assets["ETH"].asset_id, "current_price": "1000.0000"}
    ])

    assert err is None
    assert result["assets"][0]["current_price"] == "1000.0000"
    assert len(result["at_risk_before"]) == 1
    assert result["at_risk_before"][0]["will_liquidate"] is True
    assert len(result["liquidations"]) == 1
    assert result["liquidations"][0]["pledge_id"] == pledge.pledge_id
    assert result["liquidations"][0]["debt_repaid"] == "952.3810"

    db.session.refresh(pledge)
    db.session.refresh(loan)
    assert pledge.pledge_status == "liquidated"
    assert loan.remaining_principal == Decimal("47.6190")
    assert Liquidation.query.count() == 1


@pytest.mark.financial
@pytest.mark.regression
def test_oracle_liquidates_highest_value_collateral_first_deterministically(
    app,
    make_user,
    assets,
    make_pledge,
    make_loan,
):
    user = make_user(user_name="bob")
    eth_pledge = make_pledge(user, assets["ETH"], amount="1")
    btc_pledge = make_pledge(user, assets["BTC"], amount="0.01")
    make_loan(user, assets["ETH"], amount="2000", remaining="2000")

    result, err = oracle_service.feed_prices([
        {"asset_id": assets["ETH"].asset_id, "current_price": "1000.0000"}
    ])

    assert err is None
    assert result["liquidations"][0]["pledge_id"] == eth_pledge.pledge_id
    assert result["liquidations"][0]["debt_repaid"] == "952.3810"

    db.session.refresh(eth_pledge)
    db.session.refresh(btc_pledge)
    assert eth_pledge.pledge_status == "liquidated"
    assert btc_pledge.pledge_status == "liquidated"
    assert Pledge.query.filter_by(user_id=user.user_id, pledge_status="active").count() == 0


@pytest.mark.integration
def test_oracle_feed_api_requires_auth_and_returns_global_envelope(
    client,
    make_user,
    make_auth_headers,
    assets,
):
    user = make_user()

    response = client.post(
        "/api/oracle/feed",
        json=[{"asset_id": assets["ETH"].asset_id, "current_price": "2900.0000"}],
        headers=make_auth_headers(user),
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["code"] == 200
    assert set(body["data"]) == {
        "assets",
        "at_risk_before",
        "liquidations",
        "at_risk",
        "stats",
        "recent_liquidations",
    }
