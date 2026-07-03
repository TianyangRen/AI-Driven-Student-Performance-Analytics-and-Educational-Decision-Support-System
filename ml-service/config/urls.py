"""Root URL configuration."""
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from analytics import views as analytics_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("analytics.urls")),
    path("dashboard/", analytics_views.dashboard, name="dashboard"),
    path("", RedirectView.as_view(url="/dashboard/", permanent=False)),
]
