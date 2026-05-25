"""
AI家政双向信任匹配平台 - FastAPI后端入口
启动命令: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
接口文档: http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from database.database import init_db
from api.auth import router as auth_router
from api.certification import qualification_router, router as cert_router
from api.service_standard import router as service_router
from api.matching import router as match_router
from api.dispute import router as dispute_router
from api.order import router as order_router
from api.review import router as review_router
from api.admin import router as admin_router
from api.video import router as video_router

# 创建应用
app = FastAPI(
    title="AI家政双向信任匹配平台",
    description="提供用户认证、AI资质核验、服务标准量化、双向智能匹配、纠纷仲裁、数据统计等功能",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 静态文件目录（上传的图片等）
os.makedirs("uploads", exist_ok=True)
os.makedirs("uploads/videos", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# 注册路由
app.include_router(auth_router)
app.include_router(cert_router)
app.include_router(qualification_router)
app.include_router(service_router)
app.include_router(match_router)
app.include_router(dispute_router)
app.include_router(order_router)
app.include_router(review_router)
app.include_router(admin_router)
app.include_router(video_router)


@app.on_event("startup")
def startup():
    """应用启动时初始化数据库"""
    init_db()
    print("=" * 50)
    print("  AI家政双向信任匹配平台 已启动")
    print("  接口文档: http://localhost:8000/docs")
    print("  管理后台: admin / admin123")
    print("=" * 50)


@app.get("/", summary="平台首页")
def root():
    return {
        "name": "AI家政双向信任匹配平台",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
