from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services import repayment_service
from app.utils.response import success, error

repayment_bp = Blueprint("repayment", __name__, url_prefix="/api/repayment")


@repayment_bp.route("/create", methods=["POST"])
@jwt_required()
def create():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if not data:
        return error("请求数据为空")
    loan_id = data.get("loan_id")
    repayment_amount = data.get("repayment_amount")
    if not loan_id or not repayment_amount:
        return error("借贷ID和还款金额不能为空")
    result, err = repayment_service.create_repayment(user_id, loan_id, repayment_amount)
    if err:
        return error(err)
    return success(result, "还款成功")


@repayment_bp.route("/list", methods=["GET"])
@jwt_required()
def get_list():
    user_id = int(get_jwt_identity())
    return success(repayment_service.get_repayments(user_id))
