"""服务标准相关Pydantic模型"""
from pydantic import BaseModel, Field
from typing import Optional

class SopCreate(BaseModel):
    category: str = Field(..., description="服务类别")
    name: str = Field(..., description="步骤名称")
    step_order: int = Field(..., description="步骤序号")
    description: Optional[str] = None
    default_score: float = Field(default=10.0, description="默认分值")

class CustomStandardCreate(BaseModel):
    category: str
    name: str
    weight: float = 1.0
    description: Optional[str] = None

class CheckInCreate(BaseModel):
    order_id: int
    step_name: str
    step_order: int
    is_done: int = 1
    remark: Optional[str] = None
