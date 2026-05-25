"""用户认证服务"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database.models import User, SmsCode
from utils.security import hash_password, verify_password, create_access_token, generate_sms_code
from utils.common import validate_phone


def send_sms_code(db: Session, phone: str) -> str:
    """发送短信验证码（模拟）"""
    if not validate_phone(phone):
        raise ValueError("手机号格式不正确")
    code = generate_sms_code()
    sms = SmsCode(phone=phone, code=code)
    db.add(sms)
    db.commit()
    # 实际场景：调用短信服务商API发送
    print(f"[模拟短信] 手机号{phone} 验证码: {code}")
    return code


def verify_sms_code(db: Session, phone: str, code: str) -> bool:
    """验证短信验证码（5分钟内有效）"""
    five_min_ago = datetime.utcnow() - timedelta(minutes=5)
    sms = db.query(SmsCode).filter(
        SmsCode.phone == phone,
        SmsCode.code == code,
        SmsCode.is_used == 0,
        SmsCode.created_at >= five_min_ago,
    ).order_by(SmsCode.created_at.desc()).first()
    if sms:
        sms.is_used = 1
        db.commit()
        return True
    return False


def register_user(db: Session, phone: str, password: str, role: str, nickname: str = None) -> User:
    """用户注册"""
    if db.query(User).filter(User.phone == phone).first():
        raise ValueError("该手机号已注册")
    user = User(
        phone=phone,
        password=hash_password(password),
        role=role,
        nickname=nickname or f"用户{phone[-4:]}",
        credit_score=80.0 if role == "worker" else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login_user(db: Session, phone: str, password: str) -> dict:
    """用户登录，返回JWT令牌"""
    user = db.query(User).filter(User.phone == phone, User.status == 1).first()
    if not user or not verify_password(password, user.password):
        raise ValueError("手机号或密码错误")
    token = create_access_token({"user_id": user.id, "role": user.role})
    return {
        "token": token,
        "user": {
            "id": user.id,
            "phone": user.phone,
            "role": user.role,
            "nickname": user.nickname,
            "avatar": user.avatar,
            "credit_score": user.credit_score,
        }
    }
