from django.urls import path
from . import views

urlpatterns = [
    path("reports", views.create_report),
    path("reports/<int:report_id>", views.get_report),
    path("reports/<int:report_id>/download", views.download_report),
]
