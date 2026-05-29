"""Django admin registrations — gives you a free data-management UI."""
from django.contrib import admin

from analytics.models import Assessment, RiskPrediction, Student


class AssessmentInline(admin.TabularInline):
    model = Assessment
    extra = 0


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("student_id", "name", "group", "semester")
    search_fields = ("student_id", "name")
    list_filter = ("group", "semester")
    inlines = [AssessmentInline]


@admin.register(RiskPrediction)
class RiskPredictionAdmin(admin.ModelAdmin):
    list_display = ("student", "risk_level", "risk_score", "model_version", "created_at")
    list_filter = ("risk_level", "model_version")
    search_fields = ("student__student_id",)
