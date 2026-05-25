"""Qualification trust-tag domain service."""
from __future__ import annotations

import json
from datetime import datetime, date, timedelta
from typing import Any

from sqlalchemy.orm import Session

from database.models import (
    AiQualificationExtraction,
    Certification,
    Order,
    ProviderQualificationTag,
    QualificationTagDefinition,
    Review,
    User,
)
from services.credit_service import calculate_credit_score, check_duplicate_cert
from services.ocr_providers.mock import normalize_doc_type
from services.ocr_service import flatten_ocr_result, is_expired, recognize_certificate, verify_certificate_validity


HIGH_SENSITIVE_SERVICE_TYPES = {
    "maternity_care",
    "infant_care",
    "elderly_care",
    "live_in_housekeeping",
    "patient_care",
    "住家保姆",
    "母婴护理",
    "婴幼儿照护",
    "老人照护",
    "失能老人照护",
    "半失能老人照护",
    "病患陪护",
    "夜间陪护",
    "独居老人上门服务",
}


DOC_TYPE_LABELS = {
    "id_card": "身份证",
    "health_cert": "健康证",
    "health_certificate": "健康证明",
    "qualification": "资格证",
    "no_criminal_record": "无犯罪记录证明",
    "background_check_authorization": "背景核查授权",
    "housekeeping_certificate": "家政服务证书",
    "maternity_matron_certificate": "母婴护理证书",
    "infant_care_certificate": "育婴照护证书",
    "elderly_care_certificate": "养老护理证书",
    "medical_caregiver_certificate": "病患陪护证书",
    "first_aid_certificate": "基础急救证书",
    "insurance_policy": "服务保险",
}


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def json_loads(value: str | None, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def mask_cert_number(cert_number: str | None) -> str:
    if not cert_number:
        return ""
    if len(cert_number) <= 8:
        return cert_number[:2] + "****"
    return f"{cert_number[:4]}****{cert_number[-4:]}"


def submit_document(
    db: Session,
    provider: User,
    cert_type: str,
    image_url: str,
    image_data: bytes,
    declared_doc_name: str | None = None,
) -> tuple[Certification | None, dict | None, str | None]:
    """Upload a qualification document, run AI extraction, and keep it pending."""
    ocr_result = recognize_certificate(cert_type, image_data, provider=provider, declared_doc_name=declared_doc_name)
    is_valid, verify_msg = verify_certificate_validity(ocr_result)
    if not is_valid:
        return None, None, f"证件校验未通过: {verify_msg}"

    ocr_result = enrich_risk_flags(ocr_result)
    flat = flatten_ocr_result(ocr_result)
    cert_number = flat.get("cert_number", "")
    if cert_number and check_duplicate_cert(db, cert_type, cert_number):
        return None, None, "该证件已被其他用户注册"

    cert = Certification(
        user_id=provider.id,
        cert_type=cert_type,
        cert_number=cert_number,
        real_name=flat.get("real_name", ""),
        expire_date=flat.get("expire_date") or "",
        image_url=image_url,
        ocr_result=json_dumps(ocr_result),
        status="pending",
        doc_name=flat.get("doc_name") or declared_doc_name or DOC_TYPE_LABELS.get(cert_type, cert_type),
        issuing_authority=flat.get("issuing_authority", ""),
        issue_date=flat.get("issue_date") or "",
        verification_source="ai_model",
        ai_confidence=flat.get("confidence"),
        extracted_fields=json_dumps(ocr_result.get("extracted_fields", {})),
        suggested_tags=json_dumps(ocr_result.get("suggested_tags", [])),
        risk_flags=json_dumps(ocr_result.get("risk_flags", [])),
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)

    extraction = save_ai_extraction(db, cert, ocr_result)
    apply_pending_ai_tags(db, cert, ocr_result)
    db.commit()

    return cert, {
        "verify_msg": verify_msg,
        "extraction_id": extraction.id,
        "ocr_result": ocr_result,
    }, None


def rerun_ai_extraction(db: Session, cert: Certification) -> dict:
    with open(cert.image_url, "rb") as f:
        image_data = f.read()
    provider = db.query(User).filter(User.id == cert.user_id).first()
    ocr_result = recognize_certificate(cert.cert_type, image_data, provider=provider, declared_doc_name=cert.doc_name)
    ocr_result = enrich_risk_flags(ocr_result)
    flat = flatten_ocr_result(ocr_result)

    cert.cert_number = flat.get("cert_number", cert.cert_number)
    cert.real_name = flat.get("real_name", cert.real_name)
    cert.expire_date = flat.get("expire_date") or cert.expire_date
    cert.ocr_result = json_dumps(ocr_result)
    cert.issuing_authority = flat.get("issuing_authority", cert.issuing_authority)
    cert.issue_date = flat.get("issue_date") or cert.issue_date
    cert.ai_confidence = flat.get("confidence")
    cert.extracted_fields = json_dumps(ocr_result.get("extracted_fields", {}))
    cert.suggested_tags = json_dumps(ocr_result.get("suggested_tags", []))
    cert.risk_flags = json_dumps(ocr_result.get("risk_flags", []))
    cert.verification_source = "ai_model"
    cert.status = "pending"
    save_ai_extraction(db, cert, ocr_result)
    apply_pending_ai_tags(db, cert, ocr_result)
    db.commit()
    return ocr_result


def save_ai_extraction(db: Session, cert: Certification, ocr_result: dict) -> AiQualificationExtraction:
    extraction = AiQualificationExtraction(
        document_id=cert.id,
        provider_id=cert.user_id,
        model_name=ocr_result.get("model_name", "mock-qualification-ocr-v1"),
        extracted_json=json_dumps(ocr_result.get("extracted_fields", {})),
        suggested_tags=json_dumps(ocr_result.get("suggested_tags", [])),
        risk_flags=json_dumps(ocr_result.get("risk_flags", [])),
        confidence=ocr_result.get("confidence"),
        status="pending_review",
    )
    db.add(extraction)
    db.flush()
    return extraction


def enrich_risk_flags(ocr_result: dict) -> dict:
    flags = list(ocr_result.get("risk_flags", []))
    fields = ocr_result.get("extracted_fields", {})
    expire_date = fields.get("expire_date")
    if is_expired(expire_date):
        flags.append({
            "code": "DOCUMENT_EXPIRED",
            "message": "证书已超过有效期",
            "severity": "high",
        })
    ocr_result["risk_flags"] = flags
    return ocr_result


def apply_pending_ai_tags(db: Session, cert: Certification, ocr_result: dict):
    for tag in ocr_result.get("suggested_tags", []):
        upsert_provider_tag(
            db,
            provider_id=cert.user_id,
            tag_code=tag["tag_code"],
            status="pending",
            trust_level=3,
            source_type="document",
            source_id=cert.id,
            confidence=tag.get("confidence"),
            valid_until=cert.expire_date,
            generated_by="ai_model",
            visible_to_customer=True,
        )
    for flag in ocr_result.get("risk_flags", []):
        if flag.get("code") == "NAME_MISMATCH":
            upsert_provider_tag(
                db,
                provider_id=cert.user_id,
                tag_code="name_mismatch_risk",
                status="warning",
                trust_level=3,
                source_type="document",
                source_id=cert.id,
                confidence=cert.ai_confidence,
                generated_by="ai_model",
                visible_to_customer=False,
            )
        elif flag.get("code") == "DOCUMENT_EXPIRED":
            upsert_provider_tag(
                db,
                provider_id=cert.user_id,
                tag_code="health_certificate_expired" if normalize_doc_type(cert.cert_type) == "health_certificate" else "suspected_forgery_risk",
                status="expired",
                trust_level=3,
                source_type="document",
                source_id=cert.id,
                confidence=cert.ai_confidence,
                generated_by="system_rule",
                visible_to_customer=normalize_doc_type(cert.cert_type) == "health_certificate",
            )


def review_document(
    db: Session,
    cert: Certification,
    status: str,
    reviewer_id: int | None,
    review_comment: str | None = None,
    verified_fields: dict | None = None,
) -> dict:
    normalized_status = "passed" if status == "verified" else status
    if normalized_status not in {"passed", "rejected", "expired", "pending"}:
        raise ValueError("审核状态仅支持 passed/verified/rejected/expired/pending")

    cert.status = normalized_status
    cert.reviewer_id = reviewer_id
    cert.review_comment = review_comment
    cert.reject_reason = review_comment if normalized_status == "rejected" else None
    cert.verification_source = "human_reviewer"

    if verified_fields:
        fields = json_loads(cert.extracted_fields, {})
        fields.update(verified_fields)
        cert.extracted_fields = json_dumps(fields)

    generated_tags = []
    if normalized_status == "passed":
        generated_tags = activate_verified_tags(db, cert)
        sync_user_from_verified_document(db, cert)
    elif normalized_status == "rejected":
        mark_source_tags(db, cert, status="rejected", visible_to_customer=False)
    elif normalized_status == "expired":
        mark_source_tags(db, cert, status="expired", visible_to_customer=True)
        apply_expiry_tags(db, cert)

    recalculate_worker_credit(db, cert.user_id)
    db.commit()
    return generated_tags


def activate_verified_tags(db: Session, cert: Certification) -> list:
    generated_tags = []
    suggested_tags = json_loads(cert.suggested_tags, [])
    for tag in suggested_tags:
        provider_tag = upsert_provider_tag(
            db,
            provider_id=cert.user_id,
            tag_code=tag["tag_code"],
            status="active",
            trust_level=4,
            source_type="document",
            source_id=cert.id,
            confidence=tag.get("confidence"),
            valid_from=date.today().isoformat(),
            valid_until=cert.expire_date,
            generated_by="human_reviewer",
            visible_to_customer=True,
        )
        generated_tags.append(serialize_tag(db, provider_tag))

    apply_expiry_tags(db, cert)
    return generated_tags


def apply_expiry_tags(db: Session, cert: Certification):
    normalized_type = normalize_doc_type(cert.cert_type)
    if normalized_type != "health_certificate" or not cert.expire_date:
        return
    try:
        exp = datetime.strptime(cert.expire_date, "%Y-%m-%d").date()
    except ValueError:
        return

    today = date.today()
    if exp < today:
        cert.status = "expired"
        upsert_provider_tag(
            db,
            provider_id=cert.user_id,
            tag_code="health_certificate_expired",
            status="expired",
            trust_level=4,
            source_type="document",
            source_id=cert.id,
            confidence=cert.ai_confidence,
            valid_until=cert.expire_date,
            generated_by="system_rule",
            visible_to_customer=True,
        )
    elif exp <= today + timedelta(days=30):
        upsert_provider_tag(
            db,
            provider_id=cert.user_id,
            tag_code="health_certificate_expiring",
            status="warning",
            trust_level=4,
            source_type="document",
            source_id=cert.id,
            confidence=cert.ai_confidence,
            valid_until=cert.expire_date,
            generated_by="system_rule",
            visible_to_customer=True,
        )


def sync_user_from_verified_document(db: Session, cert: Certification):
    user = db.query(User).filter(User.id == cert.user_id).first()
    if not user:
        return
    if cert.cert_type == "id_card":
        if cert.real_name and not user.real_name:
            user.real_name = cert.real_name
        if cert.cert_number and not user.id_card:
            user.id_card = cert.cert_number
    if cert.real_name and not user.real_name:
        user.real_name = cert.real_name


def recalculate_worker_credit(db: Session, user_id: int):
    worker = db.query(User).filter(User.id == user_id).first()
    if not worker:
        return
    certifications = db.query(Certification).filter(Certification.user_id == user_id).all()
    orders = db.query(Order).filter(Order.worker_id == user_id).all()
    reviews = db.query(Review).filter(Review.target_id == user_id).all()
    credit_result = calculate_credit_score(certifications, orders, reviews)
    worker.credit_score = credit_result["score"]
    worker.risk_level = credit_result["risk_level"]


def mark_source_tags(db: Session, cert: Certification, status: str, visible_to_customer: bool):
    tags = db.query(ProviderQualificationTag).filter(
        ProviderQualificationTag.provider_id == cert.user_id,
        ProviderQualificationTag.source_type == "document",
        ProviderQualificationTag.source_id == cert.id,
    ).all()
    for tag in tags:
        tag.status = status
        tag.visible_to_customer = 1 if visible_to_customer else 0
        tag.generated_by = "human_reviewer"


def upsert_provider_tag(
    db: Session,
    provider_id: int,
    tag_code: str,
    status: str,
    trust_level: int,
    source_type: str | None = None,
    source_id: int | None = None,
    confidence: float | None = None,
    valid_from: str | None = None,
    valid_until: str | None = None,
    generated_by: str = "system_rule",
    visible_to_customer: bool = True,
) -> ProviderQualificationTag:
    query = db.query(ProviderQualificationTag).filter(
        ProviderQualificationTag.provider_id == provider_id,
        ProviderQualificationTag.tag_code == tag_code,
        ProviderQualificationTag.source_type == source_type,
        ProviderQualificationTag.source_id == source_id,
    )
    tag = query.first()
    if not tag:
        tag = ProviderQualificationTag(
            provider_id=provider_id,
            tag_code=tag_code,
            source_type=source_type,
            source_id=source_id,
        )
        db.add(tag)
    tag.status = status
    tag.trust_level = trust_level
    tag.confidence = confidence
    tag.valid_from = valid_from or tag.valid_from
    tag.valid_until = valid_until
    tag.generated_by = generated_by
    tag.visible_to_customer = 1 if visible_to_customer else 0
    return tag


def refresh_expiry_tags(db: Session, provider_id: int):
    certs = db.query(Certification).filter(
        Certification.user_id == provider_id,
        Certification.status.in_(["passed", "expired"]),
    ).all()
    for cert in certs:
        apply_expiry_tags(db, cert)
    db.commit()


def get_provider_profile(db: Session, provider_id: int) -> dict | None:
    provider = db.query(User).filter(User.id == provider_id, User.role == "worker").first()
    if not provider:
        return None
    refresh_expiry_tags(db, provider_id)

    certs = db.query(Certification).filter(Certification.user_id == provider_id).all()
    visible_tags = db.query(ProviderQualificationTag).filter(
        ProviderQualificationTag.provider_id == provider_id,
        ProviderQualificationTag.visible_to_customer == 1,
    ).all()
    active_tag_codes = {tag.tag_code for tag in visible_tags if tag.status == "active"}
    risk_warnings = collect_risk_warnings(db, certs, visible_tags)

    return {
        "provider_id": provider.id,
        "qualification_summary": {
            "identity_verified": "identity_verified" in active_tag_codes,
            "health_verified": "health_verified" in active_tag_codes,
            "background_check_status": "authorized" if "background_check_authorized" in active_tag_codes else "not_authorized",
            "qualification_completeness": qualification_completeness(active_tag_codes),
        },
        "visible_tags": [
            serialize_tag(db, tag)
            for tag in sorted(visible_tags, key=lambda item: tag_priority(db, item.tag_code))
            if tag.status in {"active", "warning", "expired"}
        ],
        "documents": [serialize_document(cert, include_sensitive=False) for cert in certs],
        "risk_warnings": risk_warnings,
        "growth_suggestions": growth_suggestions(active_tag_codes),
    }


def serialize_document(cert: Certification, include_sensitive: bool = False) -> dict:
    data = {
        "id": cert.id,
        "cert_type": cert.cert_type,
        "doc_type": normalize_doc_type(cert.cert_type),
        "doc_name": cert.doc_name or DOC_TYPE_LABELS.get(cert.cert_type, cert.cert_type),
        "cert_number": cert.cert_number if include_sensitive else mask_cert_number(cert.cert_number),
        "real_name": cert.real_name,
        "expire_date": cert.expire_date,
        "issuing_authority": cert.issuing_authority,
        "ai_confidence": cert.ai_confidence,
        "status": cert.status,
        "reject_reason": cert.reject_reason,
        "review_comment": cert.review_comment,
        "suggested_tags": json_loads(cert.suggested_tags, []),
        "risk_flags": json_loads(cert.risk_flags, []),
        "created_at": str(cert.created_at),
    }
    if include_sensitive:
        data["image_url"] = cert.image_url
        data["extracted_fields"] = json_loads(cert.extracted_fields, {})
    return data


def serialize_tag(db: Session, tag: ProviderQualificationTag) -> dict:
    definition = db.query(QualificationTagDefinition).filter(
        QualificationTagDefinition.tag_code == tag.tag_code
    ).first()
    return {
        "tag_code": tag.tag_code,
        "tag_name": definition.tag_name if definition else tag.tag_code,
        "tag_category": definition.tag_category if definition else None,
        "status": tag.status,
        "trust_level": tag.trust_level,
        "source_type": tag.source_type,
        "source_id": tag.source_id,
        "confidence": tag.confidence,
        "valid_until": tag.valid_until,
        "generated_by": tag.generated_by,
    }


def tag_priority(db: Session, tag_code: str) -> int:
    definition = db.query(QualificationTagDefinition).filter(
        QualificationTagDefinition.tag_code == tag_code
    ).first()
    return definition.display_priority if definition else 999


def collect_risk_warnings(db: Session, certs: list[Certification], tags: list[ProviderQualificationTag]) -> list[dict]:
    warnings = []
    for cert in certs:
        for flag in json_loads(cert.risk_flags, []):
            if flag.get("severity") in {"medium", "high"}:
                warnings.append({
                    "code": flag.get("code"),
                    "message": flag.get("message"),
                    "document_id": cert.id,
                })
    for tag in tags:
        if tag.status in {"warning", "expired"}:
            definition = db.query(QualificationTagDefinition).filter(
                QualificationTagDefinition.tag_code == tag.tag_code
            ).first()
            warnings.append({
                "code": tag.tag_code.upper(),
                "message": definition.tag_name if definition else tag.tag_code,
                "document_id": tag.source_id,
            })
    deduped = []
    seen = set()
    for warning in warnings:
        key = (warning.get("code"), warning.get("document_id"))
        if key not in seen:
            deduped.append(warning)
            seen.add(key)
    return deduped


def qualification_completeness(active_tag_codes: set[str]) -> str:
    score = 0
    if "identity_verified" in active_tag_codes:
        score += 1
    if "health_verified" in active_tag_codes:
        score += 1
    if active_tag_codes & {"housekeeping", "maternity_care", "infant_care", "elderly_care", "patient_care"}:
        score += 1
    if "background_check_authorized" in active_tag_codes:
        score += 1
    if score >= 3:
        return "high"
    if score == 2:
        return "medium"
    return "low"


def growth_suggestions(active_tag_codes: set[str]) -> list[dict]:
    suggestions = []
    if "identity_verified" not in active_tag_codes:
        suggestions.append({"title": "完成身份核验", "reason": "身份核验是进入服务匹配池的基础条件"})
    if "health_verified" not in active_tag_codes:
        suggestions.append({"title": "上传健康证明", "reason": "可提升母婴、老人照护、住家等服务机会"})
    if "background_check_authorized" not in active_tag_codes:
        suggestions.append({"title": "上传无犯罪记录证明或授权背景核查", "reason": "可提升住家服务和老人照护服务的匹配机会"})
    if not (active_tag_codes & {"elderly_care", "maternity_care", "infant_care", "patient_care"}):
        suggestions.append({"title": "补充专项技能证书", "reason": "可获得更明确的技能标签和推荐理由"})
    return suggestions[:3]


def check_eligibility(db: Session, provider_id: int, service_type: str, required_tags: list[str] | None = None) -> dict:
    profile = get_provider_profile(db, provider_id)
    if not profile:
        return {"eligible": False, "reasons": ["服务人员不存在"], "missing_tags": required_tags or [], "risk_warnings": []}

    active_tags = {
        tag["tag_code"]
        for tag in profile["visible_tags"]
        if tag["status"] == "active"
    }
    missing_tags = [tag for tag in (required_tags or []) if tag not in active_tags]
    reasons = []

    if service_type in HIGH_SENSITIVE_SERVICE_TYPES:
        for tag_code in ["identity_verified", "health_verified"]:
            if tag_code not in active_tags and tag_code not in missing_tags:
                missing_tags.append(tag_code)
        expired_health = any(tag["tag_code"] == "health_certificate_expired" for tag in profile["visible_tags"])
        if expired_health:
            reasons.append("健康证明已过期，高敏服务暂不可接单")

    if missing_tags:
        reasons.append("缺少必要资质标签：" + "、".join(missing_tags))

    return {
        "eligible": not reasons,
        "reasons": reasons,
        "missing_tags": missing_tags,
        "risk_warnings": profile["risk_warnings"],
        "qualification_summary": profile["qualification_summary"],
    }


def get_provider_matching_facts(db: Session, provider_id: int, service_type: str | None = None) -> dict | None:
    """Return DB-backed qualification facts for same-process matching code.

    Matching/recommendation should call this function or query the underlying
    tables with the same Session. The HTTP APIs are for external clients,
    Swagger, and debugging, not for the monolith to call itself.
    """
    profile = get_provider_profile(db, provider_id)
    if not profile:
        return None

    active_tags = [
        tag["tag_code"]
        for tag in profile["visible_tags"]
        if tag["status"] == "active"
    ]
    warning_tags = [
        tag["tag_code"]
        for tag in profile["visible_tags"]
        if tag["status"] in {"warning", "expired"}
    ]
    eligibility = None
    if service_type:
        eligibility = check_eligibility(
            db,
            provider_id=provider_id,
            service_type=service_type,
            required_tags=[],
        )

    return {
        "provider_id": provider_id,
        "active_tags": active_tags,
        "warning_tags": warning_tags,
        "qualification_summary": profile["qualification_summary"],
        "risk_warnings": profile["risk_warnings"],
        "eligibility": eligibility,
    }
