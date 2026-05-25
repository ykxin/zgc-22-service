"""AI纠纷公允判定模块API"""
import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.database import get_db
from database.models import Dispute, Order, ServiceVideo
from schemas.dispute import DisputeCreate
from services.arbitration_service import gather_evidence, analyze_dispute, generate_arbitration_report
from utils.response import success, error
from utils.security import decode_access_token

router = APIRouter(prefix="/api/dispute", tags=["AI纠纷仲裁"])


@router.post("/create", summary="发起纠纷")
async def api_create_dispute(body: DisputeCreate, token: str, db: Session = Depends(get_db)):
    """雇主/从业者提交纠纷申请，AI 自动取证并完成判定。"""
    payload = decode_access_token(token)
    if not payload:
        return error("令牌无效", 401)

    order = db.query(Order).filter(Order.id == body.order_id).first()
    if not order:
        return error("订单不存在", 404)

    if payload["user_id"] not in [order.employer_id, order.worker_id]:
        return error("您不是该订单的参与方", 403)

    if order.status not in ("done", "completed"):
        return error("只有已完成的订单才能发起纠纷", 400)

    existing = db.query(Dispute).filter(
        Dispute.order_id == body.order_id,
        Dispute.status != "executed",
    ).first()
    if existing:
        return error("该订单已有未解决的纠纷，请等待处理完毕后再发起", 400)

    if body.dispute_type == "malicious_review" and payload["user_id"] != order.worker_id:
        return error("恶意差评纠纷只能由从业者发起", 403)

    dispute = Dispute(
        order_id=body.order_id,
        initiator_id=payload["user_id"],
        dispute_type=body.dispute_type,
        description=body.description,
    )
    db.add(dispute)
    db.flush()  # 获取 dispute.id，不提交事务

    # 纠纷期间锁定该订单所有视频
    db.query(ServiceVideo).filter(
        ServiceVideo.order_id == body.order_id
    ).update({"is_locked": 1})

    evidence = gather_evidence(db, body.order_id)
    judgment = analyze_dispute(evidence, body.dispute_type, body.description)
    report = generate_arbitration_report(dispute, evidence, judgment)

    dispute.evidence = json.dumps(evidence, ensure_ascii=False)
    dispute.ai_judgment = json.dumps(judgment, ensure_ascii=False)
    dispute.responsible_party = judgment["责任方"]
    dispute.suggestion = judgment["处理建议"]
    dispute.status = "judged"
    db.commit()
    # refresh 仅在非测试环境下安全；直接用已有数据构造响应
    return success({
        "dispute_id": dispute.id,
        "evidence": evidence,
        "judgment": judgment,
        "report": report,
    }, "纠纷已提交，AI已完成判定")


@router.get("/list", summary="纠纷列表")
async def api_dispute_list(token: str, db: Session = Depends(get_db)):
    """查看与我相关的纠纷"""
    payload = decode_access_token(token)
    if not payload:
        return error("令牌无效", 401)

    disputes = db.query(Dispute).filter(
        (Dispute.initiator_id == payload["user_id"]) |
        (Dispute.order.has(Order.employer_id == payload["user_id"])) |
        (Dispute.order.has(Order.worker_id == payload["user_id"]))
    ).all()

    return success([{
        "id": d.id,
        "order_id": d.order_id,
        "order_no": d.order.order_no,
        "dispute_type": d.dispute_type,
        "description": d.description,
        "responsible_party": d.responsible_party,
        "suggestion": d.suggestion,
        "status": d.status,
        "judgment": json.loads(d.ai_judgment) if d.ai_judgment else None,
        "created_at": str(d.created_at),
    } for d in disputes])


@router.get("/{dispute_id}", summary="纠纷详情")
async def api_dispute_detail(dispute_id: int, token: str, db: Session = Depends(get_db)):
    """获取纠纷详情及AI仲裁报告，仅订单参与方和管理员可查看。"""
    payload = decode_access_token(token)
    if not payload:
        return error("令牌无效", 401)

    dispute = db.query(Dispute).filter(Dispute.id == dispute_id).first()
    if not dispute:
        return error("纠纷不存在", 404)

    order = dispute.order
    if payload["user_id"] not in [order.employer_id, order.worker_id] and payload["role"] != "admin":
        return error("无权查看该纠纷", 403)

    return success({
        "id": dispute.id,
        "order_id": dispute.order_id,
        "dispute_type": dispute.dispute_type,
        "description": dispute.description,
        "evidence": json.loads(dispute.evidence) if dispute.evidence else None,
        "judgment": json.loads(dispute.ai_judgment) if dispute.ai_judgment else None,
        "responsible_party": dispute.responsible_party,
        "suggestion": dispute.suggestion,
        "status": dispute.status,
        "created_at": str(dispute.created_at),
        "updated_at": str(dispute.updated_at),
    })
