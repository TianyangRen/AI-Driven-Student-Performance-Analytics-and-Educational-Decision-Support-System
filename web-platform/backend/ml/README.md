# `backend/ml/` —— 模型集成槽位

本目录是【web-platform】系统与【组员模型仓库】之间约定的唯一集成点。
当前为空（仅有占位 `__init__.py`），等组员模型稳定后按下面步骤接入。

## 集成步骤（一次性操作）

```bash
# 在仓库根目录执行
cp -R backend/analytics/ml/*  web-platform/backend/ml/
# 模型 .pkl 也一起放进来
mkdir -p web-platform/backend/ml_models
cp backend/ml_models/risk_model.pkl   web-platform/backend/ml_models/
cp backend/ml_models/grade_model.pkl  web-platform/backend/ml_models/
```

完成后重启 Django，`apps/predictions/services.py` 会在启动时 import 成功，
所有走 `predict_risk()` 的接口立刻使用真实模型，不需要改任何业务代码。

## 模块预期结构（与组员仓库一致）

```
backend/ml/
├── __init__.py
├── features.py        # FEATURE_COLUMNS / risk_level / to_feature_row
├── service.py         # MLService (RandomForest on OULAD 风险二分类)
├── grade_service.py   # GradeService (Ridge 早期成绩 → 期末总分)
├── train.py
├── train_real.py
├── oulad.py
├── real_data.py
└── ...
```

## 字段对齐

- 组员 `Student.student_id` (CharField) ↔ 本系统 `student.student_no` (CharField) —— 同型可直接传递
- 组员 `Assessment.type` 缺少 `FINAL`，本系统有 `FINAL` —— 后端 services 层做 SCORE 聚合时 final 也按权重计入

## 兜底行为

`apps/predictions/services.py` 用 `try/except` 包住 import：
- 模型未接入 → 自动降级返回 mock 数据，开发不被卡住
- 模型接入后 → 自动切换到真实推理
