"""评价相关Pydantic模型"""
from pydantic import BaseModel, Field
from typing import Optional

class ReviewCreate(BaseModel):
    order_id: int
    rating: float = Field(..., ge=1, le=5, description="评分1-5")
    content: Optional[str] = None
    tags: Optional[str] = None
