import re
from decimal import Decimal

from rest_framework import serializers

from apps.imports_app.templates import MAX_WEEK_NO  # 单一来源：教学周上限
from .models import Course, CourseSection, Student, Enrollment, Assessment

# section_code / course code 只允许字母、数字与连字符（如 01 / L01 / COMP8567）；
# 拒绝 !@#$ 等符号，避免脏数据混入唯一键与展示。
SECTION_CODE_RE = re.compile(r"^[A-Z0-9-]+$")
COURSE_CODE_RE = re.compile(r"^[A-Z0-9-]+$")
# term 需要容纳空格（如 "Summer 2026" / "2025-2026"），额外放行空格与连字符，
# 但仍拒绝 !@#$ 等符号。
TERM_RE = re.compile(r"^[A-Za-z0-9 -]+$")


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ["id", "code", "name", "term", "owner", "created_at"]
        read_only_fields = ["owner", "created_at"]

    def validate_code(self, value):
        # 规范化为大写，避免 COMP8567 / comp8567 被 unique_together 当成两门课
        code = value.strip().upper()
        if not code:
            raise serializers.ValidationError("Course code cannot be empty")
        if not COURSE_CODE_RE.match(code):
            raise serializers.ValidationError(
                "Course code may only contain letters, digits and hyphens")
        return code

    def validate_term(self, value):
        term = value.strip()
        if not term:
            raise serializers.ValidationError("Term cannot be empty")
        if not TERM_RE.match(term):
            raise serializers.ValidationError(
                "Term may only contain letters, digits, spaces and hyphens")
        return term


class CourseSectionSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source="course.code", read_only=True)
    course_name = serializers.CharField(source="course.name", read_only=True)

    class Meta:
        model = CourseSection
        fields = ["id", "course", "course_code", "course_name", "section_code", "instructor", "status"]
        read_only_fields = ["instructor"]  # 由 perform_create 自动设为当前用户

    def get_fields(self):
        # 把 course 的可选范围收窄到当前用户名下：否则教师能把 section
        # 挂到别人的课程下（course 是可写外键、默认 queryset 为全表）。
        fields = super().get_fields()
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and not user.is_admin:
            fields["course"].queryset = Course.objects.filter(owner=user)
        return fields

    def validate_section_code(self, value):
        code = value.strip().upper()
        if not code:
            raise serializers.ValidationError("Section code cannot be empty")
        if not SECTION_CODE_RE.match(code):
            raise serializers.ValidationError(
                "Section code may only contain letters, digits and hyphens")
        return code


class StudentSerializer(serializers.ModelSerializer):
    # email 用 EmailField 校验格式（模型侧也已改为 EmailField）
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Student
        fields = ["id", "student_no", "full_name", "email", "anonymized_code"]


class AssessmentSerializer(serializers.ModelSerializer):
    # 与导入侧 (imports_app.templates) 的数值边界保持一致，防止未来接入
    # 可写端点时漏校验（负权重污染加权均分、week_no 越界等）。
    max_score = serializers.DecimalField(max_digits=8, decimal_places=2,
                                         min_value=Decimal("0"), max_value=Decimal("10000"))
    weight = serializers.DecimalField(max_digits=5, decimal_places=2,
                                      min_value=Decimal("0"), max_value=Decimal("1000"))
    week_no = serializers.IntegerField(min_value=1, max_value=MAX_WEEK_NO,
                                       required=False, allow_null=True)

    class Meta:
        model = Assessment
        fields = ["id", "section", "name", "type", "max_score", "weight", "week_no"]

    def validate_max_score(self, value):
        if value <= 0:
            raise serializers.ValidationError("must be greater than 0")
        return value
