from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services import user_service
from app.utils.response import success, error

user_bp = Blueprint("user", __name__, url_prefix="/api/user")


@user_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    if not data:
        return error("请求数据为空")
    user_name = data.get("user_name")
    virtual_address = data.get("virtual_address")
    password = data.get("password")
    if not all([user_name, virtual_address, password]):
        return error("用户名、虚拟地址和密码不能为空")
    result, err = user_service.register(user_name, virtual_address, password)
    if err:
        return error(err)
    return success(result, "注册成功")


@user_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data:
        return error("请求数据为空")
    virtual_address = data.get("virtual_address")
    password = data.get("password")
    if not all([virtual_address, password]):
        return error("虚拟地址和密码不能为空")
    result, err = user_service.login(virtual_address, password)
    if err:
        return error(err)
    return success(result, "登录成功")


@user_bp.route("/info", methods=["GET"])
@jwt_required()
def get_info():
    user_id = int(get_jwt_identity())
    result, err = user_service.get_info(user_id)
    if err:
        return error(err)
    return success(result)


@user_bp.route("/info", methods=["PUT"])
@jwt_required()
def update_info():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if not data:
        return error("请求数据为空")
    result, err = user_service.update_info(user_id, data)
    if err:
        return error(err)
    return success(result, "更新成功")
