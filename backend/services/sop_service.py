"""
AI服务标准（SOP）与智能验收服务
"""
import base64
import json
import mimetypes
import os
import re
import socket
import urllib.error
import urllib.request
import sqlalchemy.orm
from database.models import CheckIn


def _load_env_file():
    """Load backend/.env into os.environ without requiring extra dependencies."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as env_file:
            for raw_line in env_file:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError:
        return


_load_env_file()


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

    根据打卡数据、图片AI核验和SOP标准，综合计算服务得分率（0-1）
    打分规则：
    1. 平台SOP总分为各步骤 default_score 之和
    2. 已完成但未上传图片的步骤得该步骤25%分值
    3. 已完成且上传图片的步骤得25%基础分 + AI图片核验分（0~75%分值）
    4. 未完成步骤不得分
    5. 自定义标准按 weight 计入总分，并按同样规则参与AI核验
    6. 最终得分率 = 实际得分 / 总分
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

    sop_max_score = sum(s.default_score for s in sop_steps)
    custom_max_score = sum(c.weight for c in custom_standards)
    max_score = sop_max_score + custom_max_score
    earned_score = 0.0
    details = []

    checkin_map = {c.step_name: c for c in checkins}

    for sop in sop_steps:
        step_detail = {
            "步骤": sop.name,
            "说明": sop.description,
            "满分": sop.default_score,
            "得分": 0,
            "完成": False,
            "有图片": False,
            "图片": None,
            "AI得分": 0,
            "AI说明": "未完成",
        }
        checkin = checkin_map.get(sop.name)
        if checkin and checkin.is_done:
            # 完成即获得25%基础分；图片由AI核验，最多补足75%。
            base_score = sop.default_score * 0.25
            ai_score = 0.0
            if checkin.image_url:
                step_detail["有图片"] = True
                step_detail["图片"] = _to_public_upload_url(checkin.image_url)
                ai_result = evaluate_checkin_with_ai(checkin, sop.name, sop.description, sop.default_score)
                ai_score = ai_result["score"]
                step_detail["AI得分"] = round(ai_score, 2)
                step_detail["AI说明"] = ai_result["reason"]
                if "confidence" in ai_result:
                    step_detail["AI置信度"] = ai_result["confidence"]
            else:
                step_detail["AI说明"] = "未上传图片，仅获得完成打卡基础分"
            step_score = base_score + ai_score
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

    # 自定义标准作为额外验收项计入总分：完成得weight，未完成不得分，不扣分
    custom_detail = []
    if custom_standards:
        for index, cs in enumerate(custom_standards, start=1):
            related_checkin = checkin_map.get(cs.name)
            if related_checkin and related_checkin.is_done:
                base_score = cs.weight * 0.25
                ai_score = 0.0
                ai_reason = "未上传图片，仅获得完成打卡基础分"
                has_image = bool(related_checkin.image_url)
                if has_image:
                    ai_result = evaluate_checkin_with_ai(
                        related_checkin,
                        cs.name,
                        cs.description or _build_fallback_custom_description(category, cs.name),
                        cs.weight,
                    )
                    ai_score = ai_result["score"]
                    ai_reason = ai_result["reason"]
                custom_score = base_score + ai_score
                earned_score += custom_score
                custom_detail.append({
                    "step_order": len(sop_steps) + index,
                    "标准": cs.name,
                    "说明": cs.description,
                    "满分": round(cs.weight, 2),
                    "得分": round(custom_score, 2),
                    "已完成": True,
                    "有图片": has_image,
                    "图片": _to_public_upload_url(related_checkin.image_url) if has_image else None,
                    "AI得分": round(ai_score, 2),
                    "AI说明": ai_reason,
                    "description": cs.description,
                })
            else:
                custom_detail.append({
                    "step_order": len(sop_steps) + index,
                    "标准": cs.name,
                    "说明": cs.description,
                    "满分": round(cs.weight, 2),
                    "得分": 0,
                    "已完成": False,
                    "有图片": False,
                    "图片": None,
                    "AI得分": 0,
                    "AI说明": "未完成该自定义要求",
                    "description": cs.description,
                })

    # 计算最终得分率（0-1）
    if max_score > 0:
        total_score = earned_score / max_score
    else:
        total_score = 0

    db.commit()  # 保存ai_score

    return {
        "total_score": round(total_score, 4),
        "max_score": round(max_score, 2),
        "earned_score": round(earned_score, 2),
        "details": details,
        "custom_standards": custom_detail,
        "grade": _get_grade(total_score),
    }


def evaluate_checkin_with_ai(checkin: CheckIn, step_name: str, description: str, max_score: float) -> dict:
    """
    根据打卡图片、步骤名称和步骤说明进行AI核验。

    返回的 score 永远限制在 [0, max_score * 0.75]，只作为图片核验分；
    完成打卡的25%基础分在 ai_acceptance_check 中另行计算。
    """
    cap = max(0.0, float(max_score or 0) * 0.75)
    if not checkin.image_url:
        return {"score": 0.0, "reason": "未上传图片，无法进行AI影像核验", "confidence": 0.0}

    image_payload = _load_image_as_data_url(checkin.image_url)
    if not image_payload:
        return {
            "score": 0.0,
            "reason": "图片文件不可读取，AI影像核验未通过",
            "confidence": 0.0,
        }

    prompt = (
        "你是家政服务验收AI。请结合SOP步骤名称、步骤说明、从业者备注和打卡图片，"
        "判断该步骤的服务完成度、规范度、完整度。只返回JSON，不要返回解释。"
        "JSON字段必须是：score_rate、reason、confidence。"
        "score_rate必须是0到1之间的小数，表示图片核验分占该步骤图片核验上限的比例；"
        "reason用中文简短说明扣分或通过原因；confidence为0到1之间的小数。"
    )
    text = {
        "step_name": step_name,
        "description": description or "",
        "remark": checkin.remark or "",
        "max_image_score": cap,
    }
    ai_result = _call_qwen_json([
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": json.dumps(text, ensure_ascii=False)},
                {"type": "image_url", "image_url": {"url": image_payload}},
            ],
        },
    ])
    if not ai_result:
        return _fallback_image_score(checkin, cap)

    score_rate = _clamp_float(ai_result.get("score_rate"), 0.0, 1.0, 0.6)
    confidence = _clamp_float(ai_result.get("confidence"), 0.0, 1.0, 0.5)
    reason = str(ai_result.get("reason") or "AI已根据图片完成核验").strip()
    return {
        "score": round(cap * score_rate, 2),
        "reason": reason[:160],
        "confidence": round(confidence, 2),
    }


def _get_grade(score: float) -> str:
    """根据得分率换算成百分制后返回等级"""
    percent = score * 100
    if percent >= 90:
        return "优秀"
    elif percent >= 80:
        return "良好"
    elif percent >= 60:
        return "合格"
    else:
        return "不合格"


def _call_qwen_json(messages: list, max_tokens: int = 500) -> dict:
    """调用千问/DashScope OpenAI兼容接口，失败时返回空字典。"""
    api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")
    if not api_key:
        return {}

    base_url = os.getenv("QWEN_BASE_URL", "https://api.siliconflow.cn/v1").rstrip("/")
    model = os.getenv("QWEN_MODEL", "Qwen/Qwen3.6-35B-A3B")
    url = _join_qwen_endpoint(base_url, "chat/completions")
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": max_tokens,
    }

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        timeout = _clamp_float(os.getenv("QWEN_TIMEOUT"), 1.0, 60.0, 8.0)
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
        content = result["choices"][0]["message"]["content"]
        return _parse_json_object(content)
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        socket.timeout,
        TimeoutError,
        OSError,
        KeyError,
        IndexError,
        json.JSONDecodeError,
    ):
        return {}


def _join_qwen_endpoint(base_url: str, endpoint: str) -> str:
    """Join DashScope compatible-mode base URL with an endpoint."""
    clean = base_url.rstrip("/")
    if clean.endswith("/v1") or clean.endswith("/compatible-mode/v1"):
        return f"{clean}/{endpoint}"
    return f"{clean}/v1/{endpoint}"


def _parse_json_object(content: str) -> dict:
    """尽量从AI返回文本中提取JSON对象。"""
    if not content:
        return {}
    try:
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.S)
        if not match:
            return {}
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}


def _load_image_as_data_url(image_url: str) -> str:
    """读取本地打卡图片并转换为可传给多模态模型的data URL。"""
    candidates = [image_url]
    if not os.path.isabs(image_url):
        candidates.append(os.path.join(os.getcwd(), image_url))
        candidates.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), image_url))

    image_path = None
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            image_path = candidate
            break
    if not image_path:
        return ""

    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type or not mime_type.startswith("image/"):
        mime_type = "image/jpeg"
    try:
        with open(image_path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"
    except OSError:
        return ""


def _fallback_image_score(checkin: CheckIn, cap: float) -> dict:
    """AI不可用时的降级评分，保证验收流程可运行。"""
    if not checkin.image_url:
        return {"score": 0.0, "reason": "未上传图片", "confidence": 0.0}
    return {
        "score": round(cap * 0.6, 2),
        "reason": "AI暂不可用，系统按已上传图片进行保守核验",
        "confidence": 0.4,
    }


def _clamp_float(value, min_value: float, max_value: float, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(min_value, min(max_value, number))


def _build_fallback_custom_description(category: str, name: str) -> str:
    label = name or "个性化服务要求"
    return f"按雇主要求完成{category}服务中的“{label}”，完成后拍照留存，确保结果可核验。"


def _to_public_upload_url(image_url: str) -> str:
    """Convert stored upload path to the URL path exposed by FastAPI."""
    if not image_url:
        return None
    normalized = image_url.replace("\\", "/")
    if normalized.startswith("/uploads/"):
        return normalized
    if normalized.startswith("uploads/"):
        return f"/{normalized}"
    marker = "/uploads/"
    if marker in normalized:
        return normalized[normalized.index(marker):]
    return normalized


def generate_acceptance_report(acceptance_result: dict) -> str:
    """生成服务验收报告，优先调用大模型，失败时使用本地规则报告。"""
    base_report = {
        "得分率": acceptance_result["total_score"],
        "实际得分": acceptance_result["earned_score"],
        "总分": acceptance_result["max_score"],
        "等级": acceptance_result["grade"],
        "步骤详情": acceptance_result["details"],
        "自定义标准": acceptance_result.get("custom_standards", []),
    }
    evidence_images = _collect_report_images(acceptance_result)
    ai_report = _generate_ai_service_report(base_report, evidence_images)
    if not ai_report:
        ai_report = _build_fallback_service_report(base_report, evidence_images)

    report = {
        **base_report,
        "服务报告": ai_report,
        "证据图片": evidence_images,
    }
    acceptance_result["service_report"] = report
    return json.dumps(report, ensure_ascii=False, indent=2)


def _collect_report_images(acceptance_result: dict) -> list:
    """Collect image evidence from SOP details and custom standards."""
    images = []
    for item in acceptance_result.get("details", []):
        if item.get("图片"):
            images.append({
                "type": "sop",
                "name": item.get("步骤"),
                "url": item.get("图片"),
                "score": item.get("得分"),
                "ai_reason": item.get("AI说明"),
            })
    for item in acceptance_result.get("custom_standards", []):
        if item.get("图片"):
            images.append({
                "type": "custom",
                "name": item.get("标准"),
                "url": item.get("图片"),
                "score": item.get("得分"),
                "ai_reason": item.get("AI说明"),
            })
    return images


def _generate_ai_service_report(base_report: dict, evidence_images: list) -> dict:
    """Use the LLM to produce an objective service report for both parties."""
    prompt = (
        "你是家政服务平台的客观验收报告生成助手。请基于SOP逐项核验结果、AI图片核验说明、"
        "得分和证据图片列表，生成一份给雇主和从业者共同查看的客观服务报告。"
        "报告应避免偏向任一方，说明服务完成度、规范度、完整度、亮点、待改进项和证据依据。"
        "只返回JSON，不要返回解释。JSON字段必须包含：title、summary、completion、standardization、integrity、"
        "evidence_summary、strengths、improvements、conclusion、for_employer、for_worker。"
        "strengths和improvements必须是字符串数组；其他字段为中文字符串。"
    )
    payload = {
        "score_rate": base_report["得分率"],
        "earned_score": base_report["实际得分"],
        "max_score": base_report["总分"],
        "grade": base_report["等级"],
        "sop_details": base_report["步骤详情"],
        "custom_standards": base_report["自定义标准"],
        "evidence_images": evidence_images,
    }
    ai_result = _call_qwen_json([
        {"role": "system", "content": prompt},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ], max_tokens=1200)
    if not ai_result:
        return {}

    return {
        "title": str(ai_result.get("title") or "家政服务客观验收报告"),
        "summary": str(ai_result.get("summary") or ""),
        "completion": str(ai_result.get("completion") or ""),
        "standardization": str(ai_result.get("standardization") or ""),
        "integrity": str(ai_result.get("integrity") or ""),
        "evidence_summary": str(ai_result.get("evidence_summary") or ""),
        "strengths": _ensure_string_list(ai_result.get("strengths")),
        "improvements": _ensure_string_list(ai_result.get("improvements")),
        "conclusion": str(ai_result.get("conclusion") or ""),
        "for_employer": str(ai_result.get("for_employer") or ""),
        "for_worker": str(ai_result.get("for_worker") or ""),
        "generated_by": "ai",
    }


def _build_fallback_service_report(base_report: dict, evidence_images: list) -> dict:
    """Build a deterministic report when the LLM is unavailable."""
    details = base_report.get("步骤详情", [])
    custom = base_report.get("自定义标准", [])
    all_items = details + custom
    total_items = len(all_items)
    done_items = sum(1 for item in all_items if item.get("完成") or item.get("已完成"))
    image_items = len(evidence_images)
    weak_items = [
        item.get("步骤") or item.get("标准")
        for item in all_items
        if (item.get("完成") or item.get("已完成")) and not item.get("有图片")
    ]
    failed_items = [
        item.get("步骤") or item.get("标准")
        for item in all_items
        if not (item.get("完成") or item.get("已完成"))
    ]
    percent = round(float(base_report["得分率"]) * 100, 1)

    improvements = []
    if weak_items:
        improvements.append(f"以下项目已打卡但缺少图片证据：{'、'.join(weak_items[:5])}")
    if failed_items:
        improvements.append(f"以下项目未完成或未形成有效打卡：{'、'.join(failed_items[:5])}")
    if not improvements:
        improvements.append("本次服务证据链较完整，可继续保持按步骤打卡和拍照留存。")

    return {
        "title": "家政服务客观验收报告",
        "summary": f"本次服务综合得分率为{percent}%，等级为{base_report['等级']}。共核验{total_items}项，完成{done_items}项，留存图片证据{image_items}项。",
        "completion": f"服务完成度：{done_items}/{total_items}项完成，实际得分{base_report['实际得分']}/{base_report['总分']}。",
        "standardization": "规范度：系统依据SOP步骤、打卡记录、图片证据和AI逐项说明进行核验，减少单方主观判断。",
        "integrity": f"完整度：当前留存{image_items}项图片证据，未完成或缺少证据的项目已在改进项中列出。",
        "evidence_summary": "证据包括逐项打卡记录、上传图片路径、AI图片核验说明和步骤得分。",
        "strengths": [
            "验收结果按统一SOP计算，评分依据可追溯。",
            "图片证据与AI说明共同支撑服务质量判断。",
        ],
        "improvements": improvements,
        "conclusion": "该报告用于帮助雇主和从业者共同确认服务结果，既约束敷衍服务，也减少无依据挑刺。",
        "for_employer": "建议优先查看低分项、未完成项和图片证据，再进行确认或沟通。",
        "for_worker": "建议后续按步骤完成服务，并为关键步骤补充清晰图片，提升验收通过率。",
        "generated_by": "fallback",
    }


def _ensure_string_list(value) -> list:
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    if value:
        return [str(value)]
    return []
