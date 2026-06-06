from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services import simulation_service
from app.utils.response import success, error

simulation_bp = Blueprint("simulation", __name__, url_prefix="/api/simulation")


@simulation_bp.route("/price-history/<int:asset_id>", methods=["GET"])
@jwt_required()
def price_history(asset_id):
    result, err = simulation_service.get_price_history(asset_id)
    if err:
        return error(err)
    return success(result)


@simulation_bp.route("/statistics", methods=["GET"])
@jwt_required()
def statistics():
    return success(simulation_service.get_statistics())


@simulation_bp.route("/advance-time", methods=["POST"])
@jwt_required()
def advance_time():
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    days = data.get("days", 1)
    result, err = simulation_service.advance_time(user_id, days)
    if err:
        return error(err)
    return success(result, "时间快进完成")
