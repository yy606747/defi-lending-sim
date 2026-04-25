from decimal import Decimal
from flask_jwt_extended import create_access_token
from app.models import db
from app.models.user import User


def register(user_name, virtual_address, password):
    if User.query.filter_by(virtual_address=virtual_address).first():
        return None, "该虚拟地址已被注册"
    user = User(user_name=user_name, virtual_address=virtual_address, total_asset=Decimal("10000"))
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user.to_dict(), None


def login(virtual_address, password):
    user = User.query.filter_by(virtual_address=virtual_address).first()
    if not user or not user.check_password(password):
        return None, "虚拟地址或密码错误"
    token = create_access_token(identity=str(user.user_id))
    return {"token": token, "user": user.to_dict()}, None


def get_info(user_id):
    user = User.query.get(user_id)
    if not user:
        return None, "用户不存在"
    return user.to_dict(), None


def update_info(user_id, data):
    user = User.query.get(user_id)
    if not user:
        return None, "用户不存在"
    if "user_name" in data:
        user.user_name = data["user_name"]
    db.session.commit()
    return user.to_dict(), None
