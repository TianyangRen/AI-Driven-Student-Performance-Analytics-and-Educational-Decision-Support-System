"""模型集成适配层 —— 本系统与组员 ML 服务（backend/，跑在 :8000）之间的【唯一接口】。

集成方式：HTTP 调用（见 common/ml_gateway.py），而非进程内 import。
  · ML 服务未启动 / 模型未训练(503)：自动降级到 mock 数据，前后端联调不被卡住。
  · ML 服务就绪：自动走真实推理，上层 view / 前端 / 数据库都不需要改动。

所有需要调用模型的业务（risk_prediction、student profile、dashboard 风险统计……）
都应该且只应该通过本模块的 predict_risk() / predict_grade() 入口。

字段口径见 docs/API_REFERENCE.md：
  · 组员 backend 的 risk 分类器已从服务层退役，唯一的按学生预测入口是
    POST /api/predict-grade/（输入三个早期成绩占比，输出预测课程总评 + 风险档）。
  · 因此本模块的 predict_risk() 复用 predict-grade 的结果派生风险视图
    （prob_below_60 作为风险概率，explanation 作为贡献因子）。
"""
from __future__ import annotations

import logging
import random
from datetime import datetime, timezone
from typing import Any, Dict, List

from django.db import transaction

from common import ml_gateway

logger = logging.getLogger(__name__)

_SUGGESTION = ("Review the student's recent assignment completion first, "
               "and arrange a targeted check-in.")


# 早期特征的展示名（用于 top_factors）；键必须与 predict-grade 的 explanation 一致。
_FEATURE_DISPLAY = {
    "early_lab_avg": "Early lab average",
    "early_assignment_pct": "Early assignment score",
    "early_quiz_avg": "Early quiz average",
}

# 每个早期特征取「最早的前 N 个」同类考核，与 API_REFERENCE §5 的口径一致：
#   early_lab_avg=前 4 个 lab，early_assignment_pct=Assignment 1，early_quiz_avg=最早 2 次 quiz。
_EARLY_SPEC = {
    "early_lab_avg": ("LAB", 4),
    "early_assignment_pct": ("ASSIGNMENT", 1),
    "early_quiz_avg": ("QUIZ", 2),
}


# -------------------------------------------------------------------- #
# 1. 数据映射：本系统 ORM 实例 -> predict-grade 需要的特征 dict
# -------------------------------------------------------------------- #
def build_features_for_student(student, section, cutoff_week=None) -> Dict[str, float]:
    """把一个学生在某 section 的早期成绩聚合成 predict-grade 的输入特征。

    Parameters
    ----------
    student : apps.courses.models.Student
    section : apps.courses.models.CourseSection
    cutoff_week : int | None  —— 只用 week_no <= cutoff_week 的考核（避免用未来数据）。
                  None 表示不按周截断，仅靠「取最早的前 N 个」限定早期性。

    Returns
    -------
    dict —— 取值为 0–1 小数（占满分比例）。**只包含真正有成绩的键**；
    某类考核完全没有成绩时该键不出现 —— predict-grade 会用训练均值兜底，
    并在响应里给出 data_coverage != "full" 的警告（缺交本身即风险信号）。
        early_lab_avg         最早 4 个 lab 的平均得分率
        early_assignment_pct  Assignment 1（最早 1 个）的得分率
        early_quiz_avg        最早 2 次 quiz 的平均得分率
    """
    from apps.courses.models import AssessmentScore

    rows = list(
        AssessmentScore.objects.filter(
            student=student, assessment__section=section
        )
        .select_related("assessment")
        .values(
            "percentage",
            "assessment__type",
            "assessment__week_no",
        )
    )
    if cutoff_week is not None:
        rows = [
            r for r in rows
            if r["assessment__week_no"] is not None
            and r["assessment__week_no"] <= cutoff_week
        ]

    features: Dict[str, float] = {}
    for key, (atype, n) in _EARLY_SPEC.items():
        typed = [r for r in rows if r["assessment__type"] == atype]
        # 按周次升序取最早的前 N 个；无 week_no 的排到最后
        typed.sort(key=lambda r: (r["assessment__week_no"] is None,
                                  r["assessment__week_no"] or 0))
        earliest = typed[:n]
        if earliest:
            avg_pct = sum(float(r["percentage"]) for r in earliest) / len(earliest)
            features[key] = round(avg_pct / 100.0, 4)  # 0–100 -> 0–1
    return features


# -------------------------------------------------------------------- #
# 2. 统一推理入口
# -------------------------------------------------------------------- #
def predict_grade(features: Dict[str, Any]) -> Dict[str, Any]:
    """按学生预测课程总评。真实走 POST /api/predict-grade/，失败降级 mock。

    Returns（已映射为本系统前端约定的字段）:
      {
        "predicted_final_grade": float,      # = ML 的 predicted_course_total
        "prediction_interval_80": [lo, hi],
        "prob_below_60": float,
        "risk_level": "LOW"|"MEDIUM"|"HIGH",
        "explanation": {feature: 分值贡献},
        "data_coverage": "full"|"partial"|"insufficient",
        "warning": str | None,               # coverage != full 时前端必须显著展示
        "model_version": str,
      }
    """
    try:
        raw = ml_gateway.predict_grade(_only_features(features))
        return _map_grade(raw)
    except ml_gateway.MLServiceUnavailable as exc:
        logger.info("predict_grade 降级到 mock：%s", exc)
        return _grade_mock()


def predict_risk(features: Dict[str, Any]) -> Dict[str, Any]:
    """按学生输出风险视图。派生自 predict-grade（组员 risk 分类器已退役）。

    Returns:
      {
        "probability":   float ∈ [0, 1],     # 挂科概率 prob_below_60
        "risk_level":    "LOW"|"MEDIUM"|"HIGH",
        "model_version": str,
        "top_factors":   [{feature, display_name, contribution, direction}, ...],
      }
    """
    try:
        raw = ml_gateway.predict_grade(_only_features(features))
        return _map_risk(raw)
    except ml_gateway.MLServiceUnavailable as exc:
        logger.info("predict_risk 降级到 mock：%s", exc)
        return _risk_mock()


# -------------------------------------------------------------------- #
# 3. 字段映射：ML 服务响应 -> 本系统前端约定
# -------------------------------------------------------------------- #
def _only_features(features: Dict[str, Any]) -> Dict[str, float]:
    """只透传 predict-grade 认识的三个键，避免把 ORM 杂字段发过去。"""
    return {k: features[k] for k in _FEATURE_DISPLAY if k in features}


def _map_grade(raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "predicted_final_grade": raw.get("predicted_course_total"),
        "prediction_interval_80": raw.get("prediction_interval_80"),
        "prob_below_60": raw.get("prob_below_60"),
        "risk_level": str(raw.get("risk_level", "low")).upper(),
        "explanation": raw.get("explanation", {}),
        "data_coverage": raw.get("data_coverage"),
        "warning": raw.get("warning"),
        "model_version": raw.get("model_version", "unknown"),
    }


def _map_risk(raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "probability": float(raw.get("prob_below_60", 0.0)),
        "risk_level": str(raw.get("risk_level", "low")).upper(),
        "model_version": raw.get("model_version", "unknown"),
        "top_factors": _normalize_explanation(raw.get("explanation") or {}),
    }


def _normalize_explanation(expl: Dict[str, float]) -> List[Dict[str, Any]]:
    """{feature: 对总评的分值贡献} -> 前端 top_factors。按绝对值排序取 Top 5。

    predict-grade 的贡献是「对课程总评的加/减分」：负值 = 拖低总评 = 抬高风险。
    """
    items = sorted(
        ({"feature": k, "contribution": float(v)} for k, v in expl.items()),
        key=lambda x: abs(x["contribution"]),
        reverse=True,
    )[:5]
    return [
        {
            "feature": it["feature"],
            "display_name": _FEATURE_DISPLAY.get(it["feature"], it["feature"]),
            "contribution": round(it["contribution"], 4),
            # 贡献为负 = 拉低总评 = 增加风险
            "direction": "increase_risk" if it["contribution"] < 0 else "decrease_risk",
        }
        for it in items
    ]


# -------------------------------------------------------------------- #
# 4. mock 兜底（ML 服务未就绪时；输出结构与真实一致）
# -------------------------------------------------------------------- #
def _grade_mock() -> Dict[str, Any]:
    g = round(random.uniform(45, 90), 1)
    return {
        "predicted_final_grade": g,
        "prediction_interval_80": [round(g - 7.5, 1), round(g + 7.5, 1)],
        "prob_below_60": round(max(0.0, min(1.0, (70 - g) / 40)), 3),
        "risk_level": "HIGH" if g < 60 else ("MEDIUM" if g < 70 else "LOW"),
        "explanation": {"early_lab_avg": -3.0, "early_assignment_pct": -5.0, "early_quiz_avg": 1.0},
        "data_coverage": "full",
        "warning": None,
        "model_version": "mock-fallback",
    }


def _risk_mock() -> Dict[str, Any]:
    p = round(random.uniform(0.1, 0.9), 2)
    return {
        "probability": p,
        "risk_level": "HIGH" if p > 0.7 else ("MEDIUM" if p > 0.4 else "LOW"),
        "model_version": "mock-fallback",
        "top_factors": [
            {"feature": "early_assignment_pct", "display_name": "Early assignment score",
             "contribution": -5.0, "direction": "increase_risk"},
            {"feature": "early_lab_avg", "display_name": "Early lab average",
             "contribution": -3.0, "direction": "increase_risk"},
        ],
    }


# -------------------------------------------------------------------- #
# 5. 元信息：让 /health 之类的接口可以报告 ML 服务状态
# -------------------------------------------------------------------- #
def ml_status() -> Dict[str, Any]:
    """探活 ML 服务并回传其模型状态；服务不可用时返回 mock 模式。"""
    try:
        info = ml_gateway.health()
    except ml_gateway.MLServiceError as exc:
        return {"available": False, "mode": "mock", "reason": str(exc)}
    reg = info.get("grade_regressor", {})
    return {
        "available": True,
        "mode": "real",
        "base_url": ml_gateway._base(),
        "grade_regressor": reg,
        "risk_classifier": {
            # ML 服务已退役独立 risk 分类器；风险档由 grade 模型派生
            "loaded": bool(reg.get("loaded")),
            "version": reg.get("version", "derived-from-grade"),
        },
    }


# -------------------------------------------------------------------- #
# 6. section 级预测运行（供 API view 与 seed 命令共用）
# -------------------------------------------------------------------- #
def ensure_model_version():
    """确保有一条 ModelVersion，镜像 ML 服务当前的 grade 模型（审计锚点）。"""
    from .models import ModelVersion

    status_meta = ml_status()
    version = (status_meta.get("grade_regressor", {}) or {}).get("version") or "mock-fallback"
    mv, _ = ModelVersion.objects.get_or_create(
        name=version,
        defaults={
            "algorithm": "LOGISTIC_REGRESSION",  # 远端为 Huber 回归派生风险档，此处仅登记
            "feature_schema": list(_FEATURE_DISPLAY.keys()),
            "artifact_path": status_meta.get("base_url", "remote"),
            "is_active": False,
        },
    )
    return mv


def run_section_prediction(section, cutoff_week=None):
    """遍历 section 在读学生 → 建特征 → 预测 → 落 RiskPrediction，返回 PredictionRun。

    带完整运行生命周期（RUNNING → SUCCESS/FAILED）与事务保护。
    """
    from apps.courses.models import Enrollment

    from .models import PredictionRun, RiskPrediction

    model_version = ensure_model_version()
    run = PredictionRun.objects.create(
        model_version=model_version, section=section,
        status="RUNNING", feature_snapshot_time=datetime.now(timezone.utc),
    )
    try:
        enrollments = (
            Enrollment.objects.filter(section=section, status="ACTIVE")
            .select_related("student")
        )
        with transaction.atomic():
            for enr in enrollments:
                features = build_features_for_student(enr.student, section, cutoff_week)
                r = predict_risk(features)
                RiskPrediction.objects.create(
                    run=run, student=enr.student,
                    probability=r["probability"], risk_level=r["risk_level"],
                    top_factors=r["top_factors"], suggestion=_SUGGESTION,
                )
            run.status = "SUCCESS"
            run.save(update_fields=["status"])
    except Exception:
        run.status = "FAILED"
        run.save(update_fields=["status"])
        raise
    return run
