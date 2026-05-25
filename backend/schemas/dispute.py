"""纠纷相关Pydantic模型"""
from pydantic import BaseModel, Field
from typing import Optional

class DisputeCreate(BaseModel):
    order_id: int
    dispute_type: str = Field(..., description="service_quality/salary/item_damage")
    description: str
