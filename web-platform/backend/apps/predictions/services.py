"""
模型集成适配层 —— 本系统与组员（Tianyang Ren）模型代码之间的【唯一接口】。

设计目标：
  1) 组员模型还没接入时：自动降级到 mock 数据，前后端联调不被卡住。
  2) 组员模型接入后（把 ml/ 目录复制到 backend/ml/）：本文件自动启用真实推理，
     上层 view / 前端 / 数据库都不需要任何改动。

所有需要调用模型的业务（risk_prediction、student profile、dashboard 风险
统计……）都应该且只应该通过本模块的 predict_risk() / predict_grade() 入口。
"""
from __future__ import annotations

import logging
import random
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------- #
# 1. 启动时尝试加载组员的真实模型服务
# -------------------------------------------------------------------- #
# 组员仓库结构（参考）：
#     backend/analytics/ml/service.py        -> class MLService
#     backend/analytics/ml/grade_service.py  -> class GradeService
#     backend/analytics/ml/features.py       -> FEATURE_COLUMNS
# 等他把这些文件复制到 web-platform/backend/ml/ 后，下面的 import 即成功。
_REAL_ML_AVAILABLE = False
_MLService = None
_GradeService = None
_FEATURE_COLUMNS: List[str] = []

try:
    from ml.service import MLService as _MLService            # type: ignore
    from ml.grade_service import GradeService as _GradeService  # type: ignore
    from ml.features import FEATURE_COLUMNS as _FEATURE_COLUMNS  # type: ignore
    _REAL_ML_AVAILABLE = True
    logger.info("✔ teammate ML modules loaded: MLService + GradeService")
except Exception as exc:  # noqa: BLE001 —— 任何失败都走 mock，不影响系统启动
    logger.warning(
        "ML 模块尚未集成 (%s)。/predictions/* 接口将使用 mock 数据。"
        "等组员模型稳定后参考 backend/ml/README.md 接入。", exc,
    )


# -------------------------------------------------------------------- #
# 2. 数据映射：把本系统的 ORM 实例 → 组员模型需要的特征 dict
# -------------------------------------------------------------------- #
# 当前是占位实现（返回默认值），等指标计算管线（apps/analytics）真正落地后
# 改成从 metric_snapshot / assessment_score 聚合出 FEATURE_COLUMNS 字段。
def build_features_for_student(student, section, cutoff=None) -> Dict[str, float]:
    """
    Parameters
    ----------
    student : apps.courses.models.Student
    section : apps.courses.models.CourseSection
    cutoff  : datetime | None  —— 特征截止时间（避免使用未来数据）

    Returns
    -------
    dict —— 键名必须与组员 ml/features.py 的 FEATURE_COLUMNS 一致。
            未知字段缺省为 None，他的 to_feature_row() 会用 FEATURE_DEFAULTS 兜底。
    """
    # OULAD 风格特征键；现在用兜底数值，等真实指标管线接通后填聚合结果
    return {
        "total_clicks": 0.0,
        "active_days": 0.0,
        "mean_clicks_per_day": 0.0,
        "early_avg_score": 65.0,
        "num_prev_attempts": 0.0,
        "studied_credits": 60.0,
    }


# -------------------------------------------------------------------- #
# 3. 统一推理入口：风险二分类
# -------------------------------------------------------------------- #
def predict_risk(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    单一推理入口；上层 view 只关心本函数的返回结构。

    Returns
    -------
    {
      "probability":   float ∈ [0, 1],
      "risk_level":    "LOW" | "MEDIUM" | "HIGH",
      "model_version": str,
      "top_factors":   [
          {"feature", "display_name", "contribution", "direction"}, ...
      ],
    }
    """
    if _REAL_ML_AVAILABLE and _MLService is not None:
        return _predict_real(features)
    return _predict_mock(features)


def predict_grade(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    GradeService 入口：基于早期成绩特征预测期末总分。
    Returns: {"predicted_final_grade", "risk_level", "model_version", "explanation"}
    """
    if _REAL_ML_AVAILABLE and _GradeService is not None and _GradeService.is_loaded():
        return _GradeService.predict(features)
    # mock
    g = round(random.uniform(45, 90), 1)
    return {
        "predicted_final_grade": g,
        "risk_level": "HIGH" if g < 60 else ("MEDIUM" if g < 70 else "LOW"),
        "model_version": "mock-fallback",
        "explanation": {"early_lab_avg": -3.0, "early_assignment_pct": -5.0},
    }


# -------------------------------------------------------------------- #
# 4. 实现细节：真实模型 / mock 兜底
# -------------------------------------------------------------------- #
# 组员 MLService.predict() 的输出契约：
#   {"risk_score": float, "risk_level": "low"/"medium"/"high",
#    "model_version": str, "explanation": {feature: contribution, ...}}
# 我们的前端约定字段名不同（risk_level 全大写、用 top_factors 列表 + direction），
# 因此这里做一次转换。
def _predict_real(features: Dict[str, Any]) -> Dict[str, Any]:
    raw = _MLService.predict(features)
    return {
        "probability": float(raw.get("risk_score", 0.0)),
        "risk_level": str(raw.get("risk_level", "low")).upper(),
        "model_version": raw.get("model_version", "unknown"),
        "top_factors": _normalize_explanation(raw.get("explanation") or {}),
    }


def _normalize_explanation(expl: Dict[str, float]) -> List[Dict[str, Any]]:
    """{feature: contribution} -> 前端使用的 top_factors 列表。按绝对值排序取 Top 5。"""
    display = {
        "total_clicks": "Total VLE clicks",
        "active_days": "Active days",
        "mean_clicks_per_day": "Mean clicks per day",
        "early_avg_score": "Early average score",
        "num_prev_attempts": "Previous attempts",
        "studied_credits": "Studied credits",
    }
    items = sorted(
        ({"feature": k, "contribution": float(v)} for k, v in expl.items()),
        key=lambda x: abs(x["contribution"]),
        reverse=True,
    )[:5]
    return [
        {
            "feature": it["feature"],
            "display_name": display.get(it["feature"], it["feature"]),
            "contribution": round(it["contribution"], 4),
            "direction": "increase_risk" if it["contribution"] > 0 else "decrease_risk",
        }
        for it in items
    ]


def _predict_mock(features: Dict[str, Any]) -> Dict[str, Any]:
    """组员模型尚未接入时的兜底；输出结构与真实模型完全一致。"""
    p = round(random.uniform(0.1, 0.9), 2)
    return {
        "probability": p,
        "risk_level": "HIGH" if p > 0.7 else ("MEDIUM" if p > 0.4 else "LOW"),
        "model_version": "mock-fallback",
        "top_factors": [
            {"feature": "early_avg_score", "display_name": "Early average score",
             "contribution": 0.23, "direction": "increase_risk"},
            {"feature": "active_days", "display_name": "Active days",
             "contribution": 0.18, "direction": "increase_risk"},
        ],
    }


# -------------------------------------------------------------------- #
# 5. 元信息：让 /health 之类的接口可以报告 ml 模块状态
# -------------------------------------------------------------------- #
def ml_status() -> Dict[str, Any]:
    if not _REAL_ML_AVAILABLE:
        return {"available": False, "mode": "mock", "reason": "ml/ not yet integrated"}
    return {
        "available": True,
        "mode": "real",
        "feature_columns": list(_FEATURE_COLUMNS),
        "risk_classifier": {
            "loaded": _MLService.is_model_loaded(),
            "version": _MLService.version(),
        },
        "grade_regressor": _GradeService.info(),
    }
