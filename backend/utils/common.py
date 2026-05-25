"""通用工具函数"""
import re
from datetime import datetime, date

def validate_phone(phone: str) -> bool:
    """手机号格式校验"""
    return bool(re.match(r'^1[3-9]\d{9}$', phone))

def validate_id_card(id_card: str) -> bool:
    """身份证号格式校验（18位）"""
    if not re.match(r'^\d{17}[\dXx]$', id_card):
        return False
    # 加权因子
    weight = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    check_map = '10X98765432'
    total = sum(int(id_card[i]) * weight[i] for i in range(17))
    return check_map[total % 11] == id_card[17].upper()

def is_expired(expire_date: str) -> bool:
    """判断证件是否过期"""
    try:
        d = datetime.strptime(expire_date, "%Y-%m-%d").date()
        return d < date.today()
    except ValueError:
        return True

def calculate_age(id_card: str) -> int:
    """从身份证号计算年龄"""
    birth = datetime.strptime(id_card[6:14], "%Y%m%d")
    today = date.today()
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
