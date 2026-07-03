"""ML 服务 HTTP 网关 —— web-platform 后端调用组员 backend(:8000) 的【唯一出口】。

组员的 backend/ 是独立的 ML/分析服务（见 docs/API_REFERENCE.md），提供 5 个接口：
    GET  /api/health/
    POST /api/predict-grade/         单个学生：早期成绩占比 -> 预测课程总评
    GET  /api/cohort-profile/        全班画像（研究数据集，结课复盘视图）
    GET  /api/warning-timeline/      预警时间线（学期中视角）
    GET  /api/assessment-quality/    测评质量（CTT 题目分析）

服务器到服务器调用：无鉴权、不受 CORS 约束。地址/超时来自 settings
（ML_API_BASE_URL / ML_API_TIMEOUT），可用环境变量覆盖。

上层业务不要直接 import requests —— 一律通过本模块，异常统一归一为：
    MLServiceUnavailable  服务没起 / 连不上 / 超时 / 模型未训练(503)
    MLServiceError        其它 4xx/5xx 或响应无法解析
这样调用方只需 try/except 两个异常，即可决定「降级到 mock」还是「向前端报错」。
"""
from __future__ import annotations

import logging
from typing import Any, Dict

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class MLServiceError(Exception):
    """ML 服务返回了错误（非 503 的 4xx/5xx，或响应体无法解析）。"""


class MLServiceUnavailable(MLServiceError):
    """ML 服务不可用：连不上 / 超时 / 模型或数据未就绪(503)。调用方通常应降级。"""


def _base() -> str:
    return settings.ML_API_BASE_URL.rstrip("/")


def _timeout() -> float:
    return float(getattr(settings, "ML_API_TIMEOUT", 5.0))


def _handle(resp: requests.Response) -> Dict[str, Any]:
    """把 Response 归一成 dict，或抛出统一异常。"""
    if resp.status_code == 503:
        # 模型/数据未就绪，响应体是 {"detail": "...含修复命令..."}
        detail = _safe_detail(resp)
        raise MLServiceUnavailable(detail)
    try:
        resp.raise_for_status()
    except requests.HTTPError as exc:
        raise MLServiceError(f"{resp.status_code}: {_safe_detail(resp)}") from exc
    try:
        return resp.json()
    except ValueError as exc:
        raise MLServiceError("ML 服务返回了非 JSON 响应") from exc


def _safe_detail(resp: requests.Response) -> str:
    try:
        body = resp.json()
    except ValueError:
        return resp.text[:200]
    if isinstance(body, dict):
        return str(body.get("detail") or body)
    return str(body)


def _get(path: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    url = f"{_base()}{path}"
    try:
        resp = requests.get(url, params=params, timeout=_timeout())
    except requests.RequestException as exc:
        logger.warning("ML GET %s 失败: %s", url, exc)
        raise MLServiceUnavailable(f"无法连接 ML 服务 ({url}): {exc}") from exc
    return _handle(resp)


def _post(path: str, json: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{_base()}{path}"
    try:
        resp = requests.post(url, json=json, timeout=_timeout())
    except requests.RequestException as exc:
        logger.warning("ML POST %s 失败: %s", url, exc)
        raise MLServiceUnavailable(f"无法连接 ML 服务 ({url}): {exc}") from exc
    return _handle(resp)


# ------------------------------------------------------------------ #
# 具体接口（薄封装，保留原始响应结构；字段映射交给上层 services 层）
# ------------------------------------------------------------------ #
def health() -> Dict[str, Any]:
    return _get("/api/health/")


def predict_grade(features: Dict[str, Any]) -> Dict[str, Any]:
    """features: {early_lab_avg, early_assignment_pct, early_quiz_avg}，均为 0–1 小数。"""
    return _post("/api/predict-grade/", features)


def cohort_profile(**params: Any) -> Dict[str, Any]:
    """可选 params: clusters=1, k=<int>, refresh=1。"""
    return _get("/api/cohort-profile/", {k: v for k, v in params.items() if v is not None})


def warning_timeline(**params: Any) -> Dict[str, Any]:
    return _get("/api/warning-timeline/", {k: v for k, v in params.items() if v is not None})


def assessment_quality(**params: Any) -> Dict[str, Any]:
    return _get("/api/assessment-quality/", {k: v for k, v in params.items() if v is not None})


def is_available() -> bool:
    """探活：供 /health 之类的接口报告 ML 服务状态。"""
    try:
        health()
        return True
    except MLServiceError:
        return False
