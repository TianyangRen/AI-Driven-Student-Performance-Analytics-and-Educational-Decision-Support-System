# CSV/Excel 数据导入 — 设计文档

- 日期：2026-07-02
- 范围：`web-platform/backend`（`feat/web-platform` 分支）
- 负责人：Lei Jiang（后端负责人）
- 关联：Interim Report Sprint 1（LJ：import 错误报告列级提示）、挑战 #2（事务化导入 + 错误报告）

## 1. 背景与目标

当前 `apps/imports_app` 的上传接口是打桩：`create_import` 只创建一条
`ImportBatch`（`total_rows=0`），不读文件、不落库、不校验；`import_errors`
永远返回 `[]`。下游 analytics / predictions 因此全部依赖 mock 数据。

本设计把导入链路做成真实实现：教师下载模板 → 填数据 → 上传 CSV 或 Excel →
系统按模板 schema 逐行校验 → 合法行落库、非法行进错误报告 → 前端可查状态与错误。

**非目标**：不做异步任务队列（同步处理即可，原型数据量小）；不做 pandas 管线；
不改动 analytics/predictions（它们后续单独接真实数据）。

## 2. 关键决策（已与团队确认）

| 决策点 | 选择 |
|---|---|
| 文件格式 | CSV + Excel(.xlsx)，新增依赖 `openpyxl` |
| 模板切分 | 三个独立模板：ROSTER / SCORE / ACTIVITY |
| 模板下载 | 提供接口 `GET /imports/template` |
| 错误策略 | 部分入库（PARTIAL）：合法行入库，非法行进 `error_details` |
| percentage | 自动计算 `round(score/max_score*100, 2)`，教师不填 |
| anonymized_code | 自动生成，`S-ANON-001` 顺序号风格，创建时分配、稳定不变 |
| 未知 student_no | SCORE/ACTIVITY 中不在名单的 student_no 当错误行拒绝，不自动补建 |

## 3. 架构（分层）

```
apps/imports_app/
├── templates.py   # 单一 schema 源：三种模板的列定义 + 示例行
├── parsers.py     # 文件字节 -> list[dict]（按扩展名分流 csv / openpyxl）
├── services.py    # 规范化行 -> ORM 落库（事务、逐行校验、PARTIAL 语义）
├── views.py       # 仅 HTTP：下载模板 / 上传 / 查状态 / 查错误
└── tests.py       # 每模板 happy-path + PARTIAL + 列头缺失
```

分层理由：`views` 不含业务逻辑，`parsers` 与 `services` 可脱离 HTTP 单元测试，
`templates.py` 让「模板长什么样」与「校验按什么标准」共用同一份定义，不会漂移。

## 4. 模板 schema（`templates.py`）

每列定义：`name`（列头）、`required`（bool）、`type`（str/int/decimal/date/enum）、
`example`（示例值）、`choices`（枚举可选值）。

### ROSTER —— 学生名单
| 列 | 必填 | 类型 | 说明 |
|---|---|---|---|
| `student_no` | ✅ | str | 学号，Student 唯一键 |
| `full_name` | | str | 姓名 |
| `email` | | str | 邮箱 |

落库：`Student.get_or_create(student_no=...)`，新建时分配 `anonymized_code`；
再 `Enrollment.get_or_create(section, student)`（挂到 URL 的 section）。

### SCORE —— 成绩
| 列 | 必填 | 类型 | 说明 |
|---|---|---|---|
| `student_no` | ✅ | str | 必须已在本 section 名单中，否则该行报错 |
| `assessment_name` | ✅ | str | 考核名，section+name 唯一复用 |
| `assessment_type` | ✅ | enum | QUIZ/LAB/ASSIGNMENT/MIDTERM/FINAL/PARTICIPATION |
| `max_score` | ✅ | decimal | 满分，> 0 |
| `weight` | ✅ | decimal | 权重 |
| `week_no` | | int | 周次 |
| `score` | ✅ | decimal | 得分，0 ≤ score ≤ max_score |

落库：`Assessment.get_or_create(section, name, ...)`；
`AssessmentScore.update_or_create(assessment, student, score, percentage=round(score/max_score*100,2))`。

### ACTIVITY —— 活动/出勤
| 列 | 必填 | 类型 | 说明 |
|---|---|---|---|
| `student_no` | ✅ | str | 必须已在本 section 名单中 |
| `activity_date` | ✅ | date | YYYY-MM-DD |
| `activity_type` | ✅ | enum | ATTENDANCE/PARTICIPATION/LOGIN/OTHER |
| `metric_value` | ✅ | decimal | 指标值 |

落库：`StudentActivity.create(...)`。

## 5. 解析层（`parsers.py`）

- 入口 `parse(file, filename) -> list[dict]`，按扩展名分流：
  - `.csv` → 标准库 `csv.DictReader`
  - `.xlsx` → `openpyxl.load_workbook(read_only=True)`，取首个 sheet，首行作列头
  - 其它扩展名 → 抛 `UnsupportedFormat`
- 全空行跳过；保留 1-based 行号（含表头偏移），供错误定位。
- 列头缺失（缺任一 required 列）→ 抛 `MissingColumns`，`services` 据此整批 FAILED。

## 6. 落库层（`services.py`）

`process_import(batch, rows, schema)`：

1. 逐行按 schema 校验：必填、类型转换、枚举、范围（max_score>0、score≤max_score）、
   外键存在性（SCORE/ACTIVITY 的 student_no 是否在本 section 名单）。
2. 校验通过的行在**一个 `transaction.atomic()`** 内写入；非法行不写，
   收集 `{"row", "column", "value", "reason"}` 到列表。
3. 结束时：
   - 全部成功 → `status=SUCCESS`
   - 部分成功 → `status=PARTIAL`
   - 0 行成功（或列头缺失）→ `status=FAILED`
   - 回填 `total_rows`、`valid_rows`、`error_details`。
4. 幂等：`get_or_create` / `update_or_create`，同一文件重复导入不炸唯一约束。

## 7. 接口

| 方法 | 路径 | 说明 | 状态 |
|---|---|---|---|
| GET | `/api/v1/imports/template?type=ROSTER\|SCORE\|ACTIVITY&format=csv\|xlsx` | 下载空模板（列头 + 1 行示例）；缺省 format=csv | 新增 |
| POST | `/api/v1/sections/{section_id}/imports` | 上传文件（multipart，字段 `file`、`import_type`），同步解析落库，返回批次摘要 | 改造打桩 |
| GET | `/api/v1/imports/{batch_id}` | 批次状态 + total/valid/error 计数 | 补字段 |
| GET | `/api/v1/imports/{batch_id}/errors` | 返回 `error_details` 数组 | 改造空桩 |

### 错误行结构（`error_details`）
```json
[{"row": 5, "column": "score", "value": "abc", "reason": "must be a number"}]
```

### 上传响应（示例）
```json
{
  "batch_id": 12, "import_type": "SCORE", "status": "PARTIAL",
  "total_rows": 48, "valid_rows": 45, "error_count": 3
}
```

## 8. 依赖变更

`web-platform/backend/requirements.txt` 新增：
```
openpyxl==3.1.5
```

## 9. 测试（`tests.py`）

用 DRF test client + SQLite。每种模板覆盖：
- happy-path：合法文件 → SUCCESS，DB 行数正确，percentage 计算正确。
- PARTIAL：混入非法行 → status=PARTIAL，valid_rows 正确，error_details 命中行号/列/原因。
- FAILED：缺 required 列头 → FAILED，无任何落库。
- 模板下载：GET template 返回正确列头（csv 与 xlsx 各一）。
- 未知 student_no（SCORE）→ 该行进 error_details，不落库。

满足报告质量线「每个接口至少一个 happy-path 测试」。

## 10. 风险与取舍

- **同步处理大文件**：原型数据量（≤ 48 人/班）下可接受；若未来文件变大，
  解析层已隔离，可平滑改为异步任务。
- **openpyxl 只读首个 sheet**：模板是单 sheet，符合预期；多 sheet 上传只取第一个。
- **anonymized_code 顺序号并发**：原型单实例、导入为同步事务，顺序分配安全。
