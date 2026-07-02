"""API views.

Product surface (v2):
  GET  /api/health/          service + model status
  POST /api/predict-grade/   per-student projection (course total + exam head)
  GET  /api/cohort-profile/  whole-class analysis for the dashboard
  GET  /dashboard/           the instructor dashboard page

The OULAD risk classifier was RETIRED from the product surface: its features
(VLE clickstream) don't exist in local gradebooks, so it cannot serve local
courses. It remains a research benchmark — see analytics/ml/{oulad,train,
service}.py and the validation chapters in the docs.
"""
from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from analytics.ml.grade_service import GradeService
from analytics.serializers import GradePredictRequestSerializer


@api_view(["GET"])
def health(request):
    """Liveness + model status, handy during development."""
    return Response(
        {
            "status": "ok",
            "grade_regressor": GradeService.info(),
            "note": ("OULAD risk classifier retired from serving (research "
                     "benchmark only); see docs."),
        }
    )


@api_view(["POST"])
def predict_grade(request):
    """Project a student's outcomes from leakage-free EARLY features.

    Body (all optional, fractions in [0, 1]; local real-data model):
        {"early_lab_avg": 0.7, "early_assignment_pct": 0.8, "early_quiz_avg": 0.4}

    Returns:
      * predicted_course_total (0-100) — the official course total (this
        course has no final exam), with an 80% interval, P(total<60/70),
        risk band, and data_coverage honesty flags;
      * exam_head.predicted_exam_avg — strictly-future Midterm I+II average
        (zero input overlap).
    """
    if not GradeService.is_loaded():
        return Response(
            {"detail": "Grade model not available. Run "
                       "`python -m analytics.ml.train_real --save`."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    serializer = GradePredictRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    return Response(GradeService.predict(serializer.validated_data))


@api_view(["GET"])
def cohort_profile(request):
    """Full cohort analysis for the dashboard (retrospective view).

    Returns class stats, outcome tiers on two bases (final / projected),
    multi-label weakness boards per dimension, and per-student detail.

    Query params:
      clusters  include the exploratory archetype clustering (research lens)
      k         number of archetypes when clusters is requested (default 4)
      refresh   recompute instead of serving the cached result
    """
    from analytics.ml.cohort_service import CohortProfileService

    k = request.query_params.get("k")
    try:
        data = CohortProfileService.get(
            k=int(k) if k else None,
            refresh=request.query_params.get("refresh") is not None,
            include_clusters=request.query_params.get("clusters") is not None,
        )
    except FileNotFoundError as exc:
        return Response(
            {"detail": f"Data or model not ready: {exc}"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return Response(data)


@api_view(["GET"])
def assessment_quality(request):
    """CTT item analysis of the course's own assessments (difficulty,
    discrimination, ceiling rate) — decision support for course design.
    Query params: refresh."""
    from analytics.ml.assessment_quality import AssessmentQualityService

    try:
        data = AssessmentQualityService.get(
            refresh=request.query_params.get("refresh") is not None)
    except FileNotFoundError as exc:
        return Response({"detail": f"Data not ready: {exc}"},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response(data)


@api_view(["GET"])
def warning_timeline(request):
    """Week-N snapshot models: warning-time curve + per-student LOSO
    prediction trajectories + declining-student alerts.
    Query params: refresh."""
    from analytics.ml.snapshots import TimelineService

    try:
        data = TimelineService.get(
            refresh=request.query_params.get("refresh") is not None)
    except FileNotFoundError as exc:
        return Response({"detail": f"Data not ready: {exc}"},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response(data)


def dashboard(request):
    """Instructor dashboard: drill-down tiers + weakness boards + timeline."""
    return render(request, "analytics/dashboard.html")
