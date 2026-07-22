# E2E 测试（Selenium + pytest）

用真实浏览器驱动前端，端到端验证**登录/注册**与**课程/教学班录入**流程，
并确认后端新增的校验在浏览器里确实生效。

## 覆盖用例

| 文件 | 用例 | 验证点 |
|---|---|---|
| `test_auth.py` | `register_new_user_lands_on_dashboard` | 注册成功跳转 `/dashboard` |
| `test_auth.py` | `register_as_admin_is_downgraded` | 注册选 ADMIN 也被降级为 Instructor（提权回归 #1）|
| `test_auth.py` | `login_valid_reaches_dashboard` | 正确凭据登录成功 |
| `test_auth.py` | `login_invalid_shows_error` | 错误凭据报错、停留登录页 |
| `test_courses.py` | `create_course_uppercases_code` | 小写课程码规范化为大写（#3）|
| `test_courses.py` | `create_course_requires_fields` | 空表单触发必填校验 |
| `test_courses.py` | `create_section_uppercases_code` | 小写 section 码规范化为大写（#3）|

> 注：section 归属校验（#2）需两个教师账号跨账户操作，单账户 UI 观察不到，
> 已由后端单测覆盖，这里不重复。

## 前置

- 已安装 Google Chrome 与 chromedriver（Selenium 4 也可自动管理驱动）。
- **手动启动前后端**（测试只连不起）：

```bash
# 后端（:8001）
cd web-platform/backend && uv run python manage.py runserver 8001

# 前端（:5173）
cd web-platform/frontend && npm run dev
```

## 安装与运行

```bash
cd web-platform/e2e
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

pytest
```

## 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `E2E_BASE_URL` | `http://localhost:5173` | 前端地址 |
| `E2E_HEADLESS` | `1`（无头） | 设 `0` 可打开浏览器实时观看 |

```bash
# 有头模式观看执行过程
E2E_HEADLESS=0 pytest -k section
```

## 说明

- 每个用例用带时间戳后缀的全新账号/课程码，避免 `unique` 冲突，可反复跑。
- 测试对着开发库（sqlite）执行，会产生真实数据；如需干净环境请单独准备测试库。
- 取元素刻意避开 i18n 文案（应用已切法语），改用 antd 稳定 `id` 与结构。
