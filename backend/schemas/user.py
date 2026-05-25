"""用户相关Pydantic模型"""
from pydantic import BaseModel, Field
from typing import Optional

class UserRegister(BaseModel):
    phone: str = Field(..., description="手机号")
    password: str = Field(..., min_length=6, description="密码")
    sms_code: Optional[str] = Field(None, description="短信验证码")
    role: str = Field(default="employer", description="角色 employer/worker")
    nickname: Optional[str] = None

class UserLogin(BaseModel):
    phone: str
    password: str

class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    real_name: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    # 雇主画像
    family_members: Optional[str] = None
    house_type: Optional[str] = None
    schedule: Optional[str] = None
    has_elderly: Optional[int] = None
    has_children: Optional[int] = None
    has_pet: Optional[int] = None
    # 从业者画像
    skills: Optional[str] = None
    experience_years: Optional[int] = None
    good_at: Optional[str] = None
    work_time: Optional[str] = None

class PasswordReset(BaseModel):
    phone: str
    sms_code: str
    new_password: str = Field(..., min_length=6)

class SmsSend(BaseModel):
    phone: str
