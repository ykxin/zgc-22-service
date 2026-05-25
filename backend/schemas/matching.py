"""匹配相关Pydantic模型"""
from pydantic import BaseModel, Field
from typing import Optional

class BookingCreate(BaseModel):
    worker_id: int = Field(..., description="从业者ID")
    service_category: str = Field(..., description="服务类别")
    service_date: str = Field(..., description="服务日期")
    service_time: str = Field(..., description="服务时段")
    address: Optional[str] = None
    remark: Optional[str] = None
