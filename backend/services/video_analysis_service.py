"""
视频分析服务
优先调用阿里云百炼 qwen3-vl-plus 分析视频，未配置 API Key 时降级为 mock。
"""
import base64
import json
import os
import random
import re
from datetime import datetime, timezone
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# 提示词
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """你是一名专业的家政服务质量督查员。
你将收到一段家政服务过程的视频，以及该服务的标准操作流程（SOP）步骤列表。
请根据视频内容，评估从业者的服务质量，并严格按照指定 JSON 格式输出结果，不要输出任何其他内容。"""


def _build_user_prompt(sop_steps: list) -> str:
    steps_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(sop_steps)) if sop_steps else "（无预设步骤，请根据视频内容自行判断）"
    return f"""本次服务的 SOP 标准步骤如下：
{steps_text}

请根据视频内容，输出以下 JSON（不要加 markdown 代码块，不要有任何额外说明）：
{{
  "video_score": <综合评分 0-100，浮点数>,
  "action_summary": [<识别到的操作描述，字符串列表>],
  "risk_alerts": [
    {{"timestamp": "<大约时间点，如 00:02:30>", "description": "<风险描述>"}}
  ],
  "sop_coverage_rate": <SOP 步骤覆盖率 0.0-1.0，浮点数>,
  "consistency_with_checkin": <与打卡记录是否一致，true 或 false>
}}

评分标准：
- SOP 覆盖率每缺少一步扣 10 分，基础分 100
- 操作不规范（未戴手套、遗漏区域、工具使用错误）额外扣 5-15 分
- 服务态度良好、工具使用规范可酌情加分（上限 100）"""


# ---------------------------------------------------------------------------
# 外部模型调用（阿里云百炼 qwen3-vl-plus）
# ---------------------------------------------------------------------------

def analyze_video_external(video_path: str, sop_steps: list) -> dict | None:
    """
    调用阿里云百炼 qwen3-vl-plus 分析本地视频文件。
    需要环境变量 DASHSCOPE_API_KEY。未配置时返回 None，系统自动降级为 mock。

    返回结构：
    {
        "video_score": float,
        "action_summary": list[str],
        "risk_alerts": list[dict],   # 每项含 timestamp 和 description
        "sop_coverage_rate": float,
        "consistency_with_checkin": bool,
    }
    """
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        return None

    if not os.path.exists(video_path):
        return None

    try:
        from openai import OpenAI

        # 读取视频文件并 base64 编码
        with open(video_path, "rb") as f:
            video_b64 = base64.b64encode(f.read()).decode("utf-8")

        # 根据文件扩展名确定 MIME 类型
        ext = os.path.splitext(video_path)[1].lower()
        mime = "video/mp4" if ext == ".mp4" else "video/quicktime"
        video_data_url = f"data:{mime};base64,{video_b64}"

        client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )

        completion = client.chat.completions.create(
            model="qwen3-vl-plus",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "video_url",
                            "video_url": {"url": video_data_url},
                        },
                        {"type": "text", "text": _build_user_prompt(sop_steps)},
                    ],
                },
            ],
            extra_body={"enable_thinking": False},
        )

        raw = completion.choices[0].message.content or ""
        return _parse_model_output(raw)

    except Exception:
        return None


def _parse_model_output(raw: str) -> dict | None:
    """从模型输出中提取 JSON，兼容带 markdown 代码块的情况。"""
    # 去掉 ```json ... ``` 包裹
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "").strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # 尝试提取第一个 { ... } 块
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not m:
            return None
        try:
            data = json.loads(m.group())
        except json.JSONDecodeError:
            return None

    # 校验必要字段，缺失则返回 None 触发降级
    required = {"video_score", "action_summary", "risk_alerts",
                "sop_coverage_rate", "consistency_with_checkin"}
    if not required.issubset(data.keys()):
        return None

    # 类型归一化
    data["video_score"] = float(data["video_score"])
    data["sop_coverage_rate"] = float(data["sop_coverage_rate"])
    data["consistency_with_checkin"] = bool(data["consistency_with_checkin"])
    return data


# ---------------------------------------------------------------------------
# 内置 mock 实现
# ---------------------------------------------------------------------------

def _mock_analyze(video_path: str, sop_steps: list) -> dict:
    """基于 SOP 步骤列表生成 mock 分析结果。"""
    import time
    del video_path  # 签名与 analyze_video_external 保持一致，mock 不需要读取文件
    time.sleep(5)  # 模拟 AI 分析耗时
    total = len(sop_steps) if sop_steps else 1
    covered = random.randint(max(1, total - 2), total)
    coverage = round(covered / total, 2)
    video_score = round(coverage * 70 + random.uniform(0, 30), 1)
    video_score = min(100.0, max(0.0, video_score))

    action_summary = sop_steps[:covered] if sop_steps else ["清洁操作"]
    risk_alerts = []
    if coverage < 0.8:
        risk_alerts.append({
            "timestamp": "00:05:30",
            "description": f"检测到 {total - covered} 个 SOP 步骤未执行",
        })

    return {
        "video_score": video_score,
        "action_summary": action_summary,
        "risk_alerts": risk_alerts,
        "sop_coverage_rate": coverage,
        "consistency_with_checkin": coverage >= 0.8,
    }


# ---------------------------------------------------------------------------
# 主分析入口
# ---------------------------------------------------------------------------

def analyze_video(video_path: str, order_id: int, db: Session) -> dict:
    """
    分析服务视频，优先调用外部模型，失败时降级为 mock。
    返回结构化分析结果 dict，可直接序列化为 JSON 存入 ServiceVideo.analysis_result。
    """
    from database.models import CheckIn, SopTemplate, Order

    order = db.query(Order).filter(Order.id == order_id).first()
    sop_steps = []
    if order:
        checkins = db.query(CheckIn).filter(
            CheckIn.order_id == order_id
        ).order_by(CheckIn.step_order).all()
        if checkins:
            sop_steps = [c.step_name for c in checkins]
        else:
            templates = db.query(SopTemplate).filter(
                SopTemplate.category == order.service_category,
                SopTemplate.status == 1,
            ).order_by(SopTemplate.step_order).all()
            sop_steps = [t.name for t in templates]

    result = analyze_video_external(video_path, sop_steps)
    if result is None:
        result = _mock_analyze(video_path, sop_steps)

    result["analyzed_at"] = datetime.now(timezone.utc).isoformat()
    return result


# ---------------------------------------------------------------------------
# 恶意差评检测
# ---------------------------------------------------------------------------

def detect_malicious_review(video_score: float, review_ratings: list) -> bool:
    """
    判断是否存在恶意差评。
    条件：视频综合评分 >= 80 且存在评价评分 < 3 的记录。
    """
    if video_score is None or video_score < 80:
        return False
    return any(r < 3 for r in review_ratings)
