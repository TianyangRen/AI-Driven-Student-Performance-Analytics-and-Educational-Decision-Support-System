# 模型集成方案（给团队的速查文档）

> 仓库内分工：
> - `backend/`（main 分支）—— Tianyang Ren：模型训练与推理（OULAD 风险分类 + 早期成绩回归）
> - `web-platform/`（本分支 `feat/web-platform`）—— Honghao Zhang：账户、课程、教学班、导入、分析、报告、前端原型
>
> 两套代码现在【独立运行、互不依赖】；本分支已预留了集成槽位，等模型稳定时一次性接入。

## 一、当前两边接口

| 模块 | `backend/`（组员） | `web-platform/backend/` |
|---|---|---|
| 端口 | 8000 | 8000（同端口不能同时跑） |
| 业务 | 风险预测 demo | 完整业务系统（含前端） |
| 认证 | 无 | DRF Token |
| API | `/api/predict/`, `/api/predict-grade/`, `/api/health/` | `/api/v1/*` 共 20+ 接口 |
| 模型 | ✅ 真实模型（`backend/analytics/ml/`） | ❌ 占位 mock（`web-platform/backend/ml/` 为空） |
| 前端 | 无 | ✅ React + antd 共 11 个页面 |

## 二、最终演示形态

只跑 `web-platform/`。`backend/analytics/ml/` 作为 ML 库被拷贝进 `web-platform/backend/ml/`，由 `apps/predictions/services.py` 适配层调用。

```
final/
├── backend/      ← 组员保留：训练脚本、CSV、模型文件依然在这里维护
│   └── analytics/ml/      ← 模型代码的"上游来源"
├── real_data/    ← 组员保留：训练用 CSV
└── web-platform/
    ├── backend/
    │   ├── ml/            ← ★ 从 backend/analytics/ml/ 同步过来
    │   ├── ml_models/     ← ★ 从 backend/ml_models/ 同步 .pkl
    │   └── apps/predictions/services.py  ← 适配层（已写好）
    └── frontend/
```

## 三、集成步骤（一行命令同步即可）

集成那天在仓库根目录执行：

```bash
# 1) 同步 ml 代码
rm -rf web-platform/backend/ml
cp -R   backend/analytics/ml   web-platform/backend/ml

# 2) 同步训练产物
mkdir -p web-platform/backend/ml_models
cp backend/ml_models/*.pkl  web-platform/backend/ml_models/

# 3) 重启 Django
cd web-platform/backend && python manage.py runserver

# 4) 验证
curl http://127.0.0.1:8000/api/v1/health   # 看 "ml": {"mode": "real", ...}
```

之后业务代码不需要再改 —— 所有走 `predict_risk()` 的接口立刻使用真实模型。

## 四、字段对齐速查

| 字段 | 组员定义 | web-platform 定义 | 处理方式 |
|---|---|---|---|
| 学生标识 | `Student.student_id` (CharField) | `Student.student_no` (CharField) | 同型同义，适配层直接传递 |
| 考核类型 | QUIZ / LAB / ASSIGNMENT / MIDTERM / PARTICIPATION | 同前 + FINAL | services 聚合时 FINAL 也按 weight 计入 |
| 风险等级 | low / medium / high（小写） | LOW / MEDIUM / HIGH（大写） | 适配层做大小写转换 |
| 特征字典 | OULAD 6 列：total_clicks / active_days / ... | 由 `build_features_for_student()` 生成 | 当前是占位常量，等指标管线接通后填真实聚合 |

## 五、ml 输出契约（必须保持稳定）

组员 `MLService.predict(features) -> dict` 的返回结构是契约，**改动需双方约定**：

```python
{
  "risk_score":   float,        # ∈ [0, 1]
  "risk_level":   "low"|"medium"|"high",
  "model_version": str,
  "explanation":  {feature_name: contribution_float, ...},
}
```

`GradeService.predict(features) -> dict`：

```python
{
  "predicted_final_grade": float,  # 0-100
  "risk_level":            "low"|"medium"|"high",
  "model_version":         str,
  "explanation":           {feature: contribution, ...},
  "thresholds":            {"high": "<60", "medium": "60-70", "low": ">=70"},
}
```

只要组员保持以上输出结构，`web-platform/backend/apps/predictions/services.py` 不需要修改。

## 六、协作约定

1. 任何对 `ml/features.py` 中 `FEATURE_COLUMNS` 的增删改，必须在 PR 描述里说明，并同步更新 `web-platform/backend/apps/predictions/services.py:build_features_for_student()`。
2. 训练脚本产出的 `.pkl` 不入库（`.gitignore`），通过 release / 共享盘交付。
3. 集成 PR 应包含一次 `curl /api/v1/health` 截图证明 `ml.mode == "real"`。
