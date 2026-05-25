"""数据库连接与初始化"""
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

SQLALCHEMY_DATABASE_URL = "sqlite:///./housekeeping.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, echo=False
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    """数据库会话依赖注入"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema():
    """为旧SQLite库补充新增字段；不做破坏性迁移。"""
    certification_columns = {
        "doc_name": "VARCHAR(128)",
        "issuing_authority": "VARCHAR(128)",
        "issue_date": "VARCHAR(20)",
        "verification_source": "VARCHAR(64)",
        "ai_confidence": "FLOAT",
        "reviewer_id": "INTEGER",
        "review_comment": "TEXT",
        "extracted_fields": "TEXT",
        "suggested_tags": "TEXT",
        "risk_flags": "TEXT",
    }
    inspector = inspect(engine)
    existing = {col["name"] for col in inspector.get_columns("certifications")}
    with engine.begin() as conn:
        for column_name, column_type in certification_columns.items():
            if column_name not in existing:
                conn.execute(text(f"ALTER TABLE certifications ADD COLUMN {column_name} {column_type}"))


def seed_qualification_tags(db):
    """初始化第一批可展示/可匹配资质标签定义。"""
    from database.models import QualificationTagDefinition

    tag_defs = [
        ("identity_verified", "身份已核验", "identity", "实名认证与证件信息已通过平台审核", 10, 0),
        ("phone_verified", "手机号已实名", "identity", "手机号实名状态已核验", 20, 0),
        ("face_verified", "人脸核验通过", "identity", "人脸活体核验通过", 30, 0),
        ("health_verified", "健康证明已核验", "health", "健康证明或体检材料已通过平台审核", 40, 0),
        ("health_certificate_expiring", "健康证明即将过期", "health", "健康证明将在30天内到期", 45, 0),
        ("health_certificate_expired", "健康证明已过期", "risk", "健康证明已超过有效期", 46, 0),
        ("background_check_authorized", "背景核查已授权", "health", "从业者已授权背景核查", 50, 0),
        ("insurance_policy_verified", "已配置服务保险", "health", "服务保险或意外险已审核", 55, 0),
        ("housekeeping", "家务服务", "skill", "具备家务服务能力", 60, 0),
        ("deep_cleaning", "深度保洁", "skill", "具备深度保洁能力", 61, 0),
        ("organizing", "收纳整理", "skill", "具备收纳整理能力", 62, 0),
        ("family_cooking", "家庭做饭", "skill", "具备家庭餐制作能力", 63, 0),
        ("maternity_care", "母婴护理", "skill", "具备母婴护理能力", 64, 0),
        ("infant_care", "育婴照护", "skill", "具备婴幼儿照护能力", 65, 0),
        ("elderly_care", "老人照护", "skill", "具备老人照护能力", 66, 0),
        ("elderly_care_intermediate", "养老护理员-中级", "skill", "养老护理员中级能力标签", 67, 0),
        ("patient_care", "病患陪护", "skill", "具备病患陪护能力", 68, 0),
        ("first_aid_trained", "具备基础急救培训", "skill", "已完成基础急救相关培训", 69, 0),
        ("live_in_available", "可住家", "service_preference", "接受住家服务模式", 80, 0),
        ("day_shift_available", "可白班", "service_preference", "接受白班服务", 81, 0),
        ("night_shift_available", "可夜班", "service_preference", "接受夜班服务", 82, 0),
        ("pet_family_accepted", "接受宠物家庭", "service_preference", "接受有宠物家庭服务场景", 83, 0),
        ("good_reviews", "平台好评较多", "performance", "历史评价表现较好", 90, 0),
        ("high_repeat_rate", "复购率高", "performance", "历史复购表现较好", 91, 0),
        ("name_mismatch_risk", "证书姓名待复核", "risk", "证书姓名与实名认证姓名不一致或待确认", 95, 0),
        ("suspected_forgery_risk", "证书疑似伪造", "risk", "AI或规则引擎提示证件存在异常", 96, 1),
    ]

    for tag_code, tag_name, category, description, priority, is_sensitive in tag_defs:
        tag = db.query(QualificationTagDefinition).filter(
            QualificationTagDefinition.tag_code == tag_code
        ).first()
        if tag:
            tag.tag_name = tag_name
            tag.tag_category = category
            tag.description = description
            tag.display_priority = priority
            tag.is_sensitive = is_sensitive
        else:
            db.add(QualificationTagDefinition(
                tag_code=tag_code,
                tag_name=tag_name,
                tag_category=category,
                description=description,
                display_priority=priority,
                is_sensitive=is_sensitive,
            ))
    db.commit()


def init_db():
    """初始化数据库表，并插入默认管理员"""
    from database.models import Base
    Base.metadata.create_all(bind=engine)
    ensure_schema()
    db = SessionLocal()
    try:
        from database.models import User
        from utils.security import hash_password
        # 创建默认管理员
        admin = db.query(User).filter(User.phone == "admin").first()
        if not admin:
            admin = User(
                phone="admin",
                password=hash_password("admin123"),
                role="admin",
                nickname="系统管理员",
                status=1
            )
            db.add(admin)
            db.commit()
        seed_qualification_tags(db)
    finally:
        db.close()
