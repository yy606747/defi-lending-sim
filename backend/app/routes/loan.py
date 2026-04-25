from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services import loan_service
from app.utils.response import success, error

loan_bp = Blueprint("loan", __name__, url_prefix="/api/loan")


@loan_bp.route("/create", methods=["POST"])
@jwt_required()
def create():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if not data:
        return error("请求数据为空")
    asset_id = data.get("asset_id")
    loan_amount = data.get("loan_amount")
    loan_term = data.get("loan_term")
    if not all([asset_id, loan_amount, loan_term]):
        return error("资产ID、借贷金额和期限不能为空")
    result, err = loan_service.create_loan(user_id, asset_id, loan_amount, int(loan_term))
    if err:
        return error(err)
    return success(result, "借贷成功")


@loan_bp.route("/list", methods=["GET"])
@jwt_required()
def get_list():
    user_id = int(get_jwt_identity())
    return success(loan_service.get_loans(user_id))


@loan_bp.route("/rate", methods=["GET"])
@jwt_required()
def get_rate():
    asset_id = request.args.get("asset_id", type=int)
    if not asset_id:
        return error("资产ID不能为空")
    result, err = loan_service.get_asset_rates(asset_id)
    if err:
        return error(err)
    return success(result)
