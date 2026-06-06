import pytest


@pytest.mark.integration
def test_full_user_pledge_loan_repayment_flow(client, assets):
    register = client.post(
        "/api/user/register",
        json={"user_name": "scenario", "virtual_address": "0xSCENARIO", "password": "abc12345"},
    )
    assert register.status_code == 200

    login = client.post(
        "/api/user/login",
        json={"virtual_address": "0xSCENARIO", "password": "abc12345"},
    )
    token = login.get_json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    asset_list = client.get("/api/asset/list")
    assert asset_list.status_code == 200
    assert {asset["asset_code"] for asset in asset_list.get_json()["data"]} == {"ETH", "BTC", "USDT"}

    pledge = client.post(
        "/api/pledge/create",
        json={"asset_id": assets["ETH"].asset_id, "pledge_amount": "1"},
        headers=headers,
    )
    assert pledge.status_code == 200
    assert pledge.get_json()["data"]["available_loan_amount"] == "2400.0000"

    loan = client.post(
        "/api/loan/create",
        json={"asset_id": assets["ETH"].asset_id, "loan_amount": "100", "loan_term": 30},
        headers=headers,
    )
    assert loan.status_code == 200
    loan_id = loan.get_json()["data"]["loan_id"]

    repayment = client.post(
        "/api/repayment/create",
        json={"loan_id": loan_id, "repayment_amount": "40"},
        headers=headers,
    )
    assert repayment.status_code == 200
    assert repayment.get_json()["data"]["repayment_type"] == "early"

    loans = client.get("/api/loan/list", headers=headers)
    assert loans.status_code == 200
    assert loans.get_json()["data"][0]["remaining_principal"] == "60.0000"


@pytest.mark.integration
@pytest.mark.parametrize(
    "method, url, payload",
    [
        ("post", "/api/asset/simulate", {}),
        ("post", "/api/pledge/create", {"asset_id": 1, "pledge_amount": "1"}),
        ("post", "/api/loan/create", {"asset_id": 1, "loan_amount": "1", "loan_term": 30}),
        ("post", "/api/repayment/create", {"loan_id": 1, "repayment_amount": "1"}),
        ("get", "/api/liquidation/risk", None),
        ("post", "/api/liquidation/execute", {"pledge_id": 1}),
        ("get", "/api/simulation/statistics", None),
        ("post", "/api/simulation/advance-time", {"days": 30}),
        ("get", "/api/oracle/overview", None),
        ("post", "/api/oracle/feed", [{"asset_id": 1, "current_price": "1000"}]),
    ],
)
def test_financial_endpoints_require_authentication(client, method, url, payload):
    request = getattr(client, method)
    kwargs = {"json": payload} if payload is not None else {}

    response = request(url, **kwargs)

    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.parametrize(
    "url, payload, expected_message",
    [
        ("/api/pledge/create", {}, "请求数据为空"),
        ("/api/pledge/create", {"asset_id": 1}, "资产ID和质押数量不能为空"),
        ("/api/loan/create", {}, "请求数据为空"),
        ("/api/loan/create", {"asset_id": 1, "loan_amount": "1"}, "资产ID、借贷金额和期限不能为空"),
        ("/api/repayment/create", {}, "请求数据为空"),
        ("/api/repayment/create", {"loan_id": 1}, "借贷ID和还款金额不能为空"),
        ("/api/liquidation/execute", {}, "请求数据为空"),
        ("/api/liquidation/execute", {"pledge_id": 0}, "质押ID不能为空"),
    ],
)
def test_authenticated_financial_endpoints_reject_missing_fields(
    client,
    make_user,
    make_auth_headers,
    url,
    payload,
    expected_message,
):
    user = make_user()

    response = client.post(url, json=payload, headers=make_auth_headers(user))

    assert response.status_code == 400
    assert response.get_json()["message"] == expected_message


@pytest.mark.integration
def test_statistics_api_uses_unified_success_envelope(client, make_user, make_auth_headers):
    user = make_user()

    response = client.get("/api/simulation/statistics", headers=make_auth_headers(user))

    assert response.status_code == 200
    body = response.get_json()
    assert set(body.keys()) == {"code", "message", "data"}
    assert body["code"] == 200
    assert body["message"] == "success"


@pytest.mark.integration
def test_advance_time_api_accrues_interest(client, make_user, make_auth_headers, assets, make_loan):
    user = make_user()
    make_loan(user, assets["ETH"], amount="1000", rate="0.05", term=365, remaining="1000")

    response = client.post(
        "/api/simulation/advance-time",
        json={"days": 30},
        headers=make_auth_headers(user),
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["data"]["interest_accrued"] == "4.1096"
