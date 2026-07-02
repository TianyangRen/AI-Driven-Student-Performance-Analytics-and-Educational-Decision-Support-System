from django.urls import path
from . import views

urlpatterns = [
    path("imports/template", views.download_template),
    path("sections/<int:section_id>/imports", views.create_import),
    path("imports/<int:batch_id>", views.get_import),
    path("imports/<int:batch_id>/errors", views.import_errors),
]
