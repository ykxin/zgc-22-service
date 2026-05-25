"""AI服务标准量化模块API"""
import json
import os
from fastapi import APIRouter, Depends, Form, UploadFile, File
from sqlalchemy.orm import Session
from database.database import get_db
from database.models import User, Order, CheckIn, SopTemplate, CustomStandard
from schemas.service import SopCreate, CustomStandardCreate, CheckInCreate
from services.sop_service import (
    init_default_sop,
    ai_acceptance_check,
    generate_acceptance_report,
)
from utils.response import success, error, paginate
from utils.security import decode_access_token

router = APIRouter(prefix="/api/service", tags=["AI服务标准"])
CHECKIN_UPLOAD_DIR = "uploads/checkins"
os.makedirs(CHECKIN_UPLOAD_DIR, exist_ok=True)


@router.get("/sops", summary="获取SOP标准列表")
async def api_get_sops(category: str = None, db: Session = Depends(get_db)):
    """获取平台SOP标准（按类别筛选）"""
    init_default_sop(db)  # 确保默认数据存在
    query = db.query(SopTemplate).filter(SopTemplate.status == 1)
    if category:
        query = query.filter(SopTemplate.category == category)
    sops = query.order_by(SopTemplate.category, SopTemplate.step_order).all()

    result = {}
    for s in sops:
        if s.category not in result:
            result[s.category] = []
        result[s.category].append({
            "id": s.id, "name": s.name, "step_order": s.step_order,
            "description": s.description, "default_score": s.default_score,
        })
    return success(result)


@router.post("/sop", summary="新增SOP标准（管理员）")
async def api_create_sop(body: SopCreate, token: str, db: Session = Depends(get_db)):
    """管理员新增SOP步骤"""
    payload = decode_access_token(token)
    if not payload or payload["role"] != "admin":
        return error("无权限", 403)
    sop = SopTemplate(**body.model_dump())
    db.add(sop)
    db.commit()
    return success({"id": sop.id}, "SOP步骤添加成功")


@router.put("/sop/{sop_id}", summary="编辑SOP标准")
async def api_update_sop(sop_id: int, body: SopCreate, token: str, db: Session = Depends(get_db)):
    payload = decode_access_token(token)
    if not payload or payload["role"] != "admin":
        return error("无权限", 403)
    sop = db.query(SopTemplate).filter(SopTemplate.id == sop_id).first()
    if not sop:
        return error("SOP不存在", 404)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(sop, k, v)
    db.commit()
    return success(None, "修改成功")


@router.put("/sop/{sop_id}/toggle", summary="上架/下架SOP步骤")
async def api_toggle_sop(sop_id: int, token: str, db: Session = Depends(get_db)):
    payload = decode_access_token(token)
    if not payload or payload["role"] != "admin":
        return error("无权限", 403)
    sop = db.query(SopTemplate).filter(SopTemplate.id == sop_id).first()
    if not sop:
        return error("SOP不存在", 404)
    sop.status = 0 if sop.status == 1 else 1
    db.commit()
    return success(None, "状态已切换")


@router.post("/custom-standard", summary="雇主自定义服务标准")
async def api_create_custom(body: CustomStandardCreate, token: str, db: Session = Depends(get_db)):
    """雇主为自己的订单添加自定义服务要求"""
    payload = decode_access_token(token)
    if not payload or payload["role"] != "employer":
        return error("仅雇主可自定义标准", 403)

    cs = CustomStandard(employer_id=payload["user_id"], **body.model_dump())
    db.add(cs)
    db.commit()
    return success({"id": cs.id}, "自定义标准已保存")


@router.get("/custom-standards", summary="获取我的自定义标准")
async def api_get_custom_standards(token: str, category: str = None, db: Session = Depends(get_db)):
    payload = decode_access_token(token)
    if not payload:
        return error("令牌无效", 401)
    query = db.query(CustomStandard).filter(CustomStandard.employer_id == payload["user_id"])
    if category:
        query = query.filter(CustomStandard.category == category)
    items = query.all()
    return success([{
        "id": c.id, "category": c.category, "name": c.name,
        "weight": c.weight, "description": c.description,
    } for c in items])


@router.post("/checkin", summary="服务步骤打卡上传")
async def api_checkin(
    token: str = Form(...),
    order_id: int = Form(...),
    step_name: str = Form(...),
    step_order: int = Form(...),
    is_done: int = Form(1),
    remark: str = Form(None),
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    """从业者按SOP步骤打卡，上传验证图片"""
    payload = decode_access_token(token)
    if not payload or payload["role"] != "worker":
        return error("仅从业者可打卡", 403)

    order = db.query(Order).filter(Order.id == order_id, Order.worker_id == payload["user_id"]).first()
    if not order:
        return error("订单不存在或无权操作", 404)

    image_url = None
    if file:
        ext = file.filename.split(".")[-1] if file.filename else "jpg"
        save_name = f"checkin_{order_id}_{step_order}_{os.urandom(4).hex()}.{ext}"
        save_path = os.path.join(CHECKIN_UPLOAD_DIR, save_name)
        with open(save_path, "wb") as f:
            f.write(await file.read())
        image_url = save_path

    checkin = CheckIn(
        order_id=order_id,
        step_name=step_name,
        step_order=step_order,
        is_done=is_done,
        image_url=image_url,
        remark=remark,
    )
    db.add(checkin)
    db.commit()

    return success({"id": checkin.id}, "打卡成功")


@router.post("/acceptance/{order_id}", summary="AI智能验收打分")
async def api_acceptance(order_id: int, token: str, db: Session = Depends(get_db)):
    """
    AI根据打卡数据、图片核验、自定义标准，自动生成验收报告和得分
    """
    payload = decode_access_token(token)
    if not payload:
        return error("令牌无效", 401)

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return error("订单不存在", 404)

    checkins = db.query(CheckIn).filter(CheckIn.order_id == order_id).all()
    if not checkins:
        return error("暂无打卡记录", 400)

    # AI验收
    acceptance_result = ai_acceptance_check(order_id, checkins, db)
    report = generate_acceptance_report(acceptance_result)
    try:
        report_data = json.loads(report)
        acceptance_result["service_report"] = report_data.get("服务报告")
        acceptance_result["report_images"] = report_data.get("证据图片", [])
    except json.JSONDecodeError:
        acceptance_result["service_report"] = None
        acceptance_result["report_images"] = []

    # 更新订单
    order.acceptance_score = acceptance_result["total_score"]
    order.acceptance_report = report
    if acceptance_result["total_score"] >= 0.6:
        order.status = "done"
    db.commit()

    return success(acceptance_result, f"验收完成，得分：{acceptance_result['total_score']}")
