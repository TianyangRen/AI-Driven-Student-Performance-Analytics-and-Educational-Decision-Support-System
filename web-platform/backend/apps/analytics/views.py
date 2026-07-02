"""Mock analytics endpoints — return synthesized demo data so frontend prototypes render.

Exception: dashboard_summary() below is REAL —— it queries the DB, not mock.
"""
import random
from datetime import datetime, timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from common.responses import ok


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


def _demo_overview(section_id):
    random.seed(section_id or 1)
    return {
        "section": {"id": section_id, "course_code": "COMP8567", "section_code": "01"},
        "kpis": {
            "student_count": 48,
            "average_score": round(random.uniform(68, 80), 1),
            "median_score": round(random.uniform(70, 80), 1),
            "pass_rate": round(random.uniform(0.7, 0.9), 2),
        },
        "risk_summary": {"high": 5, "medium": 8, "low": 35},
        "score_distribution": [
            {"range": "0-59", "count": 8},
            {"range": "60-69", "count": 9},
            {"range": "70-79", "count": 15},
            {"range": "80-89", "count": 11},
            {"range": "90-100", "count": 5},
        ],
        "trend": [{"week": w, "average": round(random.uniform(65, 82), 1)} for w in range(1, 8)],
        "last_calculated_at": datetime.now(timezone.utc).isoformat(),
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def overview(request, section_id):
    return ok(_demo_overview(section_id))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def students(request, section_id):
    random.seed(section_id or 1)
    items = []
    for i in range(1, 21):
        risk = random.choice(["LOW", "LOW", "LOW", "MEDIUM", "HIGH"])
        items.append({
            "student_id": i,
            "anonymized_code": f"S-ANON-{i:03d}",
            "average_score": round(random.uniform(50, 95), 1),
            "attendance_rate": round(random.uniform(0.6, 1.0), 2),
            "risk_level": risk,
        })
    return ok(items)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def recalculate(request, section_id):
    return ok({"section_id": section_id, "status": "RECALCULATED",
               "calculated_at": datetime.now(timezone.utc).isoformat()})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def distribution(request, section_id):
    return ok(_demo_overview(section_id)["score_distribution"])


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def student_profile(request, section_id, student_id):
    random.seed(student_id)
    return ok({
        "student": {"id": student_id, "anonymized_code": f"S-ANON-{student_id:03d}"},
        "section_id": section_id,
        "assessments": [
            {"name": f"Lab {i}", "type": "LAB", "score": round(random.uniform(40, 95), 1), "weight": 5}
            for i in range(1, 6)
        ] + [
            {"name": "Midterm", "type": "MIDTERM", "score": round(random.uniform(50, 95), 1), "weight": 30},
        ],
        "indicators": {
            "mastery": round(random.uniform(0.4, 0.95), 2),
            "stability": round(random.uniform(0.5, 0.95), 2),
            "engagement": round(random.uniform(0.5, 1.0), 2),
            "improvement": round(random.uniform(-0.2, 0.4), 2),
        },
        "trend": [{"week": w, "score": round(random.uniform(50, 90), 1)} for w in range(1, 8)],
        "risk": {
            "level": random.choice(["LOW", "MEDIUM", "HIGH"]),
            "probability": round(random.uniform(0.1, 0.9), 2),
        },
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def student_indicators(request, section_id, student_id):
    return ok([{"week": w, "mastery": round(random.uniform(0.4, 0.95), 2)} for w in range(1, 8)])


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def comparisons(request):
    body = request.data
    return ok({
        "dimensions": body.get("dimensions", []),
        "series": [
            {"name": "Section A", "data": [72, 75, 78, 76, 80]},
            {"name": "Section B", "data": [68, 70, 73, 74, 76]},
        ],
        "labels": ["Quiz 1", "Quiz 2", "Lab 1", "Lab 2", "Midterm"],
    })
