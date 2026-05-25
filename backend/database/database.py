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

        # 初始化从业者示例数据（如果不存在）
        demo_workers = [
            {
                "phone": "13800002222",
                "nickname": "李阿姨",
                "skills": "保洁,收纳,擦玻璃",
                "experience_years": 6,
                "good_at": "深度保洁,厨房清洁",
                "work_time": "工作日全天",
                "credit_score": 92,
                "risk_level": "低",
                "address": "北京市海淀区中关村",
                "lat": 39.9834,
                "lng": 116.3229,
            },
            {
                "phone": "13800002223",
                "nickname": "王姐",
                "skills": "育儿,辅食制作,早教",
                "experience_years": 5,
                "good_at": "0-3岁育儿",
                "work_time": "周末全天",
                "credit_score": 88,
                "risk_level": "低",
                "address": "北京市朝阳区望京",
                "lat": 39.9967,
                "lng": 116.4702,
            },
            {
                "phone": "13800002224",
                "nickname": "赵师傅",
                "skills": "养老陪护,康复训练,用药提醒",
                "experience_years": 8,
                "good_at": "失能老人陪护",
                "work_time": "工作日白天",
                "credit_score": 90,
                "risk_level": "低",
                "address": "北京市西城区金融街",
                "lat": 39.9153,
                "lng": 116.3665,
            },
            {
                "phone": "13800002225",
                "nickname": "陈姨",
                "skills": "保洁,熨烫,收纳",
                "experience_years": 10,
                "good_at": "全屋保洁",
                "work_time": "工作日全天",
                "credit_score": 95,
                "risk_level": "低",
                "address": "北京市丰台区丽泽",
                "lat": 39.8719,
                "lng": 116.3059,
            },
            {
                "phone": "13800002226",
                "nickname": "孙姐",
                "skills": "育儿,绘本阅读,日常陪伴",
                "experience_years": 4,
                "good_at": "学龄前陪护",
                "work_time": "工作日白天",
                "credit_score": 84,
                "risk_level": "中",
                "address": "北京市通州区万达",
                "lat": 39.9097,
                "lng": 116.6564,
            },
            {
                "phone": "13800002227",
                "nickname": "周阿姨",
                "skills": "养老陪护,陪诊,饮食护理",
                "experience_years": 7,
                "good_at": "术后护理",
                "work_time": "周末白天",
                "credit_score": 86,
                "risk_level": "中",
                "address": "北京市东城区东直门",
                "lat": 39.9411,
                "lng": 116.4331,
            },
            {
                "phone": "13800002228",
                "nickname": "何师傅",
                "skills": "保洁,地毯清洗,除螨",
                "experience_years": 3,
                "good_at": "深度除螨",
                "work_time": "周末全天",
                "credit_score": 80,
                "risk_level": "中",
                "address": "北京市石景山区鲁谷",
                "lat": 39.9075,
                "lng": 116.2181,
            },
            {
                "phone": "13800002229",
                "nickname": "邓阿姨",
                "skills": "育儿,英语启蒙,陪玩",
                "experience_years": 6,
                "good_at": "3-6岁陪伴",
                "work_time": "工作日全天",
                "credit_score": 89,
                "risk_level": "低",
                "address": "北京市海淀区西二旗",
                "lat": 40.0505,
                "lng": 116.3033,
            },
            {
                "phone": "13800002230",
                "nickname": "高阿姨",
                "skills": "养老陪护,康复训练,心理陪伴",
                "experience_years": 9,
                "good_at": "慢病老人陪护",
                "work_time": "工作日全天",
                "credit_score": 93,
                "risk_level": "低",
                "address": "北京市朝阳区国贸",
                "lat": 39.9086,
                "lng": 116.4660,
            },
            {
                "phone": "13800002231",
                "nickname": "钱姐",
                "skills": "保洁,整理收纳,家电清洗",
                "experience_years": 5,
                "good_at": "全屋收纳整理",
                "work_time": "工作日白天",
                "credit_score": 87,
                "risk_level": "中",
                "address": "北京市大兴区亦庄",
                "lat": 39.8086,
                "lng": 116.5210,
            },
        ]

        default_password = hash_password("123456")
        for worker in demo_workers:
            exists = db.query(User).filter(User.phone == worker["phone"]).first()
            if exists:
                continue
            db.add(User(
                phone=worker["phone"],
                password=default_password,
                role="worker",
                nickname=worker["nickname"],
                skills=worker["skills"],
                experience_years=worker["experience_years"],
                good_at=worker["good_at"],
                work_time=worker["work_time"],
                credit_score=worker["credit_score"],
                risk_level=worker["risk_level"],
                address=worker["address"],
                lat=worker["lat"],
                lng=worker["lng"],
                status=1,
            ))
        db.commit()
    finally:
        db.close()
