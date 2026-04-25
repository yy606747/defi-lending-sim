from flask import Blueprint
from flask_jwt_extended import jwt_required
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
