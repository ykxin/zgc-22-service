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
    finally:
        db.close()
