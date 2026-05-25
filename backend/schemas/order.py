"""订单相关Pydantic模型"""
from pydantic import BaseModel, Field
from typing import Optional

class OrderQuery(BaseModel):
    page: int = Field(default=1)
    page_size: int = Field(default=10)
    status: Optional[str] = None
