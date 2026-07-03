# Education-Sys · AI 驱动学生表现分析与教育决策支持系统

COMP8567 · Team 7 · V1.1 原型骨架。

本仓库基于《项目需求分析文档》《系统开发技术文档（V1.1）》搭建：

- **backend/** — Django 5 + DRF + SQLite（默认）/ PostgreSQL（可选）
- **frontend/** — Vite + React + Ant Design + ECharts

当前阶段已完成的内容：

- 完整后端分层骨架（accounts / courses / imports / analytics / predictions / reports / audit 7 个 app）
- 数据库模型按技术文档 §4 设计落库（含 V1.1 修订：`model_version` 部分唯一索引、`prediction_run` 并发约束、`audit_log` 时间字段、`report_export.expires_at`）
- **可用功能**：用户注册 / 登录 / 登出 / 获取当前用户、课程与教学班 CRUD、文件上传创建导入批次、报告生成与下载
- **接口已打桩**（返回示例数据，便于前端原型联调）：班级总览、学生详情、风险预测、SHAP 解释、比较分析
- 全部前端页面原型：登录、注册、工作台、课程管理、教学班、数据导入、班级总览、学生详情、风险预测、比较分析、报告中心、个人信息
- 统一响应结构、分页（含 next/prev）、健康检查 `/api/v1/health`、OpenAPI 文档 `/api/docs/`

## 快速运行

### 1. 后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

python manage.py migrate
python manage.py createsuperuser   # 可选；用于 Django Admin
python manage.py runserver 0.0.0.0:8000
```

打开 http://localhost:8000/api/v1/health 应返回 `{"status":"ok",...}`。
OpenAPI Swagger：http://localhost:8000/api/docs/

### 2. 前端

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

打开 http://localhost:5173 → 自动跳转登录页 → 点「注册新账号」创建第一个教师账号。

> Vite 已通过 `/api` 代理到 `http://localhost:8000`，前后端可同时跑而无 CORS 问题。

## 目录结构

```
Education-Sys/
├── backend/
│   ├── config/                # Django 配置、URL、WSGI/ASGI
│   ├── common/                # 统一响应、分页、权限
│   ├── apps/
│   │   ├── accounts/          # User 模型 + 登录注册 (已实现)
│   │   ├── courses/           # Course / Section / Student / Assessment ... (已实现 CRUD)
│   │   ├── imports_app/       # ImportBatch + 上传接口 (已实现，校验逻辑待补)
│   │   ├── analytics/         # MetricSnapshot + 总览/分布/趋势 (mock 数据)
│   │   ├── predictions/       # ModelVersion / PredictionRun / RiskPrediction (mock 数据)
│   │   ├── reports_app/       # ReportExport + 生成/下载 (基础可下载)
│   │   └── audit/             # AuditLog 模型 (写入待补)
│   ├── requirements.txt
│   ├── .env.example
│   └── manage.py
├── frontend/
│   ├── src/
│   │   ├── api/               # axios 客户端 + auth
│   │   ├── contexts/          # AuthContext
│   │   ├── components/        # Layout / ProtectedRoute
│   │   └── pages/             # 全部页面原型
│   ├── vite.config.js
│   └── package.json
└── README.md
```

## 下一步开发路线（与技术文档第 7-8 章对齐）

1. **后端**：实现 imports 的真实 CSV/Excel 解析与字段校验、analytics 的指标计算 Service、ml/ 训练与预测管道、SHAP 解释、报告 PDF/Excel 真实生成器、audit_log 写入中间件。
2. **前端**：把 mock 数据替换为真实接口结果；补完表单校验、错误页、空状态、loading；按设计稿调整样式。
3. **基础设施**：Dockerfile + docker-compose；切换 PostgreSQL；CI 跑 `pytest` + `npm run build`。
