"""Predictions API。

本文件【不直接】调用任何 ML 库 —— 全部模型相关调用都走 services 适配层
（services.build_features_for_student → services.predict_risk），从而：
  - 当 ML 服务(:8000)未就绪时：services 自动返回 mock，本视图无需感知
  - 当 ML 服务就绪后：services 自动启用真实推理，本视图同样无需改动

数据流：Enrollment(真实选课) -> build_features_for_student(按学生聚合早期成绩)
         -> predict_risk(HTTP 调 ML 服务) -> RiskPrediction(落库)。
"""
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.courses.models import CourseSection
from common.pagination import paginate_list
from common.responses import ok, fail

from .models import PredictionRun, RiskPrediction
from . import services

_DISCLAIMER = ("This result is a teaching-support signal only and is not an "
               "automated academic decision.")

# 教学周合理上限：cutoff 只用于「按周截断早期考核」，取一学年 53 周作宽松上界。
_MAX_CUTOFF_WEEK = 53


def _parse_cutoff_week(raw):
    """把请求里的 feature_cutoff_week 规范成 int 或 None。

    Returns (value, error_message)。value 为 None 表示不按周截断（合法）。
    校验失败时 error_message 非空——避免把字符串/负数原样带到
    services 里做 `week_no <= cutoff_week` 比较而抛 TypeError → 500。
    """
    if raw is None or raw == "":
        return None, None
    if isinstance(raw, bool):  # bool 是 int 子类，单独挡掉
        return None, "feature_cutoff_week 必须是整数"
    try:
        week = int(raw)
    except (TypeError, ValueError):
        return None, "feature_cutoff_week 必须是整数"
    if week < 1 or week > _MAX_CUTOFF_WEEK:
        return None, f"feature_cutoff_week 必须在 1–{_MAX_CUTOFF_WEEK} 之间"
    return week, None


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def run_prediction(request, section_id):
    """触发一次 section 级预测运行：遍历在读学生 → 建特征 → 预测 → 落库。

    Body(可选): {"feature_cutoff_week": int}  只用该周及之前的考核建特征（防泄漏）。
    """
    section = get_object_or_404(CourseSection, pk=section_id)
    cutoff_week, err = _parse_cutoff_week(request.data.get("feature_cutoff_week"))
    if err:
        return fail("VALIDATION_FAILED", err, 422,
                    [{"field": "feature_cutoff_week", "reason": err}])
    run = services.run_section_prediction(section, cutoff_week=cutoff_week)

    return ok({
        "run_id": run.id,
        "section_id": section.id,
        "status": run.status,
        "student_count": run.predictions.count(),
        "model_version": run.model_version.name,
        "feature_cutoff_week": cutoff_week,
        "ml_mode": services.ml_status().get("mode", "mock"),
        "created_at": run.created_at.isoformat(),
    }, status=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_predictions(request, section_id):
    """返回 section 内学生最近一次成功运行的预测列表（从 RiskPrediction 读）。"""
    section = get_object_or_404(CourseSection, pk=section_id)
    latest_run = (
        PredictionRun.objects.filter(section=section, status="SUCCESS")
        .order_by("-created_at").first()
    )
    if latest_run is None:
        return ok([], meta={"note": "No successful prediction run yet; POST .../predictions/run first."})

    preds = (
        RiskPrediction.objects.filter(run=latest_run)
        .select_related("student").order_by("-probability")
    )
    items = [
        {
            "prediction_id": p.id,
            "student_id": p.student_id,
            "anonymized_code": p.student.anonymized_code,
            "probability": float(p.probability),
            "risk_level": p.risk_level,
        }
        for p in preds
    ]
    return paginate_list(request, items, extra_meta={
        "run_id": latest_run.id,
        "model_version": latest_run.model_version.name,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def explanation(request, prediction_id):
    """单条预测的特征贡献解释（从落库的 RiskPrediction 读，含 top_factors）。"""
    p = get_object_or_404(
        RiskPrediction.objects.select_related("student", "run__model_version"),
        pk=prediction_id,
    )
    return ok({
        "prediction_id": p.id,
        "student_code": p.student.anonymized_code,
        "probability": float(p.probability),
        "risk_level": p.risk_level,
        "model_version": p.run.model_version.name,
        "top_factors": p.top_factors or [],
        "suggestion": p.suggestion or _SUGGESTION,
        "disclaimer": _DISCLAIMER,
    })
