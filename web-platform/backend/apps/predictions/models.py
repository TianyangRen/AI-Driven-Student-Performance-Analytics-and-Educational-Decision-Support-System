from django.db import models
from django.db.models import Q

from apps.courses.models import CourseSection, Student


class ModelVersion(models.Model):
    ALGO_CHOICES = [("LOGISTIC_REGRESSION", "LOGISTIC_REGRESSION"),
                    ("RANDOM_FOREST", "RANDOM_FOREST"),
                    ("XGBOOST", "XGBOOST")]
    name = models.CharField(max_length=100)
    algorithm = models.CharField(max_length=50, choices=ALGO_CHOICES)
    feature_schema = models.JSONField()
    evaluation_metrics = models.JSONField(blank=True, null=True)
    artifact_path = models.CharField(max_length=500)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "model_version"
        constraints = [
            models.UniqueConstraint(
                fields=["is_active"], condition=Q(is_active=True), name="uq_model_version_active"
            )
        ]


class PredictionRun(models.Model):
    STATUS_CHOICES = [("PENDING", "PENDING"), ("RUNNING", "RUNNING"),
                      ("SUCCESS", "SUCCESS"), ("FAILED", "FAILED")]
    model_version = models.ForeignKey(ModelVersion, on_delete=models.PROTECT)
    section = models.ForeignKey(CourseSection, on_delete=models.CASCADE, related_name="prediction_runs")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    feature_snapshot_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "prediction_run"
        constraints = [
            models.UniqueConstraint(
                fields=["section"],
                condition=Q(status__in=["PENDING", "RUNNING"]),
                name="uq_prediction_run_active",
            )
        ]


class RiskPrediction(models.Model):
    LEVEL_CHOICES = [("LOW", "LOW"), ("MEDIUM", "MEDIUM"), ("HIGH", "HIGH")]
    run = models.ForeignKey(PredictionRun, on_delete=models.CASCADE, related_name="predictions")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="risk_predictions")
    probability = models.DecimalField(max_digits=5, decimal_places=4)
    risk_level = models.CharField(max_length=10, choices=LEVEL_CHOICES)
    top_factors = models.JSONField(blank=True, null=True)
    suggestion = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "risk_prediction"
        unique_together = [("run", "student")]
        indexes = [models.Index(fields=["student", "-created_at"])]
