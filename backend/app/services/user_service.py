from decimal import Decimal
from flask_jwt_extended import create_access_token
from app.models import db
from app.models.user import User


def _clean_text(value):
    return str(value or "").strip()


def _is_strong_password(password):
    return len(password) >= 6 and any(c.isalpha() for c in password) and any(c.isdigit() for c in password)


def register(user_name, virtual_address, password):
    user_name = _clean_text(user_name)
    virtual_address = _clean_text(virtual_address)
    password = _clean_text(password)
    if not all([user_name, virtual_address, password]):
        return None, "用户名、虚拟地址和密码不能为空"
    if not _is_strong_password(password):
        return None, "密码需至少6位且同时包含数字和字母"
    if User.query.filter_by(virtual_address=virtual_address).first():
        return None, "该虚拟地址已被注册"
    user = User(user_name=user_name, virtual_address=virtual_address, total_asset=Decimal("10000"))
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user.to_dict(), None


def login(virtual_address, password):
    virtual_address = _clean_text(virtual_address)
    password = _clean_text(password)
    if not all([virtual_address, password]):
        return None, "虚拟地址和密码不能为空"
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
        user_name = _clean_text(data["user_name"])
        if not user_name:
            return None, "用户名不能为空"
        user.user_name = user_name
    db.session.commit()
    return user.to_dict(), None
