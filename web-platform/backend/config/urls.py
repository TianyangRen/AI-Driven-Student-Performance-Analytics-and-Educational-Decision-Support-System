from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def health(_request):
    # 顺带报告 ML 集成状态（mock / real），方便排查"模型为什么没接进来"
    from apps.predictions.services import ml_status
    return JsonResponse({
        "status": "ok", "db": "ok", "model_dir": "ok", "version": "1.1.0",
        "ml": ml_status(),
    })


api_v1 = [
    path("health", health),
    path("auth/", include("apps.accounts.urls")),
    path("", include("apps.courses.urls")),
    path("", include("apps.imports_app.urls")),
    path("", include("apps.analytics.urls")),
    path("", include("apps.predictions.urls")),
    path("", include("apps.reports_app.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
]
