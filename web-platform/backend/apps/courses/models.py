from django.conf import settings
from django.db import models


class Course(models.Model):
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=200)
    term = models.CharField(max_length=30)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_courses")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "course"
        unique_together = [("code", "term", "owner")]


class CourseSection(models.Model):
    STATUS_CHOICES = [("ACTIVE", "ACTIVE"), ("ARCHIVED", "ARCHIVED"), ("HIDDEN", "HIDDEN")]
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="sections")
    section_code = models.CharField(max_length=40)
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="taught_sections")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ACTIVE")

    class Meta:
        db_table = "course_section"
        unique_together = [("course", "section_code")]


class Student(models.Model):
    student_no = models.CharField(max_length=50, unique=True)
    full_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.CharField(max_length=120, blank=True, null=True)
    anonymized_code = models.CharField(max_length=64, unique=True)

    class Meta:
        db_table = "student"


class Enrollment(models.Model):
    STATUS_CHOICES = [("ACTIVE", "ACTIVE"), ("DROPPED", "DROPPED"), ("COMPLETED", "COMPLETED")]
    section = models.ForeignKey(CourseSection, on_delete=models.CASCADE, related_name="enrollments")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="enrollments")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ACTIVE")

    class Meta:
        db_table = "enrollment"
        unique_together = [("section", "student")]


class Assessment(models.Model):
    TYPE_CHOICES = [("QUIZ", "QUIZ"), ("LAB", "LAB"), ("ASSIGNMENT", "ASSIGNMENT"),
                    ("MIDTERM", "MIDTERM"), ("FINAL", "FINAL"), ("PARTICIPATION", "PARTICIPATION")]
    section = models.ForeignKey(CourseSection, on_delete=models.CASCADE, related_name="assessments")
    name = models.CharField(max_length=150)
    type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    max_score = models.DecimalField(max_digits=8, decimal_places=2)
    weight = models.DecimalField(max_digits=5, decimal_places=2)
    week_no = models.SmallIntegerField(null=True, blank=True)

    class Meta:
        db_table = "assessment"
        indexes = [models.Index(fields=["section", "type", "week_no"])]


class AssessmentScore(models.Model):
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="scores")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="scores")
    score = models.DecimalField(max_digits=8, decimal_places=2)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    submission_status = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        db_table = "assessment_score"
        unique_together = [("assessment", "student")]


class StudentActivity(models.Model):
    TYPE_CHOICES = [("ATTENDANCE", "ATTENDANCE"), ("PARTICIPATION", "PARTICIPATION"),
                    ("LOGIN", "LOGIN"), ("OTHER", "OTHER")]
    section = models.ForeignKey(CourseSection, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    activity_date = models.DateField()
    activity_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    metric_value = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "student_activity"
        indexes = [models.Index(fields=["section", "student", "activity_date"])]
