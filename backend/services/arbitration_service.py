"""
AI纠纷判定与仲裁服务
自动取证、责任判定、建议生成
"""
import json
from datetime import datetime
from sqlalchemy.orm import Session
from database.models import Order, CheckIn, Review, ChatRecord, Dispute, ServiceVideo
from services.video_analysis_service import detect_malicious_review

DAMAGE_KEYWORDS = ["损坏", "坏了", "破了", "摔碎", "划痕", "损毁", "碎了", "弄坏", "打碎"]


def gather_evidence(db: Session, order_id: int) -> dict:
    """
    自动取证：收集订单相关的所有数据
    包括订单信息、验收报告、打卡记录、聊天记录、评价记录、视频分析结果
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return {}

    checkins = db.query(CheckIn).filter(CheckIn.order_id == order_id).order_by(CheckIn.step_order).all()
    chats = db.query(ChatRecord).filter(ChatRecord.order_id == order_id).order_by(ChatRecord.created_at).all()
    reviews = db.query(Review).filter(Review.order_id == order_id).all()
    videos = db.query(ServiceVideo).filter(
        ServiceVideo.order_id == order_id,
        ServiceVideo.status == "done",
    ).all()

    video_scores = [v.video_score for v in videos if v.video_score is not None]
    avg_video_score = round(sum(video_scores) / len(video_scores), 1) if video_scores else None

    evidence = {
        "订单信息": {
            "订单编号": order.order_no,
            "服务类别": order.service_category,
            "服务日期": order.service_date,
            "服务时间": order.service_time,
            "地址": order.address,
            "状态": order.status,
            "金额": order.price,
        },
        "验收报告": json.loads(order.acceptance_report) if order.acceptance_report else None,
        "验收得分": order.acceptance_score,
        "打卡记录": [
            {
                "步骤": c.step_name,
                "序号": c.step_order,
                "完成": "是" if c.is_done else "否",
                "AI评分": c.ai_score,
                "备注": c.remark,
                "时间": str(c.created_at),
            }
            for c in checkins
        ],
        "聊天记录": [
            {
                "发送者ID": ch.sender_id,
                "内容": ch.content,
                "时间": str(ch.created_at),
            }
            for ch in chats
        ],
        "评价记录": [
            {
                "评分": r.rating,
                "内容": r.content,
                "标签": r.tags,
            }
            for r in reviews
        ],
        "视频记录": [
            {
                "视频ID": v.id,
                "得分": v.video_score,
                "状态": v.status,
                "上传时间": str(v.created_at),
            }
            for v in videos
        ],
        "视频得分": avg_video_score,
    }

    return evidence


def analyze_dispute(evidence: dict, dispute_type: str, description: str) -> dict:
    """
    AI责任判定引擎
    根据纠纷类型和证据进行分析，输出责任方和判定理由
    """
    order_info = evidence.get("订单信息", {})
    raw_score = evidence.get("验收得分")
    acceptance_score = raw_score  # 保留 None，不强制转 0
    checkins = evidence.get("打卡记录", [])
    chat_records = evidence.get("聊天记录", [])
    reviews = evidence.get("评价记录", [])
    video_score = evidence.get("视频得分")

    total_steps = len(checkins) if checkins else 1
    done_steps = sum(1 for c in checkins if c["完成"] == "是")
    completion_rate = done_steps / total_steps if total_steps > 0 else 0

    judgment = {
        "纠纷类型": dispute_type,
        "纠纷描述": description,
        "分析时间": datetime.utcnow().isoformat(),
    }

    if dispute_type == "service_quality":
        if acceptance_score is not None and acceptance_score < 60:
            # 视频评分高时降低处罚力度
            if video_score is not None and video_score >= 80:
                judgment["责任方"] = "both"
                judgment["判定理由"] = f"AI验收得分{acceptance_score}分偏低，但视频评分{video_score}分显示操作规范，存在评分标准差异"
                judgment["处理建议"] = "建议平台复核验收标准，从业者补做争议项目"
            else:
                judgment["责任方"] = "worker"
                judgment["判定理由"] = f"AI验收得分{acceptance_score}分，低于60分合格线，服务未达标"
                judgment["处理建议"] = "建议从业者免费补服务一次，或退还50%服务费"
        elif completion_rate < 0.7:
            judgment["责任方"] = "worker"
            judgment["判定理由"] = f"服务步骤完成率仅{completion_rate:.0%}，多项SOP步骤未完成"
            judgment["处理建议"] = "建议按未完成步骤比例退还相应费用"
        elif acceptance_score is not None and acceptance_score >= 80:
            judgment["责任方"] = "employer"
            judgment["判定理由"] = f"AI验收得分{acceptance_score}分，服务达标，雇主投诉依据不足"
            judgment["处理建议"] = "建议驳回纠纷，维持服务完成状态"
        else:
            judgment["责任方"] = "both"
            judgment["判定理由"] = "服务完成度中等，双方可能存在沟通误解"
            judgment["处理建议"] = "建议平台协调，从业者补做未达标项目"

    elif dispute_type == "salary":
        price = order_info.get("金额", 0)
        if acceptance_score is None:
            judgment["责任方"] = "both"
            judgment["判定理由"] = "订单尚无验收报告，无法量化服务质量"
            judgment["处理建议"] = "建议平台人工核查后按实际完成情况结算"
        elif acceptance_score >= 70:
            judgment["责任方"] = "employer"
            judgment["判定理由"] = f"验收得分{acceptance_score}分，服务已完成应正常结算"
            judgment["处理建议"] = f"建议雇主按约定支付{price}元服务费"
        else:
            pct = acceptance_score / 100
            judgment["责任方"] = "both"
            judgment["判定理由"] = f"服务验收得分{acceptance_score}分，未达70分结算线"
            judgment["处理建议"] = f"建议按验收得分比例支付，应付{price * pct:.0f}元"

    elif dispute_type == "item_damage":
        has_damage_evidence = any(
            any(kw in ch.get("内容", "") for kw in DAMAGE_KEYWORDS)
            for ch in chat_records
        )
        if has_damage_evidence:
            judgment["责任方"] = "worker"
            judgment["判定理由"] = "聊天记录中存在物品损坏相关描述，从业者需承担赔偿责任"
            judgment["处理建议"] = "建议从业者按物品价值赔偿，或通过平台保险理赔"
        else:
            judgment["责任方"] = "both"
            judgment["判定理由"] = "无充分证据证明物品损坏责任归属"
            judgment["处理建议"] = "建议双方协商，平台提供调解服务"

    elif dispute_type == "malicious_review":
        review_ratings = [r.get("评分", 5) for r in reviews]
        is_malicious = detect_malicious_review(video_score, review_ratings) if video_score is not None else False
        if is_malicious:
            judgment["责任方"] = "employer"
            judgment["判定理由"] = f"视频AI得分{video_score}分（≥80），但评价评分低于3分，疑似恶意差评"
            judgment["处理建议"] = "建议平台审核该评价，情况属实可予以删除并警告雇主"
        else:
            judgment["责任方"] = "both"
            judgment["判定理由"] = "无充分视频证据支持恶意差评认定" if video_score is None else f"视频得分{video_score}分，不满足恶意差评判定条件"
            judgment["处理建议"] = "建议平台人工审核评价内容"

    else:
        judgment["责任方"] = "both"
        judgment["判定理由"] = "纠纷类型需进一步核实"
        judgment["处理建议"] = "建议平台人工介入处理"

    return judgment


def generate_arbitration_report(dispute: Dispute, evidence: dict, judgment: dict) -> str:
    """生成AI仲裁报告（文本格式）"""
    video_score = evidence.get("视频得分")
    video_line = f"  视频AI得分：{video_score}" if video_score is not None else "  视频记录：无"

    report_lines = [
        "=" * 50,
        "           AI 仲 裁 报 告",
        "=" * 50,
        f"报告生成时间：{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "【基本信息】",
        f"  订单编号：{dispute.order.order_no}",
        f"  纠纷类型：{dispute.dispute_type}",
        f"  发起人ID：{dispute.initiator_id}",
        "",
        "【纠纷描述】",
        f"  {dispute.description}",
        "",
        "【取证摘要】",
        f"  验收得分：{evidence.get('验收得分', 'N/A')}",
        video_line,
        f"  打卡记录数：{len(evidence.get('打卡记录', []))}",
        f"  聊天记录数：{len(evidence.get('聊天记录', []))}",
        "",
        "【AI判定】",
        f"  责任方：{judgment.get('责任方', 'N/A')}",
        f"  判定理由：{judgment.get('判定理由', 'N/A')}",
        "",
        "【处理建议】",
        f"  {judgment.get('处理建议', 'N/A')}",
        "",
        "=" * 50,
        "  本报告由AI仲裁系统自动生成，仅供参考",
        "=" * 50,
    ]
    return "\n".join(report_lines)
