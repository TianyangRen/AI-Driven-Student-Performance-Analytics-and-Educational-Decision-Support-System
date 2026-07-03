"""Database models.

Simplified relational schema inspired by the OULAD seven-table structure:
a Student has many Assessment rows; risk predictions are stored per student
so the dashboard can show history.
"""
from django.db import models


class Student(models.Model):
    student_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    group = models.CharField(max_length=50, blank=True, default="")
    semester = models.CharField(max_length=20, blank=True, default="")

    def __str__(self):
        return f"{self.student_id} - {self.name}"


class Assessment(models.Model):
    class Type(models.TextChoices):
        QUIZ = "quiz", "Quiz"
        LAB = "lab", "Lab"
        ASSIGNMENT = "assignment", "Assignment"
        MIDTERM = "midterm", "Midterm"
        PARTICIPATION = "participation", "Participation"

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="assessments"
    )
    type = models.CharField(max_length=20, choices=Type.choices)
    score = models.FloatField()
    max_score = models.FloatField(default=100)
    week = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.student.student_id} {self.type} (wk{self.week}): {self.score}"


class RiskPrediction(models.Model):
    class Level(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="predictions"
    )
    risk_score = models.FloatField(help_text="Predicted probability of being at risk")
    risk_level = models.CharField(max_length=10, choices=Level.choices)
    model_version = models.CharField(max_length=50, default="unknown")
    explanation = models.JSONField(
        default=dict, blank=True, help_text="Per-feature contribution (SHAP)"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student.student_id}: {self.risk_level} ({self.risk_score:.2f})"
