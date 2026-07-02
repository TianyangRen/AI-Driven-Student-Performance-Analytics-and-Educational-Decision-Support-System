"""API routes for the analytics app."""
from django.urls import path

from analytics import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("predict-grade/", views.predict_grade, name="predict-grade"),
    path("cohort-profile/", views.cohort_profile, name="cohort-profile"),
    path("assessment-quality/", views.assessment_quality, name="assessment-quality"),
    path("warning-timeline/", views.warning_timeline, name="warning-timeline"),
]
