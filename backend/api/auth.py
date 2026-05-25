"""用户认证模块API"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from database.database import get_db
from database.models import User, SmsCode
from schemas.user import UserRegister, UserLogin, UserUpdate, PasswordReset, SmsSend
from services.auth_service import send_sms_code, verify_sms_code, register_user, login_user
from utils.response import success, error
from utils.security import decode_access_token

router = APIRouter(prefix="/api/auth", tags=["用户认证"])


def get_current_user(token: str = Depends(lambda: None), db: Session = Depends(get_db)):
    """通用令牌验证依赖（同时支持Header和Query参数）"""
    return token, db


@router.post("/send-sms", summary="发送短信验证码")
async def api_send_sms(body: SmsSend, db: Session = Depends(get_db)):
    """发送6位模拟验证码到手机（控制台打印）"""
    try:
        code = send_sms_code(db, body.phone)
        return success({"code": code}, "验证码已发送")
    except ValueError as e:
        return error(str(e))

@router.post("/register", summary="用户注册")
async def api_register(body: UserRegister, db: Session = Depends(get_db)):
    """雇主/从业者注册"""
    try:
        # 从业者注册需要短信验证
        if body.role == "worker" and body.sms_code:
            if not verify_sms_code(db, body.phone, body.sms_code):
                return error("验证码错误或已过期")
        user = register_user(db, body.phone, body.password, body.role, body.nickname)
        return success({
            "id": user.id,
            "phone": user.phone,
            "role": user.role,
            "nickname": user.nickname,
        }, "注册成功")
    except ValueError as e:
        return error(str(e))

@router.post("/login", summary="用户登录")
async def api_login(body: UserLogin, db: Session = Depends(get_db)):
    """手机号+密码登录，返回JWT令牌"""
    try:
        result = login_user(db, body.phone, body.password)
        return success(result, "登录成功")
    except ValueError as e:
        return error(str(e))

@router.get("/profile", summary="获取个人信息")
async def api_get_profile(
    token: str = Depends(lambda h: None),
    db: Session = Depends(get_db)
):
    """通过Header Authorization获取当前用户信息"""
    from fastapi import Header
    return error("请通过 /api/auth/profile-with-token 或 Header Authorization 访问")

@router.get("/profile-by-token", summary="获取个人信息(带token参数)")
async def api_get_profile_by_token(token: str, db: Session = Depends(get_db)):
    """通过token参数获取当前用户信息"""
    payload = decode_access_token(token)
    if not payload:
        return error("令牌无效或已过期", 401)
    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if not user:
        return error("用户不存在", 404)
    return success({
        "id": user.id,
        "phone": user.phone,
        "role": user.role,
        "nickname": user.nickname,
        "avatar": user.avatar,
        "real_name": user.real_name,
        "gender": user.gender,
        "address": user.address,
        "family_members": user.family_members,
        "house_type": user.house_type,
        "schedule": user.schedule,
        "has_elderly": user.has_elderly,
        "has_children": user.has_children,
        "has_pet": user.has_pet,
        "skills": user.skills,
        "experience_years": user.experience_years,
        "good_at": user.good_at,
        "work_time": user.work_time,
        "credit_score": user.credit_score,
        "risk_level": user.risk_level,
        "created_at": str(user.created_at),
    })

@router.put("/profile", summary="修改个人信息")
async def api_update_profile(
    body: UserUpdate,
    token: str,
    db: Session = Depends(get_db)
):
    """更新用户资料和画像"""
    payload = decode_access_token(token)
    if not payload:
        return error("令牌无效", 401)
    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if not user:
        return error("用户不存在", 404)

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)
    db.commit()
    return success(None, "资料更新成功")

@router.post("/reset-password", summary="重置密码")
async def api_reset_password(body: PasswordReset, db: Session = Depends(get_db)):
    """通过短信验证码重置密码"""
    if not verify_sms_code(db, body.phone, body.sms_code):
        return error("验证码错误或已过期")
    user = db.query(User).filter(User.phone == body.phone).first()
    if not user:
        return error("用户不存在")
    from utils.security import hash_password
    user.password = hash_password(body.new_password)
    db.commit()
    return success(None, "密码重置成功")
