"""AI资质智能核验模块API"""
import json
import os
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from database.database import get_db
from database.models import User, Certification
from schemas.certification import CertReview
from services.ocr_service import recognize_certificate, verify_certificate_validity
from services.credit_service import calculate_credit_score, check_duplicate_cert
from utils.response import success, error
from utils.security import decode_access_token

router = APIRouter(prefix="/api/cert", tags=["AI资质核验"])

# 上传文件存储目录
UPLOAD_DIR = "uploads/certifications"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload", summary="上传证件并AI核验")
async def api_upload_cert(
    token: str = Form(...),
    cert_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    从业者上传证件图片，后端AI自动OCR识别和校验
    支持：id_card(身份证)、health_cert(健康证)、qualification(资格证)
    """
    payload = decode_access_token(token)
    if not payload:
        return error("令牌无效", 401)
    if payload["role"] != "worker":
        return error("仅从业者可上传资质", 403)

    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if not user:
        return error("用户不存在", 404)

    # 1. 保存上传图片
    ext = file.filename.split(".")[-1] if file.filename else "jpg"
    save_name = f"{user.id}_{cert_type}_{os.urandom(4).hex()}.{ext}"
    save_path = os.path.join(UPLOAD_DIR, save_name)
    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    # 2. AI OCR识别证件信息
    ocr_result = recognize_certificate(cert_type, content)

    # 3. AI证件真伪校验
    is_valid, verify_msg = verify_certificate_validity(ocr_result)

    if not is_valid:
        return error(f"证件校验未通过: {verify_msg}")

    # 4. 重复注册校验
    cert_number = ocr_result.get("cert_number", "")
    if cert_number and check_duplicate_cert(db, cert_type, cert_number):
        return error("该证件已被其他用户注册")

    # 5. 保存资质记录
    cert = Certification(
        user_id=user.id,
        cert_type=cert_type,
        cert_number=cert_number,
        real_name=ocr_result.get("real_name", ""),
        expire_date=ocr_result.get("expire_date", ""),
        image_url=save_path,
        ocr_result=json.dumps(ocr_result, ensure_ascii=False),
        status="passed",
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)

    # 6. 更新用户真实姓名
    if not user.real_name and ocr_result.get("real_name"):
        user.real_name = ocr_result.get("real_name")
        db.commit()

    # 7. 重新计算信用评分
    certifications = db.query(Certification).filter(
        Certification.user_id == user.id
    ).all()
    orders = []  # 新注册用户暂无订单
    reviews = []
    credit_result = calculate_credit_score(certifications, orders, reviews)
    user.credit_score = credit_result["score"]
    user.risk_level = credit_result["risk_level"]
    db.commit()

    return success({
        "cert_id": cert.id,
        "ocr_result": ocr_result,
        "status": cert.status,
        "credit_score": credit_result["score"],
        "risk_level": credit_result["risk_level"],
    }, f"证件上传成功，{verify_msg}")


@router.get("/list", summary="获取我的资质列表")
async def api_get_certifications(
    token: str,
    db: Session = Depends(get_db),
):
    """查看当前从业者的所有资质"""
    payload = decode_access_token(token)
    if not payload:
        return error("令牌无效", 401)

    certs = db.query(Certification).filter(
        Certification.user_id == payload["user_id"]
    ).all()

    return success([{
        "id": c.id,
        "cert_type": c.cert_type,
        "cert_number": c.cert_number,
        "real_name": c.real_name,
        "expire_date": c.expire_date,
        "status": c.status,
        "reject_reason": c.reject_reason,
        "created_at": str(c.created_at),
    } for c in certs])


@router.get("/expiring", summary="检查即将到期的证件")
async def api_check_expiring(
    token: str,
    db: Session = Depends(get_db),
):
    """检查30天内即将到期的证件（到期提醒）"""
    payload = decode_access_token(token)
    if not payload:
        return error("令牌无效", 401)

    from datetime import datetime, date, timedelta
    today = date.today()
    deadline = today + timedelta(days=30)
    certs = db.query(Certification).filter(
        Certification.user_id == payload["user_id"],
        Certification.status == "passed",
    ).all()

    expiring = []
    for c in certs:
        try:
            exp = datetime.strptime(c.expire_date, "%Y-%m-%d").date()
        except ValueError:
            continue
        if today <= exp <= deadline:
            expiring.append({
                "cert_id": c.id,
                "cert_type": c.cert_type,
                "expire_date": c.expire_date,
                "days_left": (exp - today).days,
            })

    return success(expiring, f"有{len(expiring)}个证件即将到期" if expiring else "所有证件在有效期内")
