from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services import liquidation_service
from app.utils.response import success, error

liquidation_bp = Blueprint("liquidation", __name__, url_prefix="/api/liquidation")


@liquidation_bp.route("/risk", methods=["GET"])
@jwt_required()
def risk():
    user_id = int(get_jwt_identity())
    return success(liquidation_service.check_liquidation_risk(user_id))


@liquidation_bp.route("/execute", methods=["POST"])
@jwt_required()
def execute():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if not data:
        return error("请求数据为空")
    pledge_id = data.get("pledge_id")
    if not pledge_id:
        return error("质押ID不能为空")
    result, err = liquidation_service.execute_liquidation(pledge_id, user_id)
    if err:
        return error(err)
    return success(result, "清算执行完成")


@liquidation_bp.route("/list", methods=["GET"])
@jwt_required()
def get_list():
    user_id = int(get_jwt_identity())
    return success(liquidation_service.get_liquidations(user_id))
