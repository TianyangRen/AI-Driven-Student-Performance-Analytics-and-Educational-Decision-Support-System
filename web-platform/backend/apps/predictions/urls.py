from django.urls import path
from . import views

urlpatterns = [
    path("sections/<int:section_id>/predictions/run", views.run_prediction),
    path("sections/<int:section_id>/predictions", views.list_predictions),
    path("predictions/<int:prediction_id>/explanation", views.explanation),
]
