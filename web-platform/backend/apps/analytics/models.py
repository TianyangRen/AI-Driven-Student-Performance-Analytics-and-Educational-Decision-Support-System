from django.db import models

from apps.courses.models import CourseSection, Student


class MetricSnapshot(models.Model):
    TYPE_CHOICES = [("CLASS", "CLASS"), ("STUDENT", "STUDENT"),
                    ("ASSESSMENT", "ASSESSMENT"), ("GROUP", "GROUP")]
    section = models.ForeignKey(CourseSection, on_delete=models.CASCADE, related_name="snapshots")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, null=True, blank=True, related_name="snapshots")
    snapshot_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    calculated_at = models.DateTimeField(auto_now_add=True)
    metrics = models.JSONField()

    class Meta:
        db_table = "metric_snapshot"
        indexes = [
            models.Index(fields=["section", "snapshot_type", "-calculated_at"]),
            models.Index(fields=["student", "-calculated_at"]),
        ]
