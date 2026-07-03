# 模型集成方案（给团队的速查文档）

> 仓库内分工：
>
> - `ml-service/`（原 `backend/`）—— Tianyang Ren：模型训练与推理（早期成绩回归 + 队列分析；OULAD 风险分类为研究基准，已从服务层退役）
> - `web-platform/`—— Honghao Zhang：账户、课程、教学班、导入、分析、预测、报告、前端
>
> **集成方式已落地：业务后端通过 HTTP 调用 ML 服务**（不再是"把 ml/ 代码拷进来"的旧方案）。

---

## 一、架构总览

```
浏览器 ──> 前端 :5173 ──(/api 代理)──> 业务后端 :8001 ──(HTTP)──> ML 服务 :8000
          web-platform/frontend        web-platform/backend        ml-service/
```

| 子项目 | 目录 | 端口 | 角色 |
|---|---|---|---|
| ML 服务 | `ml-service/` | **8000** | 机器学习/分析引擎，独立 Django，无鉴权 |
| 业务后端 | `web-platform/backend/` | **8001** | 业务系统，DRF Token 鉴权，通过 HTTP 调 ML 服务 |
| 前端 | `web-platform/frontend/` | **5173** | React + antd + ECharts |

> 服务器到服务器调用：ML 服务无鉴权、**不受 CORS 约束**（CORS 只管浏览器）。两个后端端口
> 分离（8000 / 8001），可同时运行。

---

## 二、集成层（业务后端侧）

所有对 ML 服务的调用都收敛到两个文件：

| 文件 | 职责 |
|---|---|
| `web-platform/backend/common/ml_gateway.py` | **唯一 HTTP 出口**。封装 5 个 ML 接口，统一异常（`MLServiceUnavailable` / `MLServiceError`）。地址来自 `settings.ML_API_BASE_URL`。 |
| `web-platform/backend/apps/predictions/services.py` | **适配层**。把业务数据聚合成模型特征、调用网关、做字段映射、ML 不可用时降级 mock。业务视图只认这一层。 |

配置（`web-platform/backend/.env` 或环境变量）：

```
ML_API_BASE_URL=http://127.0.0.1:8000
ML_API_TIMEOUT=5.0
```

---

## 三、两类接口（用途不同，别混）

### 3.1 按学生预测 —— `POST /api/predict-grade/`

**唯一能喂"业务库自己学生数据"的接口。** 输入三个早期成绩占比（0–1），输出预测课程总评 + 风险档。

- 触发：前端预测页 `POST /api/v1/sections/<id>/predictions/run`，或 `seed_all` / `seed_demo` 命令。
- 链路：`services.run_section_prediction()` → 遍历在读学生 → `build_features_for_student()` 聚合特征
  → `predict_risk()` / `predict_grade()` → `ml_gateway.predict_grade()` → 落 `RiskPrediction`。

> ML 侧的独立 risk 分类器已退役，所以业务侧的 `predict_risk()` **复用 predict-grade 的结果派生风险视图**
> （`prob_below_60` 作为风险概率，`explanation` 作为贡献因子）。

### 3.2 队列分析看板 —— 3 个 GET（透传）

这三个接口分析的是 **ML 侧固定研究数据集（171 名学生）**，不是业务库数据。业务后端只做鉴权 +
统一响应封装 + 透传：

| 业务后端接口 | → ML 服务接口 | 前端页面 |
|---|---|---|
| `GET /api/v1/analytics/cohort-profile` | `/api/cohort-profile/` | Cohort Insights |
| `GET /api/v1/analytics/warning-timeline` | `/api/warning-timeline/` | Cohort Insights |
| `GET /api/v1/analytics/assessment-quality` | `/api/assessment-quality/` | Cohort Insights |

---

## 四、字段映射与契约

### 4.1 predict-grade 输入特征（业务库 → 模型）

`build_features_for_student()` 从 `AssessmentScore` 聚合，取值 0–1：

| 特征 | 含义 |
|---|---|
| `early_lab_avg` | 最早 4 个 lab 的平均得分率 |
| `early_assignment_pct` | 最早 1 个 assignment 的得分率 |
| `early_quiz_avg` | 最早 2 次 quiz 的平均得分率 |

> 某类考核无成绩时**不传该键**，predict-grade 会用训练均值兜底并给 `data_coverage` 警告。

### 4.2 predict-grade 返回契约（ML 侧稳定，改动需双方约定）

```python
{
  "predicted_course_total": float,        # 预测课程总评 0–100（主输出）
  "prediction_interval_80": [float, float],
  "prob_below_60": float, "prob_below_70": float,
  "risk_level": "low" | "medium" | "high",  # 小写
  "explanation": {feature: contribution_float, ...},  # 对总评的加/减分
  "model_version": str,
  "data_coverage": "full" | "partial" | "insufficient",
  "warning": str,                         # 仅缺特征时出现
}
```

### 4.3 业务侧字段转换（适配层做）

| 项 | ML 侧 | 业务侧 | 转换 |
|---|---|---|---|
| 风险等级 | `low/medium/high`（小写） | `LOW/MEDIUM/HIGH`（大写） | `.upper()` |
| 主输出 | `predicted_course_total` | `predicted_final_grade` | 改名透传 |
| 风险概率 | `prob_below_60` | `probability` | 直接用 |
| 解释 | `{feature: 分值}` | `top_factors` 列表 | 按绝对值排序取 Top5；分值为负=拉低总评=增加风险 |

---

## 五、降级策略（ML 不可用时）

ML 服务没启动 / 模型没训练(503) / 超时 → 网关抛 `MLServiceUnavailable`：

- **预测接口**：`services` 自动降级到 mock 风险，业务照常返回（前后端联调不被卡）。
- **分析透传接口**：返回 `503`，前端 Cohort Insights 页显示友好警示条，不白屏。

因此即使 ML 服务离线，业务系统也能跑起来，只是预测/看板数据不是真实的。

---

## 六、验证连通性

```bash
# 1) ML 服务直连
curl http://127.0.0.1:8000/api/health/            # grade_regressor.loaded=true 即模型就绪

# 2) 业务后端 -> ML 服务 全链路
curl http://127.0.0.1:8001/api/v1/health          # 看 "ml": {"mode": "real", "base_url": "...:8000"}
```

`ml.mode` 为 `real` 表示已连上；为 `mock` 表示 ML 服务未就绪（走了降级）。

> 详细的接口字段说明见 `docs/API_REFERENCE.md`；本地启动见根目录 `使用说明.md`。
