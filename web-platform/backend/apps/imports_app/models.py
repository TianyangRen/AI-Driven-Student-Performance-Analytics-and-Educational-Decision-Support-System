from django.conf import settings
from django.db import models

from apps.courses.models import CourseSection


class ImportBatch(models.Model):
    TYPE_CHOICES = [("ROSTER", "ROSTER"), ("SCORE", "SCORE"), ("ACTIVITY", "ACTIVITY"), ("MIXED", "MIXED")]
    STATUS_CHOICES = [("UPLOADED", "UPLOADED"), ("VALIDATING", "VALIDATING"),
                      ("SUCCESS", "SUCCESS"), ("PARTIAL", "PARTIAL"), ("FAILED", "FAILED")]

    section = models.ForeignKey(CourseSection, on_delete=models.CASCADE, related_name="import_batches")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    file_name = models.CharField(max_length=255)
    import_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="UPLOADED")
    total_rows = models.IntegerField(default=0)
    valid_rows = models.IntegerField(default=0)
    error_details = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "import_batch"
        indexes = [models.Index(fields=["section", "-created_at"]), models.Index(fields=["status"])]
