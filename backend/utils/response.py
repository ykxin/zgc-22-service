"""统一响应格式"""
from typing import Any

def success(data: Any = None, msg: str = "操作成功") -> dict:
    return {"code": 200, "msg": msg, "data": data}

def error(msg: str = "操作失败", code: int = 400) -> dict:
    return {"code": code, "msg": msg, "data": None}

def paginate(items: list, total: int, page: int, page_size: int) -> dict:
    return {
        "code": 200,
        "msg": "查询成功",
        "data": {
            "list": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    }
