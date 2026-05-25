"""Deterministic local OCR provider for qualification documents."""
from __future__ import annotations

import hashlib
from typing import Optional
from datetime import date


DOC_TYPE_ALIASES = {
    "health_cert": "health_certificate",
    "qualification": "housekeeping_certificate",
}


TAG_BY_DOC_TYPE = {
    "id_card": [("identity_verified", "身份已核验")],
    "health_certificate": [("health_verified", "健康证明已核验")],
    "no_criminal_record": [("background_check_authorized", "背景核查已授权")],
    "background_check_authorization": [("background_check_authorized", "背景核查已授权")],
    "insurance_policy": [("insurance_policy_verified", "已配置服务保险")],
    "housekeeping_certificate": [("housekeeping", "家务服务")],
    "maternity_matron_certificate": [("maternity_care", "母婴护理")],
    "infant_care_certificate": [("infant_care", "育婴照护")],
    "elderly_care_certificate": [
        ("elderly_care", "老人照护"),
        ("elderly_care_intermediate", "养老护理员-中级"),
    ],
    "medical_caregiver_certificate": [("patient_care", "病患陪护")],
    "first_aid_certificate": [("first_aid_trained", "具备基础急救培训")],
}


DOC_LABELS = {
    "id_card": "居民身份证",
    "health_certificate": "健康证明",
    "no_criminal_record": "无犯罪记录证明",
    "background_check_authorization": "背景核查授权书",
    "housekeeping_certificate": "家政服务员职业技能证书",
    "maternity_matron_certificate": "母婴护理职业技能证书",
    "infant_care_certificate": "育婴员职业技能等级证书",
    "elderly_care_certificate": "养老护理员职业技能等级证书",
    "medical_caregiver_certificate": "病患陪护技能证书",
    "first_aid_certificate": "基础急救培训证书",
    "insurance_policy": "服务保险保单",
}


AUTHORITIES = {
    "id_card": "公安机关",
    "health_certificate": "市卫生健康委员会",
    "no_criminal_record": "公安机关",
    "background_check_authorization": "平台背景核查中心",
    "insurance_policy": "合作保险机构",
    "default": "市人力资源和社会保障局",
}


class MockQualificationOcrProvider:
    """A predictable OCR provider used for demos and tests."""

    model_name = "mock-qualification-ocr-v1"

    def extract(self, doc_type: str, image_data: bytes, provider=None, declared_doc_name: Optional[str] = None) -> dict:
        normalized_type = normalize_doc_type(doc_type)
        seed = hashlib.sha256(normalized_type.encode("utf-8") + image_data).hexdigest()
        confidence = 0.84 + (int(seed[:2], 16) % 14) / 100
        holder_name = self._holder_name(seed, provider)
        certificate_no = self._certificate_no(normalized_type, seed)
        expire_date = self._expire_date(normalized_type, seed)
        issue_date = self._issue_date(seed)
        level = "四级/中级工" if normalized_type == "elderly_care_certificate" else None

        extracted_fields = {
            "doc_type": normalized_type,
            "certificate_name": declared_doc_name or DOC_LABELS.get(normalized_type, "资质材料"),
            "holder_name": holder_name,
            "level": level,
            "certificate_no": certificate_no,
            "issuing_authority": AUTHORITIES.get(normalized_type, AUTHORITIES["default"]),
            "issue_date": issue_date,
            "expire_date": expire_date,
        }

        suggested_tags = [
            {
                "tag_code": tag_code,
                "tag_name": tag_name,
                "confidence": round(max(0.7, confidence - index * 0.04), 4),
            }
            for index, (tag_code, tag_name) in enumerate(TAG_BY_DOC_TYPE.get(normalized_type, []))
        ]
        risk_flags = self._risk_flags(extracted_fields, confidence, provider)

        return {
            "model_name": self.model_name,
            "confidence": round(confidence, 4),
            "extracted_fields": extracted_fields,
            "suggested_tags": suggested_tags,
            "risk_flags": risk_flags,
        }

    def _holder_name(self, seed: str, provider) -> str:
        if provider and provider.real_name:
            if int(seed[2:4], 16) % 5 == 0:
                return "待复核姓名"
            return provider.real_name
        names = ["张明", "李华", "王芳", "刘洋", "陈静", "赵伟"]
        return names[int(seed[4:6], 16) % len(names)]

    def _certificate_no(self, doc_type: str, seed: str) -> str:
        if doc_type == "id_card":
            body = str(11010000000000000 + int(seed[6:16], 16) % 89999999999999999)
            return body[:17] + str(int(seed[16], 16) % 10)
        prefix_map = {
            "health_certificate": "JK",
            "no_criminal_record": "WFZ",
            "background_check_authorization": "BG",
            "insurance_policy": "BX",
            "first_aid_certificate": "JJ",
            "default": "ZG",
        }
        prefix = prefix_map.get(doc_type, prefix_map["default"])
        return f"{prefix}{date.today().year}{int(seed[8:16], 16) % 1000000:06d}"

    def _issue_date(self, seed: str) -> str:
        year = date.today().year - 1 - int(seed[10:12], 16) % 3
        month = int(seed[12:14], 16) % 12 + 1
        day = int(seed[14:16], 16) % 28 + 1
        return f"{year}-{month:02d}-{day:02d}"

    def _expire_date(self, doc_type: str, seed: str) -> Optional[str]:
        if doc_type in {"background_check_authorization", "no_criminal_record"}:
            return None
        offset = int(seed[16:18], 16) % 5
        if doc_type == "health_certificate":
            year = date.today().year + (0 if offset == 0 else 1)
        else:
            year = date.today().year + 1 + offset
        month = int(seed[18:20], 16) % 12 + 1
        day = int(seed[20:22], 16) % 28 + 1
        return f"{year}-{month:02d}-{day:02d}"

    def _risk_flags(self, extracted_fields: dict, confidence: float, provider) -> list:
        flags = []
        if confidence < 0.86:
            flags.append({
                "code": "LOW_CONFIDENCE",
                "message": "AI识别置信度较低，建议人工重点复核",
                "severity": "medium",
            })
        if provider and provider.real_name and extracted_fields.get("holder_name") != provider.real_name:
            flags.append({
                "code": "NAME_MISMATCH",
                "message": "证书姓名与实名认证姓名不一致",
                "severity": "high",
            })
        return flags


def normalize_doc_type(doc_type: str) -> str:
    return DOC_TYPE_ALIASES.get(doc_type, doc_type)
