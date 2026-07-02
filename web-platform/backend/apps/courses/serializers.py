from rest_framework import serializers
from .models import Course, CourseSection, Student, Enrollment, Assessment


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ["id", "code", "name", "term", "owner", "created_at"]
        read_only_fields = ["owner", "created_at"]


class CourseSectionSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source="course.code", read_only=True)
    course_name = serializers.CharField(source="course.name", read_only=True)

    class Meta:
        model = CourseSection
        fields = ["id", "course", "course_code", "course_name", "section_code", "instructor", "status"]
        read_only_fields = ["instructor"]  # 由 perform_create 自动设为当前用户


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ["id", "student_no", "full_name", "email", "anonymized_code"]


class AssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assessment
        fields = ["id", "section", "name", "type", "max_score", "weight", "week_no"]
