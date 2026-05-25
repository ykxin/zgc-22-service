"""资质相关Pydantic模型"""
from pydantic import BaseModel, Field
from typing import Any, Optional

class CertUpload(BaseModel):
    cert_type: str = Field(..., description="证件类型 id_card/health_cert/qualification")

class CertReview(BaseModel):
    status: str = Field(..., description="passed/verified/rejected/expired/pending")
    reject_reason: Optional[str] = None
    review_comment: Optional[str] = None
    verified_fields: Optional[dict[str, Any]] = None


class QualificationDocumentUpload(BaseModel):
    doc_type: str
    file_url: str
    declared_doc_name: Optional[str] = None


class QualificationDocumentReview(BaseModel):
    verification_status: str = Field(..., description="verified/passed/rejected/expired")
    review_comment: Optional[str] = None
    verified_fields: Optional[dict[str, Any]] = None


class EligibilityCheck(BaseModel):
    provider_id: int
    service_type: str
    required_tags: Optional[list[str]] = None
