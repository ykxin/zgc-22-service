"""管理后台模块API"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database.database import get_db
from database.models import User, Order, Dispute, Review, Certification, SopTemplate
from schemas.certification import CertReview
from utils.response import success, error, paginate
from utils.security import decode_access_token

router = APIRouter(prefix="/api/admin", tags=["管理后台"])


def check_admin(token: str, db: Session):
    """验证管理员权限"""
    payload = decode_access_token(token)
    if not payload or payload["role"] != "admin":
        return None
    return payload


@router.get("/dashboard", summary="数据统计面板")
async def api_dashboard(token: str, db: Session = Depends(get_db)):
    """平台核心数据统计"""
    if not check_admin(token, db):
        return error("无管理员权限", 403)

    total_employers = db.query(User).filter(User.role == "employer").count()
    total_workers = db.query(User).filter(User.role == "worker").count()
    total_orders = db.query(Order).count()
    completed_orders = db.query(Order).filter(Order.status == "completed").count()
    total_disputes = db.query(Dispute).count()
    judged_disputes = db.query(Dispute).filter(Dispute.status == "judged").count()

    # 纠纷率
    dispute_rate = round(total_disputes / total_orders * 100, 2) if total_orders else 0
    # 匹配成功率（accepted及之后状态算匹配成功）
    match_success_count = db.query(Order).filter(Order.status.in_(["accepted", "in_progress", "done", "completed"])).count()
    match_rate = round(match_success_count / total_orders * 100, 2) if total_orders else 0

    # 各服务类别订单量分布
    category_stats = db.query(Order.service_category, func.count(Order.id)).group_by(Order.service_category).all()

    return success({
        "用户统计": {
            "雇主数": total_employers,
            "从业者数": total_workers,
            "总用户数": total_employers + total_workers,
        },
        "订单统计": {
            "总订单数": total_orders,
            "已完成订单": completed_orders,
            "匹配成功率": f"{match_rate}%",
        },
        "纠纷统计": {
            "总纠纷数": total_disputes,
            "已判定纠纷": judged_disputes,
            "纠纷率": f"{dispute_rate}%",
        },
        "类别分布": [{"类别": c[0], "订单数": c[1]} for c in category_stats],
    })


@router.get("/users", summary="用户管理列表")
async def api_user_list(
    token: str,
    role: str = None,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
):
    """管理员查看所有用户"""
    if not check_admin(token, db):
        return error("无管理员权限", 403)

    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    total = query.count()
    users = query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return paginate([{
        "id": u.id,
        "phone": u.phone,
        "role": u.role,
        "nickname": u.nickname,
        "real_name": u.real_name,
        "credit_score": u.credit_score,
        "risk_level": u.risk_level,
        "status": u.status,
        "created_at": str(u.created_at),
    } for u in users], total, page, page_size)


@router.put("/users/{user_id}/status", summary="禁用/启用用户")
async def api_toggle_user(user_id: int, token: str, db: Session = Depends(get_db)):
    if not check_admin(token, db):
        return error("无管理员权限", 403)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return error("用户不存在", 404)
    user.status = 0 if user.status == 1 else 1
    db.commit()
    return success(None, "状态已更新")


@router.get("/certifications", summary="资质审核列表")
async def api_cert_list(
    token: str,
    status: str = None,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
):
    """管理员查看所有资质"""
    if not check_admin(token, db):
        return error("无管理员权限", 403)

    query = db.query(Certification)
    if status:
        query = query.filter(Certification.status == status)
    total = query.count()
    certs = query.order_by(Certification.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return paginate([{
        "id": c.id,
        "user_id": c.user_id,
        "cert_type": c.cert_type,
        "cert_number": c.cert_number,
        "real_name": c.real_name,
        "expire_date": c.expire_date,
        "status": c.status,
        "created_at": str(c.created_at),
    } for c in certs], total, page, page_size)


@router.put("/certifications/{cert_id}/review", summary="审核资质")
async def api_review_cert(
    cert_id: int,
    body: CertReview,
    token: str,
    db: Session = Depends(get_db),
):
    """管理员审核从业者资质"""
    if not check_admin(token, db):
        return error("无管理员权限", 403)

    cert = db.query(Certification).filter(Certification.id == cert_id).first()
    if not cert:
        return error("资质不存在", 404)

    cert.status = body.status
    cert.reject_reason = body.reject_reason
    db.commit()

    return success(None, f"资质已{body.status}")


@router.get("/orders", summary="所有订单列表")
async def api_all_orders(
    token: str,
    page: int = 1,
    page_size: int = 10,
    status: str = None,
    db: Session = Depends(get_db),
):
    """管理员查看所有订单"""
    if not check_admin(token, db):
        return error("无管理员权限", 403)

    query = db.query(Order)
    if status:
        query = query.filter(Order.status == status)
    total = query.count()
    orders = query.order_by(Order.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return paginate([{
        "id": o.id,
        "order_no": o.order_no,
        "employer_id": o.employer_id,
        "worker_id": o.worker_id,
        "service_category": o.service_category,
        "status": o.status,
        "price": o.price,
        "acceptance_score": o.acceptance_score,
        "created_at": str(o.created_at),
    } for o in orders], total, page, page_size)


@router.get("/disputes", summary="所有纠纷列表")
async def api_all_disputes(token: str, page: int = 1, page_size: int = 10, db: Session = Depends(get_db)):
    if not check_admin(token, db):
        return error("无管理员权限", 403)
    query = db.query(Dispute)
    total = query.count()
    items = query.order_by(Dispute.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return paginate([{
        "id": d.id,
        "order_id": d.order_id,
        "dispute_type": d.dispute_type,
        "responsible_party": d.responsible_party,
        "status": d.status,
        "created_at": str(d.created_at),
    } for d in items], total, page, page_size)


@router.get("/sops", summary="SOP管理列表")
async def api_admin_sops(token: str, category: str = None, db: Session = Depends(get_db)):
    if not check_admin(token, db):
        return error("无管理员权限", 403)
    query = db.query(SopTemplate)
    if category:
        query = query.filter(SopTemplate.category == category)
    sops = query.order_by(SopTemplate.category, SopTemplate.step_order).all()
    return success([{
        "id": s.id,
        "category": s.category,
        "name": s.name,
        "step_order": s.step_order,
        "description": s.description,
        "default_score": s.default_score,
        "status": s.status,
    } for s in sops])
