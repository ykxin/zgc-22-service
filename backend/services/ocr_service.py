"""AI OCR证件识别服务入口。

AI只输出结构化字段、候选标签和风险提示，不直接决定最终审核结论。
"""
import re
from datetime import datetime, date
from typing import Optional, Tuple

from services.ocr_providers import get_ocr_provider
from services.ocr_providers.mock import normalize_doc_type


SUPPORTED_DOC_TYPES = {
    "id_card",
    "health_cert",
    "health_certificate",
    "qualification",
    "no_criminal_record",
    "background_check_authorization",
    "housekeeping_certificate",
    "maternity_matron_certificate",
    "infant_care_certificate",
    "elderly_care_certificate",
    "medical_caregiver_certificate",
    "first_aid_certificate",
    "insurance_policy",
}


def recognize_certificate(cert_type: str, image_data: bytes, provider=None, declared_doc_name: Optional[str] = None) -> dict:
    """统一证件识别入口，兼容旧cert_type并返回新结构。"""
    if cert_type not in SUPPORTED_DOC_TYPES:
        return {"error": "不支持的证件类型"}
    ocr_provider = get_ocr_provider()
    return ocr_provider.extract(cert_type, image_data, provider=provider, declared_doc_name=declared_doc_name)


def flatten_ocr_result(ocr_result: dict) -> dict:
    """把新OCR结构转换为旧接口字段，便于旧代码/前端兼容。"""
    fields = ocr_result.get("extracted_fields", {})
    return {
        "cert_type": fields.get("doc_type") or normalize_doc_type(fields.get("cert_type", "")),
        "real_name": fields.get("holder_name", ""),
        "cert_number": fields.get("certificate_no", ""),
        "expire_date": fields.get("expire_date"),
        "issuing_authority": fields.get("issuing_authority", ""),
        "doc_name": fields.get("certificate_name", ""),
        "issue_date": fields.get("issue_date"),
        "confidence": ocr_result.get("confidence", 0),
    }


def verify_certificate_validity(ocr_result: dict) -> Tuple[bool, str]:
    """
    规则引擎层面的基础校验。

    返回False只代表材料不满足最低入库要求；高风险但可人工复核的情况保留为risk_flags。
    """
    if ocr_result.get("error"):
        return False, ocr_result["error"]

    flat = flatten_ocr_result(ocr_result)
    confidence = flat.get("confidence", 0)
    if confidence < 0.70:
        return False, "证件识别置信度过低，请重新上传清晰图片"

    expire_date = flat.get("expire_date")
    if expire_date:
        try:
            datetime.strptime(expire_date, "%Y-%m-%d").date()
        except ValueError:
            return False, "证件日期格式异常"

    cert_type = flat.get("cert_type", "")
    cert_number = flat.get("cert_number", "")
    if cert_type == "id_card" and not re.match(r"^\d{17}[\dXx]$", cert_number):
        return False, "身份证号格式不正确"

    return True, "AI识别完成，等待人工审核"


def is_expired(expire_date: Optional[str]) -> bool:
    if not expire_date:
        return False
    try:
        return datetime.strptime(expire_date, "%Y-%m-%d").date() < date.today()
    except ValueError:
        return False
