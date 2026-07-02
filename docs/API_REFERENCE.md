# API 接口文档（前端协作版）

> Student Performance Analytics — Backend API Reference
> 后端版本:v3(模型 `huber-grade-v4`)。本文档所有示例均为**真实接口返回**(截断处已标注)。
> 有疑问先看第 2 节「数据语义速读」——前端渲染需要的所有枚举值、阈值、色阶规则都在那里。

---

## 目录
1. [快速开始](#1-快速开始)
2. [数据语义速读(渲染必读)](#2-数据语义速读渲染必读)
3. [通用约定](#3-通用约定)
4. [GET /api/health/](#4-get-apihealth)
5. [POST /api/predict-grade/](#5-post-apipredict-grade)
6. [GET /api/cohort-profile/](#6-get-apicohort-profile)
7. [GET /api/warning-timeline/](#7-get-apiwarning-timeline)
8. [GET /api/assessment-quality/](#8-get-apiassessment-quality)
9. [参考实现:/dashboard/](#9-参考实现dashboard)
10. [错误码汇总](#10-错误码汇总)

---

## 1. 快速开始

### 启动后端
```bash
cd backend
..\.venv\Scripts\python.exe manage.py runserver     # Windows
# Base URL: http://127.0.0.1:8000
```
首次或模型缺失时先训练(否则预测类接口返回 503):
```bash
python -m analytics.ml.train_real --save
```

### 跨域(CORS)
后端已允许以下前端开发地址跨域调用:
- `http://localhost:3000`(CRA/Next 默认)
- `http://localhost:5173`(Vite 默认)

用其它端口请联系后端在 `config/settings.py` 的 `CORS_ALLOWED_ORIGINS` 里追加。
无鉴权(开发阶段),无需携带任何 token/cookie。

### 一分钟连通性测试
```bash
curl http://127.0.0.1:8000/api/health/
curl http://127.0.0.1:8000/api/cohort-profile/ | head -c 500
```

---

## 2. 数据语义速读（渲染必读）

### 2.1 两类分数,别混
| 量 | 范围 | 含义 | 出现在 |
|---|---|---|---|
| **percentile(百分位)** | 0–100 | 学生在**本届**的相对位置,越高越强 | `dims.*`、弱项板 `pctl` |
| **grade(分数)** | 0–100 | 课程总评分(绝对分) | `projected`、`final`、`predicted_course_total` |

两者用**不同色阶**(见 2.5),不要用同一套阈值渲染。

### 2.2 枚举值(全部可能取值)
| 字段 | 取值 | 说明 |
|---|---|---|
| `risk` / `risk_level` | `"low"` `"medium"` `"high"` | 由预测总评分档:≥70 / 60–70 / <60 |
| `engagement` | `"ok"` `"gaps"` `"disengaged"` | 行为轨道;`disengaged` 是最高优先级警报(红) |
| `consistency_tag` | `"balanced"` `"uneven"` | uneven=偏科(有明确短板) |
| `homog_tag` | `"tight"` `"mixed"` `"wide"` | 组内同质性;tight=可当整体对待 |
| `data_coverage` | `"full"` `"partial"` `"insufficient"` | 预测输入完整度;insufficient 必须显著提示 |
| `verdict`(测评质量) | `"good discriminator"` `"weak"` `"poor"` `"ceiling"` `"no variance"` `"n/a"` | |
| tier `key` | `"excellent"` `"ontrack"` `"borderline"` `"atrisk"` | 分档;空档不返回 |
| snapshot | `"W3"` `"W6"` `"W9"` `"W12"` | 固定 4 个,顺序即时间序 |

### 2.3 风险信号的优先级(UI 呈现建议)
同一学生可能同时带多个信号,建议优先级(高→低):
1. `engagement == "disengaged"`(红,压倒一切——人正在消失)
2. `declining == true`(红,预测轨迹下滑 ≥5 分)
3. `risk == "high"`(红,预测总评 <60;本课程历史上极少触发)
4. `risk == "medium"` / `engagement == "gaps"`(黄)
5. `weak_in` 非空(黄色小标签,按维度显示)

### 2.4 多标签语义
`weak_in` 是**数组**(如 `["Quiz","Mid"]`):一个学生可同时弱于多个维度,弱项板之间
**人员有重叠**(`also_weak_in` 给出交叉)。不要当互斥分组渲染。

### 2.5 参考色阶(与官方 dashboard 一致,可直接抄)
```js
// 百分位(dims、pctl):>=75 绿 | >=50 浅绿 | >=25 黄 | <25 红
// 分数(projected/final):>=80 绿 | >=70 浅绿 | >=60 黄 | <60 红
```

### 2.6 重要口径声明(建议在 UI 上原样展示)
- `cohort-profile` 是**结课复盘视图**(`meta.view="retrospective"`,维度画像用全期数据);
  **学期中预警**数据来自 `warning-timeline`。
- 本课程**没有期末考试**;`predicted_course_total` 是课程总评(决定挂科的那个数),
  不是某场考试的分数。
- 所有预测均带不确定性区间——**展示区间,不要只显示点值**。

---

## 3. 通用约定

- **格式**:请求/响应均为 JSON(`Content-Type: application/json`);GET 无请求体。
- **数值**:均为 number(浮点),已在后端四舍五入(1–3 位小数);前端仍建议
  `toFixed()` 后展示。
- **缓存**:三个分析类接口(cohort-profile / warning-timeline / assessment-quality)
  首次调用现算(约 1–3 秒),之后进程内缓存(<10ms)。加 `?refresh=1` 强制重算
  (仅在底层数据/模型更新后需要,平时不要带)。
- **payload 体积**:cohort-profile ≈ **105 KB**(含全部 171 名学生明细),
  warning-timeline ≈ 28 KB,其余 ≤5 KB。建议页面加载时并发取一次、存前端状态,
  勿轮询。
- **错误体**:统一 `{"detail": "..."}`(503/404)或字段级 `{"字段名": ["原因"]}`(400)。
- **学生主键**:`(id, offering)` 联合唯一——`id` 是匿名学号字符串(如 `"000000020"`,
  **保留前导零,勿转数字**),`offering` 是学期(`"Data-Part1"`…`"Data-Part4"`,
  展示时可去掉 `Data-` 前缀)。跨接口关联学生用这两个字段。

---

## 4. GET /api/health/

**用途**:探活 + 模型状态。前端可在启动时调用,若 `loaded=false` 提示"模型未就绪"。

**响应 200**(真实样例):
```json
{
  "status": "ok",
  "grade_regressor": {
    "loaded": true,
    "version": "huber-grade-v4",
    "features": ["early_lab_avg", "early_assignment_pct", "early_quiz_avg"],
    "metrics_loso": {"mae": 4.459, "rmse": 5.848, "r2": 0.375},
    "exam_head_loaded": true,
    "exam_metrics_loso": {"mae": 8.075, "r2": 0.336},
    "target_note": "Primary target = official course total ..."
  },
  "note": "OULAD risk classifier retired from serving (research benchmark only); see docs."
}
```

---

## 5. POST /api/predict-grade/

**用途**:对**单个学生**做预测。输入他的早期成绩占比,返回预计课程总评(带区间、
挂科概率)、纯未来考试均分、逐特征解释。

### 请求体
三个字段**全部可选**,但缺失会触发 coverage 警告(见下);取值必须是 **0–1 的小数**
(占满分比例,不是百分数):

| 字段 | 类型 | 含义 |
|---|---|---|
| `early_lab_avg` | number 0–1 | 前 4 个 lab 的平均得分占比 |
| `early_assignment_pct` | number 0–1 | Assignment 1 得分占比 |
| `early_quiz_avg` | number 0–1 | 按日期最早 2 次 quiz 的平均得分占比 |

```json
{"early_lab_avg": 0.5, "early_assignment_pct": 0.4, "early_quiz_avg": 0.2}
```

### 响应 200 字段说明
| 字段 | 类型 | 说明 |
|---|---|---|
| `predicted_course_total` | number | 预计课程总评(0–100)。**主输出** |
| `prediction_interval_80` | [number, number] | 80% 预测区间,**必须随点值一起展示** |
| `prob_below_60` / `prob_below_70` | number 0–1 | 总评低于 60/70 的概率 |
| `uncertainty_sigma` | number | 预测标准差(σ=5.86,固定,来自留一学期残差) |
| `risk_level` | enum | 见 2.2;由点值分档 |
| `thresholds` | object | 分档定义,直接可渲染成图例 |
| `exam_head.predicted_exam_avg` | number | **纯未来**的期中 I+II 均分预测(0–100) |
| `exam_head.exam_interval_80` | [number, number] | 考试头的 80% 区间(σ=10.43,更宽是正常的) |
| `explanation` | object | 每特征对预测的**精确贡献(分)**,负=拖低。适合画横向条形图 |
| `model_version` | string | 当前 `"huber-grade-v4"` |
| `target_note` | string | 目标口径声明,建议放 tooltip |
| `data_coverage` | enum | `full`/`partial`/`insufficient` |
| `missing_features` | string[] | 仅缺失时出现:哪些特征被均值填补 |
| `warning` | string | 仅缺失时出现:**必须显著展示**(缺交本身即风险信号) |

### 示例:缺失输入(真实响应,注意 coverage 三件套)
请求 `{"early_quiz_avg": 0.15}` →
```json
{
  "predicted_course_total": 71.2,
  "prediction_interval_80": [63.7, 78.7],
  "prob_below_60": 0.028, "prob_below_70": 0.419,
  "uncertainty_sigma": 5.86,
  "risk_level": "low",
  "exam_head": {"predicted_exam_avg": 43.6, "exam_interval_80": [30.3, 57.0]},
  "explanation": {"early_lab_avg": 0.0, "early_assignment_pct": 0.0, "early_quiz_avg": -7.25},
  "thresholds": {"high": "<60", "medium": "60-70", "low": ">=70"},
  "model_version": "huber-grade-v4",
  "data_coverage": "insufficient",
  "missing_features": ["early_lab_avg", "early_assignment_pct"],
  "warning": "Missing early-work data was imputed with training averages, so the projection may be too optimistic. Missing submissions can themselves signal risk — verify before relying on this estimate."
}
```
> ⚠️ 前端契约:`data_coverage != "full"` 时,预测值必须降级展示(灰化/加警示图标+
> warning 文案),**禁止**当可靠结论渲染。

### 错误
- **400**(字段非法):`{"early_quiz_avg": ["A valid number is required."]}`(字段级)
- **503**(模型未训练):`{"detail": "Grade model not available. Run \`python -m analytics.ml.train_real --save\`."}`

---

## 6. GET /api/cohort-profile/

**用途**:全班分析,dashboard 主数据源。一次返回:班级统计、结果分档(双轨)、
弱项板、断缴名单、全部 171 名学生明细。

### Query 参数
| 参数 | 说明 |
|---|---|
| `clusters=1` | 附加返回探索性聚类块 `cluster_analysis`(研究用,默认省流量不返回) |
| `k=<int>` | 聚类簇数(仅与 clusters 连用,默认 4) |
| `refresh=1` | 强制重算(平时不要带) |

### 响应结构(顶层 5 块)
```
{ meta, class_stats, groups: {outcome_final, outcome_projected}, weakness_boards, disengagement }
```

**`meta`** — 口径声明:`view: "retrospective"` + `data_basis`(建议原样展示在页面顶部)。

**`class_stats`**(真实样例):
```json
{"n": 171, "projected_mean": 78.5, "cv_pct": 7.1, "pct_at_risk": 1.2,
 "n_uneven": 60, "n_multi_weak": 31, "n_disengaged": 7}
```
| 字段 | 说明 |
|---|---|
| `cv_pct` | 分数离散度(变异系数%);<12 可标 "homogeneous" |
| `pct_at_risk` | 预测总评<60 的学生占比% |
| `n_uneven` | 偏科学生数 | 
| `n_multi_weak` | 同时弱于 ≥2 维的学生数 |
| `n_disengaged` | 断缴学生数(红色 KPI) |

**`groups.outcome_final` / `groups.outcome_projected`** — 分档数组(依据:官方总评 /
早期预测分)。每组:
```json
{"key": "excellent", "name": "Excellent", "n": 73,
 "dim_avgs": {"Labs": 52.3, "Quiz": 68.1, "Assign": 52.4, "Mid": 77.6},
 "projected_avg": 81.2, "homogeneity": 18.7, "homog_tag": "mixed",
 "n_high": 0, "n_medium": 0, "members": [ ...学生明细... ]}
```
- `dim_avgs`:组内各维**平均百分位**(用百分位色阶)。
- `homogeneity`+`homog_tag`:σ 越小组越同质;`wide/mixed` 提示"组内混杂,需下钻"。
- 空档(n=0)不返回——渲染前按 `key` 容错。

**学生明细 `members[]`**(真实样例,所有分组/明细共用此结构):
```json
{"id": "000000002", "offering": "Data-Part1",
 "dims": {"Labs": 55.7, "Quiz": 38.6, "Assign": 67.1, "Mid": 51.4},
 "projected": 71.7, "lo": 64.0, "hi": 79.0,
 "risk": "low", "weakest": "Quiz", "weak_in": [],
 "engagement": "ok", "consistency": 10.2, "consistency_tag": "balanced"}
```
| 字段 | 说明 |
|---|---|
| `dims` | 四维**届内百分位**(0–100),热力图数据 |
| `projected` / `lo` / `hi` | 预测总评及 80% 区间(展示成 `71.7 (64–79)`) |
| `weakest` | 最弱的一维(即使不在 weak_in 里也有值) |
| `weak_in` | 多标签弱项数组,可为空 |
| `engagement` | 见 2.2/2.3,`disengaged` 渲染红标 |

**`weakness_boards[]`** — 4 个板(Labs/Quiz/Assign/Mid),多标签:
```json
{"dim": "Quiz", "n": 40, "share_pct": 23.4,
 "definition": "within-cohort percentile <= 25 in Quiz",
 "members": [
   {"id": "000000166", "offering": "Data-Part4", "pctl": 1.6,
    "projected": 68.9, "risk": "medium", "also_weak_in": ["Labs", "Mid"]} ]}
```
members 已按 `pctl` 升序(最弱在前);`also_weak_in` 用于交叉小标签。

**`disengagement`** — 行为轨道(红色优先级最高):
```json
{"rule": "miss = missing/zero component ...; disengaged = late>=3 or total>=5; gaps = late>=2 or total>=3.",
 "n_disengaged": 7, "n_gaps": 8,
 "members": [
   {"id": "000000020", "offering": "Data-Part1", "tag": "disengaged",
    "missed_total": 14, "missed_late": 10,
    "projected": 36.6, "final": 33.0, "risk": "high"} ]}
```
members 含 `disengaged` 和 `gaps` 两档(按 tag 字段区分),已排序(严重在前)。
`rule` 建议放说明 tooltip。

**`cluster_analysis`**(仅 `?clusters=1`)— 探索性 KMeans 原型 + 有效性元数据
(silhouette/ARI/borderline)。默认 UI 不用;需要时结构见响应本身,`meta.note`
已写明"仅探索性,组籍不可当事实"。

### 错误
**503**:数据文件或模型缺失,`{"detail": "Data or model not ready: ..."}`。

---

## 7. GET /api/warning-timeline/

**用途**:预警时间线——"第几周能预警"曲线 + 每个学生的预测轨迹 + 下滑警报。
**这是学期中视角的数据源**(与 cohort-profile 的结课复盘互补)。

### Query 参数
`refresh=1`(同前)。

### 响应结构
```
{ meta, curve, trajectories, declining, sanity_check }
```

**`meta`**:`assumption`(时间近似假设声明)+ `alert_rule`(`"drop >= 5 points between consecutive snapshots"`)。建议原样展示。

**`curve[]`** — 4 个快照的精度曲线(可画折线/表格):
```json
{"snapshot": "W3", "approx_week": 3, "features": ["labs", "quiz"],
 "mae": 4.48, "r2": 0.315, "sigma": 6.14}
```
固定顺序 W3→W6→W9→W12;`mae` 越小越准(W9 起因期中 I 落地精度跳升)。

**`trajectories[]`** — 全部 171 名学生(与 cohort-profile 的学生用 `id`+`offering` 关联):
```json
{"id": "000000000", "offering": "Data-Part1",
 "preds": {"W3": 77.1, "W6": 76.4, "W9": 77.5, "W12": 76.7},
 "final": 78.0, "max_drop": -0.8, "declining": false}
```
| 字段 | 说明 |
|---|---|
| `preds` | 4 个快照的预测总评(**out-of-fold**,诚实值)。适合画 sparkline |
| `max_drop` | 相邻快照间最大降幅(负数);`<= -5` 即 declining |
| `declining` | 下滑警报布尔值 |
| `final` | 真实最终总评(复盘对照用) |

**`declining[]`** — trajectories 中 declining=true 的子集,已按 `max_drop` 升序
(跌最狠的在前),直接渲染警报列表。

**`sanity_check`**:`{"n_declining": 25, "declining_mean_final": 71.5, "stable_mean_final": 79.9}`
——可做成一句话("下滑者均分 71.5 vs 稳定者 79.9,警报有效")。

---

## 8. GET /api/assessment-quality/

**用途**:测评质量面板(CTT 题目分析)——课程每个考核组件的难度/区分度/天花板。
面向"老师改进课程设计"的视图。

### Query 参数
`refresh=1`(同前)。

### 响应结构
```
{ meta, components, category_summary, insights }
```

**`components[]`** — 25 个组件,已按类别+名称排序:
```json
{"label": "Quiz 1", "category": "quizzes", "offerings": 4, "n": 163,
 "difficulty_pct": 59.3, "discrimination_r": 0.596,
 "ceiling_pct": 13.5, "verdict": "good discriminator"}
```
| 字段 | 说明 |
|---|---|
| `label` | 跨学期统一名(Lab 1…10 / Assignment 1…4 / Quiz 1…5 / Mid-Term Exam I Part I…) |
| `difficulty_pct` | 均分%(越高越容易) |
| `discrimination_r` | 区分度(item-total 相关);**可能为 null**(零方差组件),渲染成 `--` |
| `ceiling_pct` | ≥95% 满分的学生占比 |
| `verdict` | 见 2.2;`ceiling`/`no variance` 渲染红,`good discriminator` 绿 |

**`category_summary[]`**:`{"category": "midterm", "avg_discrimination_r": 0.709, "avg_ceiling_pct": 1.0}`
——类别级汇总,已按区分度降序。

**`insights[]`**:自动生成的结论句(string 数组),直接渲染成要点列表。
**`meta.caveat`**:方法学声明(期中 r 含 part-whole 膨胀),放 tooltip。

---

## 9. 参考实现:/dashboard/

`GET /dashboard/` 是后端自带的教师 dashboard(纯 HTML/JS,无框架),**完整消费了上述
全部接口**,可作为前端实现的活文档:
- 源码:`backend/analytics/templates/analytics/dashboard.html`(约 300 行)
- 内含:三接口并发加载、百分位/分数双色阶、下钻分组表、弱项板+断缴卡、列排序、
  declining/disengaged/weak 标签叠加逻辑
- 你们的正式前端可以整体替换它;它保留作为后端自检页面

---

## 10. 错误码汇总

| 状态码 | 场景 | 响应体 | 前端处理建议 |
|---|---|---|---|
| 200 | 正常 | 见各节 | — |
| 400 | predict-grade 字段非法(非数字/越界 0–1) | `{"字段": ["原因"]}` | 表单校验提示 |
| 404 | 路径不存在 | Django 默认页 | 检查 URL |
| 405 | 方法不对(如 GET 打 predict-grade) | `{"detail": "Method \"GET\" not allowed."}` | 检查 method |
| 503 | 模型/数据未就绪 | `{"detail": "..."}`(含修复命令) | 显示"后端未就绪"+detail |

---

## 附:字段可空性与兼容性承诺

- 以下字段**可能为 null**:`discrimination_r`、`declining_mean_final`(无下滑学生时)、
  `avg_discrimination_r`。其余数值字段保证非空。
- 以下字段**仅条件出现**:`missing_features`/`warning`(仅缺失输入时)、
  `exam_head`(模型 v3+ 均有,但建议做存在性判断)、`cluster_analysis`(仅 ?clusters=1)、
  组的空档(n=0 的 tier 不返回)。
- 枚举值集合(2.2 节)在 v3 内保证稳定;新增枚举值会先在本文档更新。
- 有接口变更需求(分页、按学期过滤、字段裁剪等)→ 直接提,后端半天内可加。
