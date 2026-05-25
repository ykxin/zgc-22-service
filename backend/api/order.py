"""订单管理模块API"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.database import get_db
from database.models import Order, User, CheckIn, Review
from utils.response import success, error, paginate
from utils.security import decode_access_token

router = APIRouter(prefix="/api/order", tags=["订单管理"])


@router.get("/list", summary="我的订单列表")
async def api_order_list(
    token: str,
    page: int = 1,
    page_size: int = 10,
    status: str = None,
    db: Session = Depends(get_db),
):
    """获取当前用户的订单列表"""
    payload = decode_access_token(token)
    if not payload:
        return error("令牌无效", 401)

    query = db.query(Order)
    if payload["role"] == "employer":
        query = query.filter(Order.employer_id == payload["user_id"])
    elif payload["role"] == "worker":
        query = query.filter(Order.worker_id == payload["user_id"])

    if status:
        query = query.filter(Order.status == status)

    total = query.count()
    orders = query.order_by(Order.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    return paginate([{
        "id": o.id,
        "order_no": o.order_no,
        "employer_id": o.employer_id,
        "worker_id": o.worker_id,
        "service_category": o.service_category,
        "service_date": o.service_date,
        "service_time": o.service_time,
        "address": o.address,
        "status": o.status,
        "price": o.price,
        "acceptance_score": o.acceptance_score,
        "created_at": str(o.created_at),
    } for o in orders], total, page, page_size)


@router.get("/{order_id}", summary="订单详情")
async def api_order_detail(order_id: int, token: str, db: Session = Depends(get_db)):
    """获取订单详情，包含打卡记录"""
    payload = decode_access_token(token)
    if not payload:
        return error("令牌无效", 401)

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return error("订单不存在", 404)

    # 验证权限
    if payload["user_id"] not in [order.employer_id, order.worker_id] and payload["role"] != "admin":
        return error("无权查看", 403)

    checkins = db.query(CheckIn).filter(CheckIn.order_id == order_id).order_by(CheckIn.step_order).all()

    return success({
        "id": order.id,
        "order_no": order.order_no,
        "employer_id": order.employer_id,
        "worker_id": order.worker_id,
        "service_category": order.service_category,
        "service_date": order.service_date,
        "service_time": order.service_time,
        "address": order.address,
        "remark": order.remark,
        "status": order.status,
        "price": order.price,
        "acceptance_score": order.acceptance_score,
        "acceptance_report": order.acceptance_report,
        "created_at": str(order.created_at),
        "checkins": [{
            "id": c.id,
            "step_name": c.step_name,
            "step_order": c.step_order,
            "is_done": c.is_done,
            "image_url": c.image_url,
            "remark": c.remark,
            "ai_score": c.ai_score,
        } for c in checkins],
    })


@router.put("/{order_id}/status", summary="更新订单状态")
async def api_update_order_status(
    order_id: int,
    token: str,
    status: str,
    db: Session = Depends(get_db),
):
    """更新订单状态"""
    payload = decode_access_token(token)
    if not payload:
        return error("令牌无效", 401)

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return error("订单不存在", 404)

    # 状态流转验证
    valid_transitions = {
        "pending": ["accepted", "cancelled"],
        "accepted": ["in_progress", "cancelled"],
        "in_progress": ["done"],
        "done": ["completed"],
    }
    if status not in valid_transitions.get(order.status, []):
        return error(f"不允许从 {order.status} 变更为 {status}")

    order.status = status
    db.commit()
    return success(None, f"订单状态已变更为 {status}")
