"""AI双向智能匹配模块API"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.database import get_db
from database.models import User, Order
from schemas.matching import BookingCreate
from services.matching_service import get_top_n_matches
from utils.response import success, error
from utils.security import decode_access_token
import time

router = APIRouter(prefix="/api/match", tags=["AI双向匹配"])


@router.get("/recommend", summary="获取Top5推荐从业者")
async def api_recommend(token: str, service_category: str = None, db: Session = Depends(get_db)):
    """
    AI为雇主推荐最匹配的Top5从业者
    综合信用分、技能、距离、时间、场景适配度
    """
    payload = decode_access_token(token)
    if not payload or payload["role"] != "employer":
        return error("仅雇主可使用匹配推荐", 403)

    employer = db.query(User).filter(User.id == payload["user_id"]).first()
    if not employer:
        return error("雇主不存在", 404)

    # 临时设置雇主的需求类别以便匹配
    if service_category:
        employer.service_category = service_category

    matches = get_top_n_matches(db, employer, n=5)
    return success(matches, f"为您推荐{len(matches)}位匹配从业者")


@router.post("/booking", summary="发起预约")
async def api_booking(body: BookingCreate, token: str, db: Session = Depends(get_db)):
    """雇主向匹配的从业者发起服务预约"""
    payload = decode_access_token(token)
    if not payload or payload["role"] != "employer":
        return error("仅雇主可发起预约", 403)

    employer = db.query(User).filter(User.id == payload["user_id"]).first()
    worker = db.query(User).filter(User.id == body.worker_id, User.role == "worker").first()
    if not worker:
        return error("从业者不存在", 404)

    order_no = f"HS{int(time.time() * 1000)}"
    order = Order(
        order_no=order_no,
        employer_id=employer.id,
        worker_id=worker.id,
        service_category=body.service_category,
        service_date=body.service_date,
        service_time=body.service_time,
        address=body.address or employer.address or "",
        remark=body.remark or "",
        status="pending",
        price=99.0,  # 默认价格，实际可根据服务类别动态定价
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    return success({
        "order_id": order.id,
        "order_no": order.order_no,
        "status": order.status,
    }, "预约已发送，等待从业者确认")


@router.put("/booking/{order_id}/accept", summary="从业者接受预约")
async def api_accept_booking(order_id: int, token: str, db: Session = Depends(get_db)):
    """从业者接受雇主的预约"""
    payload = decode_access_token(token)
    if not payload or payload["role"] != "worker":
        return error("仅从业者可操作", 403)

    order = db.query(Order).filter(
        Order.id == order_id, Order.worker_id == payload["user_id"], Order.status == "pending"
    ).first()
    if not order:
        return error("订单不存在或状态不允许接单", 404)

    order.status = "accepted"
    db.commit()
    return success(None, "已接受预约，请按时服务")


@router.put("/booking/{order_id}/reject", summary="从业者拒绝预约")
async def api_reject_booking(order_id: int, token: str, db: Session = Depends(get_db)):
    """从业者拒绝雇主预约"""
    payload = decode_access_token(token)
    if not payload or payload["role"] != "worker":
        return error("仅从业者可操作", 403)

    order = db.query(Order).filter(
        Order.id == order_id, Order.worker_id == payload["user_id"], Order.status == "pending"
    ).first()
    if not order:
        return error("订单不存在或状态不允许操作", 404)

    order.status = "cancelled"
    # 将订单worker_id置空，以便重新匹配
    order.worker_id = None
    db.commit()
    return success(None, "已拒绝预约")
