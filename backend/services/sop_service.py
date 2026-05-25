"""
AI服务标准（SOP）与智能验收服务
"""
import json
import sqlalchemy.orm
from database.models import CheckIn


# --- 默认SOP模板数据 ---
DEFAULT_SOP = {
    "保洁": [
        {"step_order": 1, "name": "除尘打扫", "description": "家具表面、窗台、踢脚线除尘擦拭", "default_score": 15},
        {"step_order": 2, "name": "地面清洁", "description": "全屋地面清扫、拖洗", "default_score": 20},
        {"step_order": 3, "name": "厨房清洁", "description": "灶台、油烟机表面、水槽、橱柜表面清洁", "default_score": 25},
        {"step_order": 4, "name": "卫浴清洁", "description": "马桶、洗手台、淋浴区、镜面清洁", "default_score": 20},
        {"step_order": 5, "name": "死角清理", "description": "墙角、家具底部、天花板蜘蛛网清理", "default_score": 10},
        {"step_order": 6, "name": "垃圾分类", "description": "全屋垃圾收集、分类、打包", "default_score": 10},
    ],
    "育儿": [
        {"step_order": 1, "name": "晨间护理", "description": "起床、洗漱、穿衣、早餐", "default_score": 15},
        {"step_order": 2, "name": "教育活动", "description": "绘本阅读、早教游戏、手工制作", "default_score": 20},
        {"step_order": 3, "name": "户外活动", "description": "公园散步、体能游戏", "default_score": 15},
        {"step_order": 4, "name": "午餐与午休", "description": "营养午餐制作、午睡看护", "default_score": 20},
        {"step_order": 5, "name": "下午活动", "description": "音乐律动、绘画、益智玩具", "default_score": 15},
        {"step_order": 6, "name": "晚间交接", "description": "晚餐、洗漱、向家长汇报当日情况", "default_score": 15},
    ],
    "养老陪护": [
        {"step_order": 1, "name": "晨间护理", "description": "协助起床、洗漱、测量血压体温", "default_score": 15},
        {"step_order": 2, "name": "用药管理", "description": "按时给药、记录用药情况", "default_score": 20},
        {"step_order": 3, "name": "膳食准备", "description": "根据健康状况制作适宜餐食", "default_score": 15},
        {"step_order": 4, "name": "康复训练", "description": "协助进行适量康复运动", "default_score": 15},
        {"step_order": 5, "name": "陪伴交流", "description": "聊天、读报、陪同看电视", "default_score": 15},
        {"step_order": 6, "name": "安全巡查", "description": "检查居家安全隐患、防跌倒", "default_score": 10},
        {"step_order": 7, "name": "晚间护理", "description": "协助洗漱、就寝准备", "default_score": 10},
    ],
}


def init_default_sop(db: sqlalchemy.orm.Session):
    """初始化默认SOP模板到数据库"""
    from database.models import SopTemplate
    for category, steps in DEFAULT_SOP.items():
        existing = db.query(SopTemplate).filter(SopTemplate.category == category).first()
        if existing:
            continue
        for step in steps:
            sop = SopTemplate(
                category=category,
                name=step["name"],
                step_order=step["step_order"],
                description=step["description"],
                default_score=step["default_score"],
            )
            db.add(sop)
    db.commit()


def ai_acceptance_check(order_id: int, checkins: list, db: sqlalchemy.orm.Session) -> dict:
    """
    AI智能验收打分

    根据打卡数据和SOP标准，综合计算服务得分（0-100分）
    打分规则：
    1. 基础分：每个步骤完成得基础分（按SOP default_score）
    2. 图片核验加分：上传了打卡图片的步骤额外+10%分值
    3. 未完成扣分：未完成步骤不得分
    4. 最终得分 = sum(步骤得分) / sum(步骤满分) * 100
    """
    from database.models import SopTemplate

    # 从订单关联获取服务类别（通过checkin的order关联）
    if checkins:
        order = checkins[0].order
        category = order.service_category
    else:
        return {"total_score": 0, "message": "无打卡记录", "details": []}

    sop_steps = db.query(SopTemplate).filter(
        SopTemplate.category == category,
        SopTemplate.status == 1,
    ).order_by(SopTemplate.step_order).all()

    # 也加载雇主自定义标准
    from database.models import CustomStandard, Order
    order_obj = db.query(Order).filter(Order.id == order_id).first()
    custom_standards = []
    if order_obj:
        custom_standards = db.query(CustomStandard).filter(
            CustomStandard.employer_id == order_obj.employer_id,
            CustomStandard.category == category,
        ).all()

    max_score = sum(s.default_score for s in sop_steps)
    earned_score = 0.0
    details = []

    checkin_map = {c.step_name: c for c in checkins}

    for sop in sop_steps:
        step_detail = {
            "步骤": sop.name,
            "满分": sop.default_score,
            "得分": 0,
            "完成": False,
            "有图片": False,
        }
        checkin = checkin_map.get(sop.name)
        if checkin and checkin.is_done:
            step_score = sop.default_score
            # 图片核验加分：有图片额外+10%
            if checkin.image_url:
                step_score *= 1.1
                step_detail["有图片"] = True
            step_detail["得分"] = round(step_score, 2)
            step_detail["完成"] = True
            earned_score += step_score

            # 存储AI对该步骤的评分
            checkin.ai_score = round(step_score, 2)
        else:
            checkin = db.query(CheckIn).filter(
                CheckIn.order_id == order_id,
                CheckIn.step_name == sop.name,
            ).first()
            if checkin:
                checkin.ai_score = 0

        details.append(step_detail)

    # 计算最终得分（百分制）
    if max_score > 0:
        total_score = (earned_score / max_score) * 100
    else:
        total_score = 0

    # 考虑自定义标准的影响（附加分 ±10分）
    custom_detail = []
    if custom_standards:
        custom_bonus = 0
        for cs in custom_standards:
            # 检查该自定义标准是否在打卡中体现
            related_checkin = checkin_map.get(cs.name)
            if related_checkin and related_checkin.is_done:
                custom_bonus += cs.weight * 2
                custom_detail.append({"标准": cs.name, "已完成": True, "加分": round(cs.weight * 2, 1)})
            else:
                custom_bonus -= cs.weight
                custom_detail.append({"标准": cs.name, "已完成": False, "扣分": round(cs.weight, 1)})
        total_score = max(0, min(100, total_score + custom_bonus))

    db.commit()  # 保存ai_score

    return {
        "total_score": round(total_score, 2),
        "max_score": round(max_score, 2),
        "earned_score": round(earned_score, 2),
        "details": details,
        "custom_standards": custom_detail,
        "grade": _get_grade(total_score),
    }


def _get_grade(score: float) -> str:
    """根据分数返回等级"""
    if score >= 90:
        return "优秀"
    elif score >= 80:
        return "良好"
    elif score >= 60:
        return "合格"
    else:
        return "不合格"


def generate_acceptance_report(acceptance_result: dict) -> str:
    """生成服务验收报告"""
    report = {
        "总得分": acceptance_result["total_score"],
        "等级": acceptance_result["grade"],
        "步骤详情": acceptance_result["details"],
        "自定义标准": acceptance_result.get("custom_standards", []),
    }
    return json.dumps(report, ensure_ascii=False, indent=2)
