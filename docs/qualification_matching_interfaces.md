# 资质画像给匹配推荐模块的接口

本文档说明匹配/推荐模块如何消费资质可信标签。本仓库后端是 FastAPI 单体，推荐模块应优先用同进程 DB/service 调用，不要让服务端 HTTP 调自己。HTTP 接口保留给 Swagger、外部客户端和调试。

## 1. 后端内部调用方式

推荐模块已有 `db: Session` 时，直接调用资质服务：

```python
from services.certification_service import check_eligibility, get_provider_matching_facts

facts = get_provider_matching_facts(db, provider_id=worker.id, service_type="elderly_care")

eligibility = check_eligibility(
    db,
    provider_id=worker.id,
    service_type="elderly_care",
    required_tags=["identity_verified", "health_verified"],
)
```

`get_provider_matching_facts()` 返回：

```json
{
  "provider_id": 888,
  "active_tags": ["identity_verified", "health_verified", "elderly_care"],
  "warning_tags": ["health_certificate_expiring"],
  "qualification_summary": {
    "identity_verified": true,
    "health_verified": true,
    "background_check_status": "authorized",
    "qualification_completeness": "high"
  },
  "risk_warnings": [],
  "eligibility": {
    "eligible": true,
    "reasons": [],
    "missing_tags": []
  }
}
```

也可以直接查表：

- `ProviderQualificationTag`：服务人员标签，按 `provider_id`、`status='active'` 过滤有效标签。
- `QualificationTagDefinition`：标签名称、分类、展示优先级。
- `Certification`：资质材料状态和有效期，不建议推荐理由直接使用敏感字段。

## 2. 距离与就近推荐

距离不属于资质模块，推荐模块应继续使用现有用户画像字段：

- 雇主位置：`User.lat`、`User.lng`
- 服务人员位置：`User.lat`、`User.lng`
- 距离函数：`services.matching_service.haversine(lat1, lng1, lat2, lng2)`

示例：

```python
from services.matching_service import haversine

distance_km = haversine(employer.lat, employer.lng, worker.lat, worker.lng)
```

就近推荐建议在匹配模块中完成：先用资质准入过滤高敏服务，再按距离、技能、时间、信用分等维度排序。资质画像接口不返回详细地址，避免隐私泄露。

## 3. HTTP 调试接口

外部客户端或 Swagger 调试可使用：

```http
GET /api/providers/{provider_id}/qualification-profile
POST /api/qualifications/eligibility-check
```

准入检查请求：

```json
{
  "provider_id": 888,
  "service_type": "elderly_care",
  "required_tags": ["identity_verified", "health_verified"]
}
```

返回：

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": {
    "eligible": true,
    "reasons": [],
    "missing_tags": [],
    "risk_warnings": [],
    "qualification_summary": {
      "identity_verified": true,
      "health_verified": true,
      "background_check_status": "authorized",
      "qualification_completeness": "high"
    }
  }
}
```

高敏服务类型包括：母婴护理、育婴照护、老人照护、住家保姆、病患陪护、夜间陪护、独居老人上门服务。高敏服务默认要求 `identity_verified` 与 `health_verified`，健康证明过期时返回 `eligible=false`。

## 4. 隐私边界

匹配推荐模块可以使用可展示标签、资质摘要、准入结果、风险提示、经纬度距离计算结果。不要依赖或展示以下信息：

- 完整身份证号
- 完整证件图片路径
- 完整体检报告或具体疾病信息
- 完整无犯罪记录证明
- 家庭住址、紧急联系人等敏感信息

推荐理由可使用 `tag_name` 与 `qualification_summary` 生成，例如：“该服务人员身份和健康证明已核验，具备老人照护相关资质，距离较近。”
