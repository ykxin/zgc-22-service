"""
AI OCR证件识别服务（模拟实现）
实际场景可对接百度OCR、腾讯OCR等API
"""
import re
import random
import hashlib
from typing import Tuple
from datetime import datetime, date


# --- 模拟证件数据库（用于证件真伪校验） ---
MOCK_VALID_CERTS = {
    "health_cert": {"no": "JK2024", "org": "市卫生健康委员会"},
    "qualification": {"no": "ZG2024", "org": "市人力资源和社会保障局"},
}


def ocr_recognize_id_card(image_data: bytes) -> dict:
    """
    模拟身份证OCR识别
    真实场景：调用OCR API，识别姓名、身份证号、有效期等
    """
    # 模拟从图片中识别的结果
    mock_names = ["张明", "李华", "王芳", "刘洋", "陈静", "赵伟", "孙丽", "周强"]
    mock_cards = [
        "320102199003071234", "440106198506152345",
        "110108199210081456", "330106199507093678",
    ]
    name = random.choice(mock_names)
    id_card = random.choice(mock_cards)
    gender = "男" if int(id_card[-2]) % 2 else "女"
    birth = f"{id_card[6:10]}-{id_card[10:12]}-{id_card[12:14]}"
    # 有效期：签发日(随机过去几年) + 10年
    issue_year = random.randint(2018, 2023)
    expire_date = f"{issue_year + 10}-{id_card[10:12]}-{id_card[12:14]}"

    return {
        "cert_type": "id_card",
        "real_name": name,
        "cert_number": id_card,
        "gender": gender,
        "birth_date": birth,
        "expire_date": expire_date,
        "confidence": round(random.uniform(0.88, 0.99), 2),
    }


def ocr_recognize_health_cert(image_data: bytes) -> dict:
    """模拟健康证OCR识别"""
    mock_names = ["张明", "李华", "王芳", "刘洋"]
    cert_no = f"JK{random.randint(2020, 2025)}{random.randint(100, 999):03d}"
    expire_date = f"{random.randint(2025, 2027)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
    return {
        "cert_type": "health_cert",
        "real_name": random.choice(mock_names),
        "cert_number": cert_no,
        "expire_date": expire_date,
        "issuing_authority": "市卫生健康委员会",
        "confidence": round(random.uniform(0.85, 0.98), 2),
    }


def ocr_recognize_qualification(image_data: bytes) -> dict:
    """模拟资格证OCR识别"""
    mock_names = ["张明", "李华", "王芳"]
    cert_no = f"ZG{random.randint(2020, 2025)}{random.randint(1000, 9999):04d}"
    mock_skills = ["高级家政师", "母婴护理师", "养老护理员", "保洁工程师"]
    expire_date = f"{random.randint(2026, 2028)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
    return {
        "cert_type": "qualification",
        "real_name": random.choice(mock_names),
        "cert_number": cert_no,
        "qualification_name": random.choice(mock_skills),
        "expire_date": expire_date,
        "issuing_authority": "市人力资源和社会保障局",
        "confidence": round(random.uniform(0.85, 0.98), 2),
    }


def recognize_certificate(cert_type: str, image_data: bytes) -> dict:
    """
    统一证件识别入口
    根据证件类型调用对应的OCR识别
    """
    if cert_type == "id_card":
        return ocr_recognize_id_card(image_data)
    elif cert_type == "health_cert":
        return ocr_recognize_health_cert(image_data)
    elif cert_type == "qualification":
        return ocr_recognize_qualification(image_data)
    else:
        return {"error": "不支持的证件类型"}


def verify_certificate_validity(ocr_result: dict) -> Tuple[bool, str]:
    """
    AI证件真伪校验逻辑
    返回 (是否有效, 校验说明)
    """
    # 1. OCR置信度检查
    if ocr_result.get("confidence", 0) < 0.80:
        return False, "证件识别置信度过低，请重新上传清晰图片"

    # 2. 有效期检查
    expire_date = ocr_result.get("expire_date", "")
    if expire_date:
        try:
            exp = datetime.strptime(expire_date, "%Y-%m-%d").date()
            if exp < date.today():
                return False, f"证件已过期（有效期至{expire_date}）"
        except ValueError:
            return False, "证件日期格式异常"

    # 3. 证件号格式校验
    cert_type = ocr_result.get("cert_type", "")
    cert_number = ocr_result.get("cert_number", "")
    if cert_type == "id_card":
        if not re.match(r'^\d{17}[\dXx]$', cert_number):
            return False, "身份证号格式不正确"

    return True, "证件校验通过"
