from decimal import Decimal

import pytest

from app.models.user import User
from app.services import user_service


def test_register_hashes_password_and_initializes_total_asset(app):
    result, err = user_service.register("alice", "0xALICE", "abc12345")

    assert err is None
    assert result["virtual_address"] == "0xALICE"
    assert result["total_asset"] == "10000.0000"
    assert "password" not in result

    user = User.query.filter_by(virtual_address="0xALICE").one()
    assert user.password != "abc12345"
    assert user.check_password("abc12345")


def test_register_duplicate_virtual_address_rejected(app):
    assert user_service.register("alice", "0xDUP", "abc12345")[1] is None

    result, err = user_service.register("bob", "0xDUP", "abc12345")

    assert result is None
    assert err == "该虚拟地址已被注册"


@pytest.mark.parametrize(
    "payload, missing_message",
    [
        ({}, "请求数据为空"),
        ({"virtual_address": "0xA", "password": "abc12345"}, "用户名、虚拟地址和密码不能为空"),
        ({"user_name": "alice", "password": "abc12345"}, "用户名、虚拟地址和密码不能为空"),
        ({"user_name": "alice", "virtual_address": "0xA"}, "用户名、虚拟地址和密码不能为空"),
    ],
)
def test_register_api_rejects_missing_required_fields(client, payload, missing_message):
    response = client.post("/api/user/register", json=payload)

    assert response.status_code == 400
    body = response.get_json()
    assert body["code"] == 400
    assert body["message"] == missing_message


@pytest.mark.regression
@pytest.mark.parametrize(
    "payload",
    [
        {"user_name": "   ", "virtual_address": "0xBLANK1", "password": "abc12345"},
        {"user_name": "alice", "virtual_address": "   ", "password": "abc12345"},
    ],
)
def test_register_api_rejects_blank_strings(client, payload):
    response = client.post("/api/user/register", json=payload)

    assert response.status_code == 400
    assert response.get_json()["code"] == 400


@pytest.mark.regression
@pytest.mark.parametrize("password", ["1234", "abcdef", "a1"])
def test_register_api_enforces_password_policy_from_design_example(client, password):
    response = client.post(
        "/api/user/register",
        json={"user_name": "alice", "virtual_address": f"0xPWD{password}", "password": password},
    )

    assert response.status_code == 400
    assert response.get_json()["code"] == 400


def test_login_success_returns_jwt_and_sanitized_user(client):
    client.post(
        "/api/user/register",
        json={"user_name": "alice", "virtual_address": "0xLOGIN", "password": "abc12345"},
    )

    response = client.post(
        "/api/user/login",
        json={"virtual_address": "0xLOGIN", "password": "abc12345"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["code"] == 200
    assert body["data"]["token"]
    assert body["data"]["user"]["virtual_address"] == "0xLOGIN"
    assert "password" not in body["data"]["user"]


def test_login_wrong_password_rejected(client, make_user):
    make_user(virtual_address="0xBADPWD", password="abc12345")

    response = client.post(
        "/api/user/login",
        json={"virtual_address": "0xBADPWD", "password": "wrong"},
    )

    assert response.status_code == 400
    assert response.get_json()["message"] == "虚拟地址或密码错误"


def test_protected_info_requires_token(client):
    response = client.get("/api/user/info")

    assert response.status_code == 401


def test_get_info_returns_current_identity_only(client, make_user, make_auth_headers):
    alice = make_user(user_name="alice", virtual_address="0xINFO")
    make_user(user_name="bob", virtual_address="0xOTHER")

    response = client.get("/api/user/info", headers=make_auth_headers(alice))

    assert response.status_code == 200
    body = response.get_json()
    assert body["data"]["user_id"] == alice.user_id
    assert body["data"]["virtual_address"] == "0xINFO"


def test_update_info_changes_user_name_only(client, make_user, make_auth_headers):
    user = make_user(user_name="old", virtual_address="0xUPDATE", total_asset=Decimal("12345"))

    response = client.put(
        "/api/user/info",
        json={"user_name": "new", "total_asset": "0", "virtual_address": "0xHACK"},
        headers=make_auth_headers(user),
    )

    assert response.status_code == 200
    db_user = User.query.get(user.user_id)
    assert db_user.user_name == "new"
    assert db_user.total_asset == Decimal("12345.0000")
    assert db_user.virtual_address == "0xUPDATE"


@pytest.mark.regression
def test_update_info_rejects_blank_user_name(client, make_user, make_auth_headers):
    user = make_user(user_name="old", virtual_address="0xBLANKUPDATE")

    response = client.put(
        "/api/user/info",
        json={"user_name": "   "},
        headers=make_auth_headers(user),
    )

    assert response.status_code == 400
    assert response.get_json()["code"] == 400

