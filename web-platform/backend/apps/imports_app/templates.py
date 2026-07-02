"""
导入模板的【单一 schema 源】。

模板下载（views.download_template）与逐行校验（services.process_import）都从这里
读取列定义，保证「模板长什么样」与「按什么标准校验」永远一致，不会漂移。

每个 Column：
  name     -- 列头（也是解析后 dict 的键）
  required -- 是否必填
  type     -- "str" | "int" | "decimal" | "date" | "enum"
  example  -- 模板示例行里的取值
  choices  -- 当 type == "enum" 时的可选值集合
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class Column:
    name: str
    required: bool
    type: str
    example: str
    choices: Optional[List[str]] = field(default=None)


ASSESSMENT_TYPES = ["QUIZ", "LAB", "ASSIGNMENT", "MIDTERM", "FINAL", "PARTICIPATION"]
ACTIVITY_TYPES = ["ATTENDANCE", "PARTICIPATION", "LOGIN", "OTHER"]


TEMPLATES = {
    "ROSTER": [
        Column("student_no", True, "str", "S-001"),
        Column("full_name", False, "str", "Alice Wang"),
        Column("email", False, "str", "alice@example.com"),
    ],
    "SCORE": [
        Column("student_no", True, "str", "S-001"),
        Column("assessment_name", True, "str", "Quiz 1"),
        Column("assessment_type", True, "enum", "QUIZ", ASSESSMENT_TYPES),
        Column("max_score", True, "decimal", "100"),
        Column("weight", True, "decimal", "5"),
        Column("week_no", False, "int", "1"),
        Column("score", True, "decimal", "82"),
    ],
    "ACTIVITY": [
        Column("student_no", True, "str", "S-001"),
        Column("activity_date", True, "date", "2026-06-15"),
        Column("activity_type", True, "enum", "ATTENDANCE", ACTIVITY_TYPES),
        Column("metric_value", True, "decimal", "1"),
    ],
}

TEMPLATE_TYPES = list(TEMPLATES.keys())


def columns_for(import_type: str) -> List[Column]:
    return TEMPLATES[import_type]


def header_for(import_type: str) -> List[str]:
    return [c.name for c in TEMPLATES[import_type]]


def example_row_for(import_type: str) -> List[str]:
    return [c.example for c in TEMPLATES[import_type]]
