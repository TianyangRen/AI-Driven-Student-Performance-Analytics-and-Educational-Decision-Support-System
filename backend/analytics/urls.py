"""API routes for the analytics app."""
from django.urls import path

from analytics import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("predict/", views.predict_risk, name="predict-risk"),
    path("predict-grade/", views.predict_grade, name="predict-grade"),
]
