from django.urls import path
from . import views

urlpatterns = [
    path("sections/<int:section_id>/overview", views.overview),
    path("sections/<int:section_id>/students", views.students),
    path("sections/<int:section_id>/analytics/recalculate", views.recalculate),
    path("sections/<int:section_id>/analytics/distribution", views.distribution),
    path("sections/<int:section_id>/students/<int:student_id>/profile", views.student_profile),
    path("sections/<int:section_id>/students/<int:student_id>/indicators", views.student_indicators),
    path("analytics/comparisons", views.comparisons),
]
