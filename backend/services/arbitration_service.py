"""
AI纠纷判定与仲裁服务
自动取证、责任判定、建议生成
"""
import json
from datetime import datetime
from sqlalchemy.orm import Session
from database.models import Order, CheckIn, Review, ChatRecord, Dispute


def gather_evidence(db: Session, order_id: int) -> dict:
    """
    自动取证：收集订单相关的所有数据
    包括订单信息、验收报告、打卡记录、聊天记录、评价记录
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return {}

    checkins = db.query(CheckIn).filter(CheckIn.order_id == order_id).order_by(CheckIn.step_order).all()
    chats = db.query(ChatRecord).filter(ChatRecord.order_id == order_id).order_by(ChatRecord.created_at).all()
    reviews = db.query(Review).filter(Review.order_id == order_id).all()

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
    }

    return evidence


def analyze_dispute(evidence: dict, dispute_type: str, description: str) -> dict:
    """
    AI责任判定引擎

    根据纠纷类型和证据进行分析，输出责任方和判定理由
    """
    order_info = evidence.get("订单信息", {})
    acceptance_score = evidence.get("验收得分", 0) or 0
    checkins = evidence.get("打卡记录", [])
    chat_records = evidence.get("聊天记录", [])
    reviews = evidence.get("评价记录", [])

    total_steps = len(checkins) if checkins else 1
    done_steps = sum(1 for c in checkins if c["完成"] == "是")
    completion_rate = done_steps / total_steps if total_steps > 0 else 0

    judgment = {
        "纠纷类型": dispute_type,
        "纠纷描述": description,
        "分析时间": datetime.utcnow().isoformat(),
    }

    if dispute_type == "service_quality":
        # 服务质量纠纷判定
        if acceptance_score is not None and acceptance_score < 60:
            judgment["责任方"] = "worker"
            judgment["判定理由"] = f"AI验收得分{acceptance_score}分，低于60分合格线，服务未达标"
            judgment["处理建议"] = "建议从业者免费补服务一次，或退还50%服务费"
        elif completion_rate < 0.7:
            judgment["责任方"] = "worker"
            judgment["判定理由"] = f"服务步骤完成率仅{completion_rate:.0%}，多项SOP步骤未完成"
            judgment["处理建议"] = "建议按未完成步骤比例退还相应费用"
        elif acceptance_score and acceptance_score >= 80:
            judgment["责任方"] = "employer"
            judgment["判定理由"] = f"AI验收得分{acceptance_score}分，服务达标，雇主投诉依据不足"
            judgment["处理建议"] = "建议驳回纠纷，维持服务完成状态"
        else:
            judgment["责任方"] = "both"
            judgment["判定理由"] = "服务完成度中等，双方可能存在沟通误解"
            judgment["处理建议"] = "建议平台协调，从业者补做未达标项目"

    elif dispute_type == "salary":
        # 薪资纠纷判定
        price = order_info.get("金额", 0)
        if acceptance_score and acceptance_score >= 70:
            judgment["责任方"] = "employer"
            judgment["判定理由"] = f"验收得分{acceptance_score}分，服务已完成应正常结算"
            judgment["处理建议"] = f"建议雇主按约定支付{price}元服务费"
        else:
            judgment["责任方"] = "both"
            judgment["判定理由"] = "服务验收不达标，建议协商调整费用"
            judgment["处理建议"] = f"建议按验收得分比例支付，应付{max(0, price * (acceptance_score or 0) / 100):.0f}元"

    elif dispute_type == "item_damage":
        # 物品损耗纠纷
        has_damage_evidence = any(
            "损坏" in ch.get("内容", "") or "坏了" in ch.get("内容", "")
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

    else:
        judgment["责任方"] = "both"
        judgment["判定理由"] = "纠纷类型需进一步核实"
        judgment["处理建议"] = "建议平台人工介入处理"

    return judgment


def generate_arbitration_report(dispute: Dispute, evidence: dict, judgment: dict) -> str:
    """
    生成AI仲裁报告（文本格式）
    """
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
