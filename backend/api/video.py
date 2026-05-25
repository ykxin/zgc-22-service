"""服务视频上传与管理 API"""
import json
import os
import secrets
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session
from database.database import get_db
from database.models import Order, ServiceVideo
from services.video_analysis_service import analyze_video
from utils.response import success, error
from utils.security import decode_access_token

router = APIRouter(prefix="/api/video", tags=["服务视频"])

ALLOWED_CONTENT_TYPES = {"video/mp4", "video/quicktime"}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB
MAX_VIDEOS_PER_ORDER = 5
UPLOAD_DIR = "uploads/videos"


@router.post("/upload", summary="上传服务视频")
async def api_upload_video(
    token: str = Form(...),
    order_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """从业者上传服务过程视频，上传后自动触发 AI 分析。"""
    payload = decode_access_token(token)
    if not payload:
        return error("令牌无效", 401)

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return error("订单不存在", 404)

    if order.worker_id != payload["user_id"]:
        return error("只有该订单的从业者才能上传视频", 403)

    if order.status not in ("accepted", "in_progress", "done", "completed"):
        return error("只有已接单或进行中/已完成的订单才能上传视频", 400)

    existing_count = db.query(ServiceVideo).filter(
        ServiceVideo.order_id == order_id
    ).count()
    if existing_count >= MAX_VIDEOS_PER_ORDER:
        return error(f"每个订单最多上传 {MAX_VIDEOS_PER_ORDER} 段视频", 400)

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        return error("仅支持 MP4 或 MOV 格式视频", 400)

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        return error("视频文件不能超过 500MB", 400)

    ext = "mp4" if file.content_type == "video/mp4" else "mov"
    filename = f"{order_id}_{payload['user_id']}_{secrets.token_hex(8)}.{ext}"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, filename)
    with open(file_path, "wb") as f:
        f.write(content)

    video = ServiceVideo(
        order_id=order_id,
        uploader_id=payload["user_id"],
        file_url=file_path,
        status="analyzing",
    )
    db.add(video)
    db.flush()

    os.makedirs(UPLOAD_DIR, exist_ok=True)  # 确保目录存在（测试环境也适用）
    try:
        result = analyze_video(file_path, order_id, db)
        video.video_score = result["video_score"]
        video.analysis_result = json.dumps(result, ensure_ascii=False)
        video.status = "done"
    except Exception:
        video.status = "failed"
        result = None

    db.commit()
    db.refresh(video)

    return success({
        "video_id": video.id,
        "file_url": video.file_url,
        "status": video.status,
        "video_score": video.video_score,
        "analysis_result": result,
    }, "视频上传成功")


@router.get("/list/{order_id}", summary="获取订单视频列表")
async def api_list_videos(order_id: int, token: str, db: Session = Depends(get_db)):
    """获取指定订单的所有视频及分析结果，仅订单参与方可查看。"""
    payload = decode_access_token(token)
    if not payload:
        return error("令牌无效", 401)

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return error("订单不存在", 404)

    if payload["user_id"] not in [order.employer_id, order.worker_id] and payload["role"] != "admin":
        return error("无权查看该订单的视频", 403)

    videos = db.query(ServiceVideo).filter(
        ServiceVideo.order_id == order_id
    ).order_by(ServiceVideo.created_at).all()

    return success([{
        "video_id": v.id,
        "file_url": v.file_url,
        "status": v.status,
        "video_score": v.video_score,
        "is_locked": bool(v.is_locked),
        "analysis_result": json.loads(v.analysis_result) if v.analysis_result else None,
        "created_at": str(v.created_at),
    } for v in videos])


@router.post("/analyze/{video_id}", summary="（预留）触发外部模型重新分析")
async def api_reanalyze_video(video_id: int, token: str, db: Session = Depends(get_db)):
    """
    预留接口：对已上传视频触发外部模型重新分析。
    当前返回 501，接入外部模型后在此实现调用逻辑。
    """
    payload = decode_access_token(token)
    if not payload:
        return error("令牌无效", 401)

    video = db.query(ServiceVideo).filter(ServiceVideo.id == video_id).first()
    if not video:
        return error("视频不存在", 404)

    # TODO: 在此处调用外部视频分析模型
    # result = call_external_model(video.file_url)
    # video.video_score = result["video_score"]
    # video.analysis_result = json.dumps(result)
    # video.status = "done"
    # db.commit()

    return error("外部分析模型尚未接入，请配置后使用", 501)

