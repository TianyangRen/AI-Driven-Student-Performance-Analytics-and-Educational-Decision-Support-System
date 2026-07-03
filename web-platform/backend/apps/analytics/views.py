"""Analytics endpoints —— 全部基于真实 DB 聚合（见 apps/analytics/services.py）。

  · dashboard_summary / overview / students / distribution / student_profile
    / student_indicators / comparisons：从 AssessmentScore / StudentActivity /
    RiskPrediction 等真实数据计算。
  · cohort_profile / warning_timeline / assessment_quality：透传组员 ML 服务(:8000)。

分数口径统一为 percentage(0–100) 按权重加权；风险来自最近一次成功预测运行。
"""
from datetime import datetime, timezone
from statistics import mean, median

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.courses.models import AssessmentScore, CourseSection, Enrollment, Student
from common import ml_gateway
from common.responses import fail, ok

from . import services


def _get_section_or_404(request, section_id):
    """取 section 并做权限校验：非 admin 只能看自己名下的 section。"""
    section = get_object_or_404(CourseSection.objects.select_related("course"), pk=section_id)
    user = request.user
    if not user.is_admin and section.instructor_id != user.id:
        raise Http404
    return section


# ------------------------------------------------------------------ #
# 真实数据接口：工作台汇总（不是 mock）
# ------------------------------------------------------------------ #
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_summary(request):
    """
    GET /api/v1/dashboard/summary —— 工作台顶部统计卡 + 教学班快捷入口。

    数据按权限过滤：ADMIN / 超级用户看全部，普通教师只看自己名下。
    """
    from django.db.models import Count, Q
    from apps.courses.models import Course, CourseSection, Enrollment
    from apps.predictions.models import RiskPrediction
    from apps.reports_app.models import ReportExport

    user = request.user
    if user.is_admin:
        courses = Course.objects.all()
        sections = CourseSection.objects.select_related("course").all()
        reports = ReportExport.objects.all()
    else:
        courses = Course.objects.filter(owner=user)
        sections = CourseSection.objects.select_related("course").filter(instructor=user)
        reports = ReportExport.objects.filter(requested_by=user)

    section_ids = list(sections.values_list("id", flat=True))

    student_count = (
        Enrollment.objects.filter(section_id__in=section_ids)
        .values("student").distinct().count()
    )
    high_risk_count = (
        RiskPrediction.objects.filter(run__section_id__in=section_ids, risk_level="HIGH")
        .values("student").distinct().count()
    )
    pending_reports = reports.filter(status__in=["PENDING", "PROCESSING"]).count()

    # 每个教学班的学生数 / 高风险数，供快捷入口列表展示
    per_section_students = {
        row["section_id"]: row["n"]
        for row in Enrollment.objects.filter(section_id__in=section_ids)
        .values("section_id").annotate(n=Count("student", distinct=True))
    }
    per_section_risk = {
        row["run__section_id"]: row["n"]
        for row in RiskPrediction.objects.filter(run__section_id__in=section_ids, risk_level="HIGH")
        .values("run__section_id").annotate(n=Count("student", distinct=True))
    }

    section_list = [
        {
            "id": s.id,
            "course_code": s.course.code,
            "course_name": s.course.name,
            "section_code": s.section_code,
            "term": s.course.term,
            "student_count": per_section_students.get(s.id, 0),
            "high_risk_count": per_section_risk.get(s.id, 0),
        }
        for s in sections.order_by("course__code", "section_code")
    ]

    return ok({
        "kpis": {
            "course_count": courses.count(),
            "section_count": len(section_ids),
            "student_count": student_count,
            "high_risk_count": high_risk_count,
            "pending_report_count": pending_reports,
        },
        "sections": section_list,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def overview(request, section_id):
    """班级总览：KPI + 风险分布 + 分数分布 + 每周趋势（真实 DB 聚合）。"""
    section = _get_section_or_404(request, section_id)
    ids = services.active_student_ids(section)
    scores = services.student_scores(section, ids)
    vals = list(scores.values())
    _, run = services.risk_by_student(section)

    return ok({
        "section": {
            "id": section.id,
            "course_code": section.course.code,
            "section_code": section.section_code,
        },
        "kpis": {
            "student_count": len(ids),
            "average_score": round(mean(vals), 1) if vals else 0,
            "median_score": round(median(vals), 1) if vals else 0,
            "pass_rate": round(sum(1 for v in vals if v >= services.PASS_MARK) / len(vals), 2) if vals else 0,
        },
        "risk_summary": services.risk_summary(section, ids),
        "score_distribution": services.score_distribution(vals),
        "trend": services.weekly_trend(section),
        "last_calculated_at": (run.created_at if run else datetime.now(timezone.utc)).isoformat(),
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def students(request, section_id):
    """班级学生列表：均分 + 出勤率 + 风险等级（真实 DB 聚合）。"""
    section = _get_section_or_404(request, section_id)
    ids = services.active_student_ids(section)
    scores = services.student_scores(section, ids)
    attendance = services.attendance_rates(section, ids)
    rmap, _ = services.risk_by_student(section)

    enrollments = (
        Enrollment.objects.filter(section=section, status="ACTIVE")
        .select_related("student")
    )
    items = [
        {
            "student_id": e.student_id,
            "anonymized_code": e.student.anonymized_code,
            "average_score": round(scores.get(e.student_id, 0.0), 1),
            "attendance_rate": attendance.get(e.student_id, 0.0),
            "risk_level": (rmap.get(e.student_id) or {}).get("level", "LOW"),
        }
        for e in enrollments
    ]
    items.sort(key=lambda x: x["average_score"])
    return ok(items)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def recalculate(request, section_id):
    """重算入口：分析类指标为实时聚合、无需缓存，这里回报最近一次预测运行时间。"""
    section = _get_section_or_404(request, section_id)
    run = services.latest_success_run(section)
    return ok({
        "section_id": section.id,
        "status": "RECALCULATED",
        "last_prediction_run_at": run.created_at.isoformat() if run else None,
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def distribution(request, section_id):
    """分数分布（真实）。"""
    section = _get_section_or_404(request, section_id)
    scores = services.student_scores(section, services.active_student_ids(section))
    return ok(services.score_distribution(list(scores.values())))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def student_profile(request, section_id, student_id):
    """学生画像：考核明细 + 多维指标 + 趋势 + 风险（真实 DB 聚合）。"""
    section = _get_section_or_404(request, section_id)
    student = get_object_or_404(Student, pk=student_id)

    rows = (
        AssessmentScore.objects.filter(assessment__section=section, student=student)
        .select_related("assessment")
        .order_by("assessment__week_no", "assessment__name")
    )
    assessments = [
        {
            "name": r.assessment.name,
            "type": r.assessment.type,
            "score": round(float(r.percentage), 1),
            "weight": float(r.assessment.weight),
        }
        for r in rows
    ]
    percentages = [float(r.percentage) for r in rows]
    rmap, _ = services.risk_by_student(section)
    r = rmap.get(student.id)

    return ok({
        "student": {"id": student.id, "anonymized_code": student.anonymized_code},
        "section_id": section.id,
        "assessments": assessments,
        "indicators": services.student_indicators(section, student, percentages),
        "trend": services.student_weekly_trend(section, student),
        "risk": {
            "level": r["level"] if r else "LOW",
            "probability": r["probability"] if r else 0.0,
            "prediction_id": r["prediction_id"] if r else None,
        },
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def student_indicators(request, section_id, student_id):
    """学生每周得分趋势（真实）。"""
    section = _get_section_or_404(request, section_id)
    student = get_object_or_404(Student, pk=student_id)
    return ok(services.student_weekly_trend(section, student))


# ------------------------------------------------------------------ #
# 队列分析看板：透传组员 ML 服务(:8000) 的三个分析接口
# ------------------------------------------------------------------ #
# 这三个接口分析的是 ML 侧的固定研究数据集（非本系统 DB），本层只做鉴权 +
# 统一响应封装 + 服务不可用兜底，数据结构原样透传（见 docs/API_REFERENCE.md）。
def _proxy(fetch, request):
    """调用 ML 网关并用统一响应封装；ML 服务不可用时返回 503 业务错误。"""
    params = {}
    if request.query_params.get("refresh") is not None:
        params["refresh"] = 1
    try:
        return ok(fetch(**params))
    except ml_gateway.MLServiceUnavailable as exc:
        return fail("ML_SERVICE_UNAVAILABLE", str(exc), http_status=503)
    except ml_gateway.MLServiceError as exc:
        return fail("ML_SERVICE_ERROR", str(exc), http_status=502)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def cohort_profile(request):
    """GET 全班画像（结课复盘视图）。透传 /api/cohort-profile/。
    额外支持 ?clusters=1&k=<int> 透传给 ML 服务。"""
    params = {}
    if request.query_params.get("refresh") is not None:
        params["refresh"] = 1
    if request.query_params.get("clusters") is not None:
        params["clusters"] = 1
    if request.query_params.get("k"):
        params["k"] = request.query_params.get("k")
    try:
        return ok(ml_gateway.cohort_profile(**params))
    except ml_gateway.MLServiceUnavailable as exc:
        return fail("ML_SERVICE_UNAVAILABLE", str(exc), http_status=503)
    except ml_gateway.MLServiceError as exc:
        return fail("ML_SERVICE_ERROR", str(exc), http_status=502)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def warning_timeline(request):
    """GET 预警时间线（学期中视角）。透传 /api/warning-timeline/。"""
    return _proxy(ml_gateway.warning_timeline, request)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def assessment_quality(request):
    """GET 测评质量（CTT 题目分析）。透传 /api/assessment-quality/。"""
    return _proxy(ml_gateway.assessment_quality, request)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def comparisons(request):
    """按维度对比各群体在各考核类型上的平均得分率（真实 DB 聚合）。

    Body: {"dimension": "SECTION"|"COURSE"|"TERM"|"ASSESSMENT_TYPE"}
    权限范围：admin 看全部，教师只看自己名下的 section。
    """
    dimension = (request.data.get("dimension") or "SECTION").upper()
    valid = {"SECTION", "COURSE", "TERM", "ASSESSMENT_TYPE"}
    if dimension not in valid:
        return fail("VALIDATION_FAILED", f"dimension 必须是 {', '.join(sorted(valid))} 之一", 422)
    return ok(services.comparison(request.user, dimension))
