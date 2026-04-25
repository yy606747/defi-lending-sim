from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services import pledge_service
from app.utils.response import success, error

pledge_bp = Blueprint("pledge", __name__, url_prefix="/api/pledge")


@pledge_bp.route("/create", methods=["POST"])
@jwt_required()
def create():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if not data:
        return error("请求数据为空")
    asset_id = data.get("asset_id")
    pledge_amount = data.get("pledge_amount")
    if not asset_id or not pledge_amount:
        return error("资产ID和质押数量不能为空")
    result, err = pledge_service.create_pledge(user_id, asset_id, pledge_amount)
    if err:
        return error(err)
    return success(result, "质押成功")


@pledge_bp.route("/list", methods=["GET"])
@jwt_required()
def get_list():
    user_id = int(get_jwt_identity())
    return success(pledge_service.get_pledges(user_id))


@pledge_bp.route("/unlock/<int:pledge_id>", methods=["POST"])
@jwt_required()
def unlock(pledge_id):
    user_id = int(get_jwt_identity())
    result, err = pledge_service.unlock_pledge(pledge_id, user_id)
    if err:
        return error(err)
    return success(result, "解锁成功")
