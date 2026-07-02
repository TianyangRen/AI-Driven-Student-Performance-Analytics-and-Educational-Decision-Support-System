"""
导入落库层：规范化行 -> 逐行校验 -> 合法行入库、非法行进错误报告。

对外只暴露 process_import(batch, parsed_rows, import_type)，由 views 调用。
落库语义：部分入库（PARTIAL）——合法行在一个事务内写入，非法行不写、
收集到 batch.error_details；据结果置 status。
"""
from decimal import Decimal, InvalidOperation
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction

from apps.courses.models import (
    Assessment,
    AssessmentScore,
    Enrollment,
    Student,
    StudentActivity,
)
from .templates import Column, columns_for


# --------------------------------------------------------------------- #
# 逐行校验：把字符串值按列类型转换，返回 (coerced_dict, [errors])
# --------------------------------------------------------------------- #
def _coerce_value(col: Column, raw: str) -> Tuple[Any, Optional[str]]:
    """返回 (值, 错误原因)。错误原因非 None 表示该格校验失败。"""
    val = (raw or "").strip()
    if val == "":
        if col.required:
            return None, "required"
        return None, None

    if col.type == "str":
        return val, None
    if col.type == "int":
        try:
            return int(val), None
        except ValueError:
            return None, "must be an integer"
    if col.type == "decimal":
        try:
            return Decimal(val), None
        except InvalidOperation:
            return None, "must be a number"
    if col.type == "date":
        try:
            return datetime.strptime(val, "%Y-%m-%d").date(), None
        except ValueError:
            return None, "must be a date (YYYY-MM-DD)"
    if col.type == "enum":
        if val not in (col.choices or []):
            return None, f"must be one of {', '.join(col.choices or [])}"
        return val, None
    return val, None


def _validate_row(row_no: int, values: Dict[str, str], columns: List[Column]
                  ) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    coerced: Dict[str, Any] = {}
    errors: List[Dict[str, Any]] = []
    for col in columns:
        value, reason = _coerce_value(col, values.get(col.name, ""))
        if reason:
            errors.append({"row": row_no, "column": col.name,
                           "value": values.get(col.name, ""), "reason": reason})
        else:
            coerced[col.name] = value

    # 跨列业务规则：SCORE 的 score 不能超过 max_score
    if not errors and "max_score" in coerced and "score" in coerced:
        if coerced["max_score"] is not None and coerced["max_score"] <= 0:
            errors.append({"row": row_no, "column": "max_score",
                           "value": values.get("max_score", ""), "reason": "must be greater than 0"})
        elif coerced["score"] is not None and coerced["score"] > coerced["max_score"]:
            errors.append({"row": row_no, "column": "score",
                           "value": values.get("score", ""), "reason": "score exceeds max_score"})

    if errors:
        return None, errors
    return coerced, []


# --------------------------------------------------------------------- #
# anonymized_code 顺序号分配器：S-ANON-001 风格，创建时分配、稳定不变
# --------------------------------------------------------------------- #
class _AnonAllocator:
    def __init__(self):
        self._n = Student.objects.count()

    def next(self) -> str:
        while True:
            self._n += 1
            code = f"S-ANON-{self._n:03d}"
            if not Student.objects.filter(anonymized_code=code).exists():
                return code


# --------------------------------------------------------------------- #
# 三种模板各自的落库 handler
# --------------------------------------------------------------------- #
def _persist_roster(section, data, ctx):
    student, created = Student.objects.get_or_create(
        student_no=data["student_no"],
        defaults={
            "full_name": data.get("full_name"),
            "email": data.get("email"),
            "anonymized_code": ctx["anon"].next(),
        },
    )
    if not created:
        # 已存在：补齐这次提供的姓名 / 邮箱
        changed = False
        if data.get("full_name") and student.full_name != data["full_name"]:
            student.full_name = data["full_name"]; changed = True
        if data.get("email") and student.email != data["email"]:
            student.email = data["email"]; changed = True
        if changed:
            student.save(update_fields=["full_name", "email"])
    Enrollment.objects.get_or_create(section=section, student=student)
    return None


def _persist_score(section, data, ctx):
    student = ctx["enrolled"].get(data["student_no"])
    if student is None:
        return "student_no not enrolled in this section (import ROSTER first)"
    assessment, _ = Assessment.objects.get_or_create(
        section=section,
        name=data["assessment_name"],
        defaults={
            "type": data["assessment_type"],
            "max_score": data["max_score"],
            "weight": data["weight"],
            "week_no": data.get("week_no"),
        },
    )
    percentage = (data["score"] / data["max_score"] * 100).quantize(Decimal("0.01"))
    AssessmentScore.objects.update_or_create(
        assessment=assessment,
        student=student,
        defaults={"score": data["score"], "percentage": percentage},
    )
    return None


def _persist_activity(section, data, ctx):
    student = ctx["enrolled"].get(data["student_no"])
    if student is None:
        return "student_no not enrolled in this section (import ROSTER first)"
    StudentActivity.objects.create(
        section=section,
        student=student,
        activity_date=data["activity_date"],
        activity_type=data["activity_type"],
        metric_value=data["metric_value"],
    )
    return None


_HANDLERS = {
    "ROSTER": _persist_roster,
    "SCORE": _persist_score,
    "ACTIVITY": _persist_activity,
}


# --------------------------------------------------------------------- #
# 入口
# --------------------------------------------------------------------- #
def process_import(batch, parsed_rows, import_type: str) -> None:
    """
    校验并落库，直接更新 batch 的 status / total_rows / valid_rows / error_details。
    """
    columns = columns_for(import_type)
    handler = _HANDLERS[import_type]
    section = batch.section

    total = len(parsed_rows)
    errors: List[Dict[str, Any]] = []
    valid: List[Tuple[int, Dict[str, Any]]] = []

    for row in parsed_rows:
        coerced, row_errors = _validate_row(row.row_no, row.values, columns)
        if row_errors:
            errors.extend(row_errors)
        else:
            valid.append((row.row_no, coerced))

    # 上下文：名单映射（SCORE/ACTIVITY 用）、匿名码分配器（ROSTER 用）
    enrolled = {
        e.student.student_no: e.student
        for e in Enrollment.objects.filter(section=section).select_related("student")
    }
    ctx = {"enrolled": enrolled, "anon": _AnonAllocator()}

    persisted = 0
    with transaction.atomic():
        for row_no, data in valid:
            reason = handler(section, data, ctx)
            if reason:
                errors.append({"row": row_no, "column": "student_no",
                               "value": data.get("student_no", ""), "reason": reason})
            else:
                persisted += 1
                # ROSTER 落库后同步刷新映射，后续行可引用（一般不需要，但更稳）
                if import_type == "ROSTER":
                    s = Student.objects.get(student_no=data["student_no"])
                    enrolled[s.student_no] = s

    if persisted == 0:
        batch.status = "FAILED"
    elif errors:
        batch.status = "PARTIAL"
    else:
        batch.status = "SUCCESS"
    batch.total_rows = total
    batch.valid_rows = persisted
    batch.error_details = errors
    batch.save(update_fields=["status", "total_rows", "valid_rows", "error_details"])
