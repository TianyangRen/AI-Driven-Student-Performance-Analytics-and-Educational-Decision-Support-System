"""
导入模板的【单一 schema 源】。

模板下载（views.download_template）与逐行校验（services.process_import）都从这里
读取列定义，保证「模板长什么样」与「按什么标准校验」永远一致，不会漂移。

每个 Column：
  name       -- 列头（也是解析后 dict 的键）
  required   -- 是否必填
  type       -- "str" | "int" | "decimal" | "date" | "enum" | "email"
  example    -- 模板示例行里的取值
  choices    -- 当 type == "enum" 时的可选值集合
  min_value  -- int/decimal 类型的下界（含）；None 表示不限
  max_value  -- int/decimal 类型的上界（含）；None 表示不限
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
    min_value: Optional[float] = field(default=None)
    max_value: Optional[float] = field(default=None)


ASSESSMENT_TYPES = ["QUIZ", "LAB", "ASSIGNMENT", "MIDTERM", "FINAL", "PARTICIPATION"]
ACTIVITY_TYPES = ["ATTENDANCE", "PARTICIPATION", "LOGIN", "OTHER"]

# 教学周合理上限（与 predictions 的 cutoff 校验保持一致）。
MAX_WEEK_NO = 53


TEMPLATES = {
    "ROSTER": [
        Column("student_no", True, "str", "S-001"),
        Column("full_name", False, "str", "Alice Wang"),
        Column("email", False, "email", "alice@example.com"),
    ],
    "SCORE": [
        Column("student_no", True, "str", "S-001"),
        Column("assessment_name", True, "str", "Quiz 1"),
        Column("assessment_type", True, "enum", "QUIZ", ASSESSMENT_TYPES),
        # max_score 须为正（另有跨列规则再校验 score<=max_score）
        Column("max_score", True, "decimal", "100", min_value=0, max_value=10000),
        # weight：相对权重，非负（0 会在聚合层退化为等权），封顶防误填
        Column("weight", True, "decimal", "5", min_value=0, max_value=1000),
        Column("week_no", False, "int", "1", min_value=1, max_value=MAX_WEEK_NO),
        Column("score", True, "decimal", "82", min_value=0, max_value=10000),
    ],
    "ACTIVITY": [
        Column("student_no", True, "str", "S-001"),
        Column("activity_date", True, "date", "2026-06-15"),
        Column("activity_type", True, "enum", "ATTENDANCE", ACTIVITY_TYPES),
        # metric_value 口径随 activity_type 变（出勤 0-100 / 参与 0-4 / 登录次数…），
        # 只强制非负，上界给足以覆盖登录计数等场景
        Column("metric_value", True, "decimal", "1", min_value=0, max_value=100000),
    ],
}

TEMPLATE_TYPES = list(TEMPLATES.keys())


def columns_for(import_type: str) -> List[Column]:
    return TEMPLATES[import_type]


def header_for(import_type: str) -> List[str]:
    return [c.name for c in TEMPLATES[import_type]]


def example_row_for(import_type: str) -> List[str]:
    return [c.example for c in TEMPLATES[import_type]]
