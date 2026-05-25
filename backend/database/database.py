"""数据库连接与初始化"""
from sqlalchemy import create_engine
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

def init_db():
    """初始化数据库表，并插入默认管理员"""
    from database.models import Base
    Base.metadata.create_all(bind=engine)
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
