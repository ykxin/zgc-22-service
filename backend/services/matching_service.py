"""
AI双向智能匹配算法
综合多维度画像计算匹配度，生成Top-N推荐
"""
import math
from sqlalchemy.orm import Session
from database.models import User


def calculate_match_score(employer: User, worker: User) -> dict:
    """
    计算雇主与从业者的匹配分数（0-100分）

    匹配维度：
    1. 信用分匹配 (25分)：从业者信用分 / 100 * 25
    2. 技能匹配度 (30分)：雇主需求 vs 从业者技能的Jaccard相似度
    3. 距离适配度 (15分)：距离越近分越高
    4. 时间适配度 (15分)：服务时间是否匹配雇主作息
    5. 场景适配度 (15分)：特殊需求匹配（老人/小孩/宠物）
    """
    total_score = 0.0
    details = {}

    # 1. 信用分匹配 (25分)
    credit = worker.credit_score or 80
    credit_score = credit / 100 * 25
    total_score += credit_score
    details["信用分"] = round(credit_score, 1)

    # 2. 技能匹配度 (30分) - Jaccard相似度
    employer_needs = set()
    if employer.service_category:
        employer_needs.add(employer.service_category)
    if employer.family_members:
        # 从家庭成员描述中提取可能的需求关键词
        kw_map = {"老人": "养老", "小孩": "育儿", "宠物": "保洁"}
        for k, v in kw_map.items():
            if k in employer.family_members:
                employer_needs.add(v)

    worker_skills = set()
    if worker.skills:
        worker_skills = {s.strip() for s in worker.skills.split(",") if s.strip()}
    if worker.good_at:
        worker_skills.update({s.strip() for s in worker.good_at.split(",") if s.strip()})

    if employer_needs and worker_skills:
        intersection = employer_needs & worker_skills
        union = employer_needs | worker_skills
        jaccard = len(intersection) / len(union) if union else 0
    else:
        jaccard = 0.5  # 信息不足时给基础分
    skill_score = jaccard * 30
    total_score += skill_score
    details["技能匹配"] = round(skill_score, 1)

    # 3. 距离适配度 (15分) - 简化的距离计算
    if employer.lat and worker.lat and employer.lng and worker.lng:
        dist = haversine(employer.lat, employer.lng, worker.lat, worker.lng)
        # 距离小于3km满分，超过20km基本0分
        if dist < 3:
            distance_score = 15
        elif dist < 20:
            distance_score = 15 * (1 - (dist - 3) / 17)
        else:
            distance_score = max(0, 15 - dist * 0.5)
    else:
        distance_score = 10  # 无位置信息给基础分
    total_score += distance_score
    details["距离适配"] = round(distance_score, 1)

    # 4. 时间适配度 (15分)
    if employer.schedule and worker.work_time:
        # 简单时段匹配：上午/下午/全天
        emp_times = set(employer.schedule.replace(" ", "").split(","))
        wkr_times = set(worker.work_time.replace(" ", "").split(","))
        overlap = len(emp_times & wkr_times)
        if overlap > 0:
            time_score = min(15, overlap * 7.5)
        else:
            time_score = 5
    else:
        time_score = 7.5  # 信息不足给一半
    total_score += time_score
    details["时间适配"] = round(time_score, 1)

    # 5. 场景适配度 (15分) - 特殊需求
    scene_score = 0.0
    special_needs = 0
    matched_needs = 0

    if employer.has_elderly:
        special_needs += 1
        if worker.good_at and "养老" in worker.good_at:
            matched_needs += 1

    if employer.has_children:
        special_needs += 1
        if worker.good_at and "育儿" in worker.good_at:
            matched_needs += 1

    if employer.has_pet:
        special_needs += 1
        if worker.good_at and "宠物" in worker.good_at:
            matched_needs += 1

    if special_needs > 0:
        scene_score = (matched_needs / special_needs) * 15
    else:
        scene_score = 10  # 无特殊需求给基础分
    total_score += scene_score
    details["场景适配"] = round(scene_score, 1)

    return {
        "total_score": round(total_score, 2),
        "details": details,
    }


def get_top_n_matches(db: Session, employer: User, n: int = 5) -> list:
    """
    为指定雇主推荐Top-N从业者
    返回排序后的推荐列表
    """
    # 查询所有正常状态的从业者
    workers = db.query(User).filter(
        User.role == "worker",
        User.status == 1,
        User.credit_score >= 60  # 信用分门槛
    ).all()

    results = []
    for worker in workers:
        match_result = calculate_match_score(employer, worker)
        results.append({
            "worker_id": worker.id,
            "nickname": worker.nickname,
            "skills": worker.skills,
            "experience_years": worker.experience_years,
            "credit_score": worker.credit_score,
            "risk_level": worker.risk_level,
            "address": worker.address,
            "avatar": worker.avatar,
            "match_score": match_result["total_score"],
            "match_details": match_result["details"],
        })

    # 按匹配分降序排序，取TopN
    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results[:n]


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """计算两点间的距离（km）"""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng / 2) ** 2)
    c = 2 * math.asin(math.sqrt(a))
    return R * c
