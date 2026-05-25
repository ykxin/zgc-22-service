"""数据库ORM模型 - 完整表结构"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database.database import Base

class User(Base):
    """用户表 - 雇主/从业者/管理员"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone = Column(String(20), unique=True, nullable=False, index=True)         # 手机号（管理员用admin）
    password = Column(String(255), nullable=False)                              # 加密密码
    role = Column(String(20), nullable=False, default="employer")               # employer/worker/admin
    nickname = Column(String(50))                                               # 昵称
    avatar = Column(String(500))                                                # 头像URL
    real_name = Column(String(50))                                              # 真实姓名
    id_card = Column(String(18))                                                # 身份证号
    gender = Column(String(4))                                                  # 性别
    age = Column(Integer)                                                       # 年龄
    address = Column(String(200))                                               # 地址
    # 雇主画像字段
    family_members = Column(Text)                                               # 家庭成员描述
    house_type = Column(String(50))                                             # 户型
    schedule = Column(String(100))                                              # 作息时间
    has_elderly = Column(Integer, default=0)                                    # 有老人
    has_children = Column(Integer, default=0)                                   # 有小孩
    has_pet = Column(Integer, default=0)                                        # 有宠物
    # 从业者画像字段
    skills = Column(Text)                                                       # 技能标签，逗号分隔
    experience_years = Column(Integer, default=0)                               # 从业年限
    good_at = Column(Text)                                                      # 擅长场景
    work_time = Column(String(100))                                             # 可服务时间
    credit_score = Column(Float, default=80.0)                                  # 信用评分(0-100)
    risk_level = Column(String(10), default="低")                               # 风险等级：低/中/高
    lat = Column(Float, default=0.0)                                            # 纬度
    lng = Column(Float, default=0.0)                                            # 经度
    status = Column(Integer, default=1)                                         # 0禁用 1正常
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    certifications = relationship("Certification", back_populates="user")
    qualification_tags = relationship("ProviderQualificationTag", back_populates="provider")
    orders_as_employer = relationship("Order", foreign_keys="Order.employer_id", back_populates="employer")
    orders_as_worker = relationship("Order", foreign_keys="Order.worker_id", back_populates="worker")

class Certification(Base):
    """从业者资质表"""
    __tablename__ = "certifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    cert_type = Column(String(30), nullable=False)                              # id_card/health_cert/qualification
    cert_number = Column(String(50))                                            # 证件编号
    real_name = Column(String(50))                                              # OCR识别的姓名
    expire_date = Column(String(20))                                            # 有效期 yyyy-mm-dd
    image_url = Column(String(500))                                             # 证件图片路径
    ocr_result = Column(Text)                                                   # OCR识别原始结果JSON
    status = Column(String(20), default="pending")                              # pending/passed/expired/rejected
    reject_reason = Column(String(200))                                         # 驳回原因
    doc_name = Column(String(128))                                               # 证件/材料名称
    issuing_authority = Column(String(128))                                      # 发证机构
    issue_date = Column(String(20))                                              # 签发日期 yyyy-mm-dd
    verification_source = Column(String(64), default="ai_model")                 # ai_model/human_reviewer/third_party
    ai_confidence = Column(Float)                                                # AI识别置信度
    reviewer_id = Column(Integer, ForeignKey("users.id"))                        # 审核人
    review_comment = Column(Text)                                                # 审核意见
    extracted_fields = Column(Text)                                              # AI结构化字段JSON
    suggested_tags = Column(Text)                                                # AI候选标签JSON
    risk_flags = Column(Text)                                                    # AI风险提示JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="certifications")

class QualificationTagDefinition(Base):
    """资质标签定义表"""
    __tablename__ = "qualification_tag_definition"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tag_code = Column(String(64), unique=True, nullable=False, index=True)
    tag_name = Column(String(128), nullable=False)
    tag_category = Column(String(64), nullable=False)                            # identity/health/skill/credit/performance/service_preference/risk
    description = Column(Text)
    display_priority = Column(Integer, default=100)
    is_sensitive = Column(Integer, default=0)                                    # 0否 1是
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ProviderQualificationTag(Base):
    """服务人员资质标签表"""
    __tablename__ = "provider_qualification_tag"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider_id = Column(Integer, ForeignKey("users.id"), nullable=False)         # provider_id 等同从业者 user_id
    tag_code = Column(String(64), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="pending")               # active/pending/rejected/expired/warning/revoked
    trust_level = Column(Integer, nullable=False, default=2)                     # 1-5
    source_type = Column(String(64))                                             # document/profile/performance/system
    source_id = Column(Integer)
    confidence = Column(Float)
    visible_to_customer = Column(Integer, default=1)                             # 0否 1是
    valid_from = Column(String(20))
    valid_until = Column(String(20))
    generated_by = Column(String(32), default="system_rule")                     # system_rule/ai_model/human_reviewer/third_party_sync
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    provider = relationship("User", back_populates="qualification_tags")

class AiQualificationExtraction(Base):
    """AI资质材料解析结果表"""
    __tablename__ = "ai_qualification_extraction"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("certifications.id"), nullable=False)
    provider_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    model_name = Column(String(64), default="mock-qualification-ocr-v1")
    extracted_json = Column(Text)
    suggested_tags = Column(Text)
    risk_flags = Column(Text)
    confidence = Column(Float)
    status = Column(String(32), default="pending_review")
    created_at = Column(DateTime, default=datetime.utcnow)

class SopTemplate(Base):
    """SOP服务标准模板表"""
    __tablename__ = "sop_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(30), nullable=False)                               # 保洁/育儿/养老陪护
    name = Column(String(100), nullable=False)                                  # 步骤名称
    step_order = Column(Integer, nullable=False)                                # 步骤序号
    description = Column(Text)                                                  # 步骤说明
    default_score = Column(Float, default=10.0)                                 # 默认分值
    status = Column(Integer, default=1)                                         # 0下架 1上架
    created_at = Column(DateTime, default=datetime.utcnow)

class CustomStandard(Base):
    """雇主自定义服务标准"""
    __tablename__ = "custom_standards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category = Column(String(30), nullable=False)                               # 服务类别
    name = Column(String(100), nullable=False)                                  # 自定义要求名称
    weight = Column(Float, default=1.0)                                         # 权重
    description = Column(Text)                                                  # 要求描述
    created_at = Column(DateTime, default=datetime.utcnow)

class Order(Base):
    """服务订单表"""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(30), unique=True, nullable=False)                  # 订单编号
    employer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    worker_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    service_category = Column(String(30), nullable=False)                       # 保洁/育儿/养老陪护
    service_date = Column(String(20))                                           # 预约服务日期
    service_time = Column(String(20))                                           # 预约服务时段
    address = Column(String(200))                                               # 服务地址
    remark = Column(Text)                                                       # 备注
    status = Column(String(20), default="pending")                              # pending/accepted/in_progress/done/completed/cancelled
    price = Column(Float, default=0.0)                                          # 服务价格
    acceptance_score = Column(Float)                                            # AI验收得分
    acceptance_report = Column(Text)                                            # 验收报告JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employer = relationship("User", foreign_keys=[employer_id], back_populates="orders_as_employer")
    worker = relationship("User", foreign_keys=[worker_id], back_populates="orders_as_worker")
    checkins = relationship("CheckIn", back_populates="order")
    reviews = relationship("Review", back_populates="order")
    disputes = relationship("Dispute", back_populates="order")
    videos = relationship("ServiceVideo", back_populates="order")

class CheckIn(Base):
    """服务打卡记录表"""
    __tablename__ = "checkins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    step_name = Column(String(100), nullable=False)                             # SOP步骤名称
    step_order = Column(Integer, nullable=False)                                # 步骤序号
    is_done = Column(Integer, default=1)                                        # 是否完成 1是 0否
    image_url = Column(String(500))                                             # 打卡图片
    remark = Column(Text)                                                       # 备注
    ai_score = Column(Float)                                                    # AI对该步骤打分
    created_at = Column(DateTime, default=datetime.utcnow)

    order = relationship("Order", back_populates="checkins")

class Review(Base):
    """评价表"""
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)       # 评价人
    target_id = Column(Integer, ForeignKey("users.id"), nullable=False)         # 被评价人
    rating = Column(Float, nullable=False)                                      # 评分 1-5
    content = Column(Text)                                                      # 评价内容
    tags = Column(String(200))                                                  # 评价标签，逗号分隔
    created_at = Column(DateTime, default=datetime.utcnow)

    order = relationship("Order", back_populates="reviews")

class Dispute(Base):
    """纠纷记录表"""
    __tablename__ = "disputes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    initiator_id = Column(Integer, ForeignKey("users.id"), nullable=False)      # 发起人
    dispute_type = Column(String(30), nullable=False)                           # service_quality/salary/item_damage
    description = Column(Text, nullable=False)                                  # 纠纷描述
    evidence = Column(Text)                                                     # 自动取证的证据JSON
    ai_judgment = Column(Text)                                                  # AI判定结果JSON
    responsible_party = Column(String(20))                                      # employer/worker/both
    suggestion = Column(Text)                                                   # 处理建议
    status = Column(String(20), default="pending")                              # pending/judged/executed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    order = relationship("Order", back_populates="disputes")

class ServiceVideo(Base):
    """服务视频表"""
    __tablename__ = "service_videos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_url = Column(String(500), nullable=False)                                # 视频文件路径
    status = Column(String(20), default="uploaded")                              # uploaded/analyzing/done/failed
    video_score = Column(Float)                                                   # AI综合评分 0-100
    analysis_result = Column(Text)                                                # AI分析结果JSON
    is_locked = Column(Integer, default=0)                                        # 1=纠纷期间锁定
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    order = relationship("Order", back_populates="videos")
    uploader = relationship("User", foreign_keys=[uploader_id])


class ChatRecord(Base):
    """聊天记录表（用于纠纷取证）"""
    __tablename__ = "chat_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class SmsCode(Base):
    """短信验证码表"""
    __tablename__ = "sms_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone = Column(String(20), nullable=False)
    code = Column(String(6), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_used = Column(Integer, default=0)
