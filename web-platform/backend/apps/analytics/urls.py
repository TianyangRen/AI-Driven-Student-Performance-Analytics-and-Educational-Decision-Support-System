from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/summary", views.dashboard_summary),
    path("sections/<int:section_id>/overview", views.overview),
    path("sections/<int:section_id>/students", views.students),
    path("sections/<int:section_id>/analytics/recalculate", views.recalculate),
    path("sections/<int:section_id>/analytics/distribution", views.distribution),
    path("sections/<int:section_id>/students/<int:student_id>/profile", views.student_profile),
    path("sections/<int:section_id>/students/<int:student_id>/indicators", views.student_indicators),
    path("analytics/comparisons", views.comparisons),
    # 透传组员 ML 服务(:8000) 的分析看板
    path("analytics/cohort-profile", views.cohort_profile),
    path("analytics/warning-timeline", views.warning_timeline),
    path("analytics/assessment-quality", views.assessment_quality),
]
