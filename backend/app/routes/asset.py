from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from app.services import asset_service
from app.utils.response import success, error

asset_bp = Blueprint("asset", __name__, url_prefix="/api/asset")


@asset_bp.route("/list", methods=["GET"])
def get_all():
    return success(asset_service.get_all_assets())


@asset_bp.route("/<int:asset_id>", methods=["GET"])
def get_one(asset_id):
    result, err = asset_service.get_asset(asset_id)
    if err:
        return error(err)
    return success(result)


@asset_bp.route("/simulate", methods=["POST"])
@jwt_required()
def simulate():
    try:
        result = asset_service.simulate_price_change(request.get_json(silent=True))
    except ValueError as e:
        return error(str(e))
    return success(result, "价格模拟完成")
