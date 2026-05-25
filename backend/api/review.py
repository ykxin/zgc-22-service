"""评价模块API"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.database import get_db
from database.models import Order, Review, User, Certification
from schemas.review import ReviewCreate
from services.credit_service import calculate_credit_score
from utils.response import success, error
from utils.security import decode_access_token

router = APIRouter(prefix="/api/review", tags=["评价管理"])


@router.post("/create", summary="提交评价")
async def api_create_review(body: ReviewCreate, token: str, db: Session = Depends(get_db)):
    """
    双向评价：雇主评从业者 / 从业者评雇主
    评价会影响信用分
    """
    payload = decode_access_token(token)
    if not payload:
        return error("令牌无效", 401)

    order = db.query(Order).filter(Order.id == body.order_id).first()
    if not order:
        return error("订单不存在", 404)
    if order.status != "completed" and order.status != "done":
        return error("订单未完成，无法评价")

    # 确定被评价人
    if payload["user_id"] == order.employer_id:
        target_id = order.worker_id
    elif payload["user_id"] == order.worker_id:
        target_id = order.employer_id
    else:
        return error("无权评价", 403)

    # 检查是否已评价
    existing = db.query(Review).filter(
        Review.order_id == body.order_id,
        Review.reviewer_id == payload["user_id"],
    ).first()
    if existing:
        return error("您已评价过该订单")

    review = Review(
        order_id=body.order_id,
        reviewer_id=payload["user_id"],
        target_id=target_id,
        rating=body.rating,
        content=body.content or "",
        tags=body.tags or "",
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    # 如果被评价人是从业者，更新其信用分
    target = db.query(User).filter(User.id == target_id).first()
    if target and target.role == "worker":
        # 重新计算信用评分
        reviews = db.query(Review).filter(Review.target_id == target_id).all()
        certifications = db.query(Certification).filter(Certification.user_id == target_id).all()
        orders_completed = db.query(Order).filter(
            Order.worker_id == target_id
        ).all()
        credit_result = calculate_credit_score(certifications, orders_completed, reviews)
        target.credit_score = credit_result["score"]
        target.risk_level = credit_result["risk_level"]
        db.commit()

    # 检查是否双方都评价了，都评价后订单变为completed
    review_count = db.query(Review).filter(Review.order_id == body.order_id).count()
    if review_count >= 2:
        order.status = "completed"
        db.commit()

    return success({"id": review.id}, "评价成功")
