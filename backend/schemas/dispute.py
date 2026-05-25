"""纠纷相关Pydantic模型"""
from pydantic import BaseModel, Field
from typing import Literal


class DisputeCreate(BaseModel):
    order_id: int
    dispute_type: Literal["service_quality", "salary", "item_damage", "malicious_review"] = Field(
        ..., description="纠纷类型：service_quality/salary/item_damage/malicious_review"
    )
    description: str = Field(..., min_length=10, max_length=500, description="纠纷描述，10-500字")
