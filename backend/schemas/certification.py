"""资质相关Pydantic模型"""
from pydantic import BaseModel, Field
from typing import Optional

class CertUpload(BaseModel):
    cert_type: str = Field(..., description="证件类型 id_card/health_cert/qualification")

class CertReview(BaseModel):
    status: str = Field(..., description="passed/rejected")
    reject_reason: Optional[str] = None
