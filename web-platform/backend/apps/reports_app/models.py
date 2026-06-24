from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.courses.models import CourseSection


def _default_expires_at():
    return timezone.now() + timedelta(days=7)


class ReportExport(models.Model):
    TYPE_CHOICES = [("CLASS_SUMMARY", "CLASS_SUMMARY"),
                    ("RISK_LIST", "RISK_LIST"),
                    ("COMPARISON", "COMPARISON")]
    STATUS_CHOICES = [("PENDING", "PENDING"), ("PROCESSING", "PROCESSING"),
                      ("SUCCESS", "SUCCESS"), ("FAILED", "FAILED"), ("EXPIRED", "EXPIRED")]

    section = models.ForeignKey(CourseSection, on_delete=models.CASCADE, related_name="reports", null=True)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    report_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    parameters = models.JSONField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    file_path = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=_default_expires_at)

    class Meta:
        db_table = "report_export"
        indexes = [models.Index(fields=["section", "-created_at"]), models.Index(fields=["status"])]
