from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.services import oracle_service
from app.utils.response import error, success


oracle_bp = Blueprint("oracle", __name__, url_prefix="/api/oracle")


@oracle_bp.route("/overview", methods=["GET"])
@jwt_required()
def overview():
    return success(oracle_service.get_global_overview())


@oracle_bp.route("/feed", methods=["POST"])
@jwt_required()
def feed():
    result, err = oracle_service.feed_prices(request.get_json(silent=True))
    if err:
        return error(err)
    return success(result, "全局喂价与风控扫描完成")
