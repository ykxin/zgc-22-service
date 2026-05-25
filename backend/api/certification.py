"""AI资质可信标签模块API"""
import os
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import Certification, User
from schemas.certification import (
    EligibilityCheck,
    QualificationDocumentReview,
    QualificationDocumentUpload,
)
from services.certification_service import (
    check_eligibility,
    get_provider_profile,
    rerun_ai_extraction,
    review_document,
    serialize_document,
    submit_document,
)
from utils.response import success, error
from utils.security import decode_access_token

router = APIRouter(prefix="/api/cert", tags=["AI资质核验"])
qualification_router = APIRouter(tags=["资质可信标签"])

UPLOAD_DIR = "uploads/certifications"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_payload(token: str | None):
    return decode_access_token(token) if token else None


def can_manage_provider(payload: dict | None, provider_id: int) -> bool:
    return bool(payload and (payload.get("role") == "admin" or payload.get("user_id") == provider_id))


def save_upload_file(user_id: int, cert_type: str, file: UploadFile, content: bytes) -> str:
    ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
    save_name = f"{user_id}_{cert_type}_{os.urandom(4).hex()}.{ext}"
    save_path = os.path.join(UPLOAD_DIR, save_name)
    with open(save_path, "wb") as f:
        f.write(content)
    return save_path


@router.post("/upload", summary="上传证件并AI识别")
async def api_upload_cert(
    token: str = Form(...),
    cert_type: str = Form(...),
    file: UploadFile = File(...),
    declared_doc_name: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """
    从业者上传证件图片，AI输出结构化信息和候选标签。
    最终审核结论必须由管理员人工审核产生。
    """
    payload = get_payload(token)
    if not payload:
        return error("令牌无效", 401)
    if payload["role"] != "worker":
        return error("仅从业者可上传资质", 403)

    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if not user:
        return error("用户不存在", 404)

    content = await file.read()
    save_path = save_upload_file(user.id, cert_type, file, content)
    cert, result, err_msg = submit_document(
        db,
        provider=user,
        cert_type=cert_type,
        image_url=save_path,
        image_data=content,
        declared_doc_name=declared_doc_name,
    )
    if err_msg:
        try:
            os.remove(save_path)
        except OSError:
            pass
        return error(err_msg)

    ocr_result = result["ocr_result"]
    return success({
        "cert_id": cert.id,
        "document_id": cert.id,
        "status": cert.status,
        "next_step": "manual_review",
        "ocr_result": ocr_result,
        "suggested_tags": ocr_result.get("suggested_tags", []),
        "risk_flags": ocr_result.get("risk_flags", []),
        "ai_confidence": ocr_result.get("confidence"),
    }, "AI已识别资质材料，等待人工审核")


@router.get("/list", summary="获取我的资质列表")
async def api_get_certifications(token: str, db: Session = Depends(get_db)):
    payload = get_payload(token)
    if not payload:
        return error("令牌无效", 401)

    certs = db.query(Certification).filter(
        Certification.user_id == payload["user_id"]
    ).order_by(Certification.created_at.desc()).all()

    return success([serialize_document(c, include_sensitive=False) for c in certs])


@router.get("/expiring", summary="检查即将到期的证件")
async def api_check_expiring(token: str, db: Session = Depends(get_db)):
    payload = get_payload(token)
    if not payload:
        return error("令牌无效", 401)

    from datetime import datetime, date, timedelta
    today = date.today()
    deadline = today + timedelta(days=30)
    certs = db.query(Certification).filter(
        Certification.user_id == payload["user_id"],
        Certification.status.in_(["passed", "expired"]),
    ).all()

    expiring = []
    for c in certs:
        try:
            exp = datetime.strptime(c.expire_date, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            continue
        if today <= exp <= deadline:
            expiring.append({
                "cert_id": c.id,
                "cert_type": c.cert_type,
                "doc_name": c.doc_name,
                "expire_date": c.expire_date,
                "days_left": (exp - today).days,
            })

    return success(expiring, f"有{len(expiring)}个证件即将到期" if expiring else "所有证件在有效期内")


@qualification_router.post("/api/providers/{provider_id}/qualifications/documents", summary="上传资质材料")
async def api_upload_provider_document(
    provider_id: int,
    body: QualificationDocumentUpload,
    token: str,
    db: Session = Depends(get_db),
):
    payload = get_payload(token)
    if not can_manage_provider(payload, provider_id):
        return error("无权上传该服务人员资质", 403)

    provider = db.query(User).filter(User.id == provider_id, User.role == "worker").first()
    if not provider:
        return error("服务人员不存在", 404)

    image_data = body.file_url.encode("utf-8")
    if os.path.exists(body.file_url):
        with open(body.file_url, "rb") as f:
            image_data = f.read()

    cert, result, err_msg = submit_document(
        db,
        provider=provider,
        cert_type=body.doc_type,
        image_url=body.file_url,
        image_data=image_data,
        declared_doc_name=body.declared_doc_name,
    )
    if err_msg:
        return error(err_msg)

    return success({
        "document_id": cert.id,
        "status": "uploaded",
        "verification_status": cert.status,
        "next_step": "ai_extraction",
        "ai_extraction": result["ocr_result"],
    })


@qualification_router.post("/api/qualifications/documents/{document_id}/ai-extract", summary="AI解析资质材料")
async def api_ai_extract_document(document_id: int, token: str, db: Session = Depends(get_db)):
    payload = get_payload(token)
    if not payload:
        return error("令牌无效", 401)

    cert = db.query(Certification).filter(Certification.id == document_id).first()
    if not cert:
        return error("资质材料不存在", 404)
    if not can_manage_provider(payload, cert.user_id):
        return error("无权解析该资质材料", 403)

    ocr_result = rerun_ai_extraction(db, cert)
    return success({
        "document_id": cert.id,
        "confidence": ocr_result.get("confidence"),
        "extracted_fields": ocr_result.get("extracted_fields", {}),
        "suggested_tags": ocr_result.get("suggested_tags", []),
        "risk_flags": ocr_result.get("risk_flags", []),
    })


@qualification_router.post("/api/admin/qualifications/documents/{document_id}/review", summary="人工审核资质")
async def api_admin_review_qualification_document(
    document_id: int,
    body: QualificationDocumentReview,
    token: str,
    db: Session = Depends(get_db),
):
    payload = get_payload(token)
    if not payload or payload.get("role") != "admin":
        return error("无管理员权限", 403)

    cert = db.query(Certification).filter(Certification.id == document_id).first()
    if not cert:
        return error("资质材料不存在", 404)

    try:
        generated_tags = review_document(
            db,
            cert,
            status=body.verification_status,
            reviewer_id=payload["user_id"],
            review_comment=body.review_comment,
            verified_fields=body.verified_fields,
        )
    except ValueError as exc:
        return error(str(exc))

    return success({
        "document_id": cert.id,
        "verification_status": "verified" if cert.status == "passed" else cert.status,
        "generated_tags": generated_tags,
    })


@qualification_router.get("/api/providers/{provider_id}/qualification-profile", summary="查询服务人员资质画像")
async def api_provider_qualification_profile(provider_id: int, db: Session = Depends(get_db)):
    profile = get_provider_profile(db, provider_id)
    if not profile:
        return error("服务人员不存在", 404)
    return success(profile)


@qualification_router.post("/api/qualifications/eligibility-check", summary="资质准入检查")
async def api_eligibility_check(body: EligibilityCheck, db: Session = Depends(get_db)):
    return success(check_eligibility(
        db,
        provider_id=body.provider_id,
        service_type=body.service_type,
        required_tags=body.required_tags or [],
    ))
