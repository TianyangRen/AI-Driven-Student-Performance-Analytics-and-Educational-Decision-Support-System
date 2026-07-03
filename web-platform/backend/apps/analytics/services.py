"""分析聚合层 —— 从 DB 真实成绩/活动/预测计算班级与学生指标。

被 analytics 的 overview / students / distribution / student_profile / comparisons
视图共用。所有"分数"口径统一为 AssessmentScore.percentage(0–100)按考核权重加权。
风险等级来自该 section 最近一次成功的 PredictionRun（见 apps/predictions）。
"""
from __future__ import annotations

from collections import defaultdict
from statistics import mean, median, pstdev
from typing import Dict, List

from django.db.models import Avg

from apps.courses.models import (
    AssessmentScore,
    CourseSection,
    Enrollment,
    StudentActivity,
)
from apps.predictions.models import PredictionRun, RiskPrediction

PASS_MARK = 60.0
# 分数分布分桶：[lo, hi) ，最后一档含 100
_BUCKETS = [(0, 60, "0-59"), (60, 70, "60-69"), (70, 80, "70-79"),
            (80, 90, "80-89"), (90, 101, "90-100")]
# 考核类型展示顺序（comparisons 的坐标轴/系列用）
_TYPE_ORDER = ["LAB", "QUIZ", "ASSIGNMENT", "MIDTERM", "FINAL", "PARTICIPATION"]


# ------------------------------------------------------------------ #
# 权限范围 / 选课
# ------------------------------------------------------------------ #
def scoped_sections(user):
    """ADMIN / 超级用户看全部 section，普通教师只看自己名下（与 dashboard 一致）。"""
    qs = CourseSection.objects.select_related("course")
    return qs.all() if user.is_admin else qs.filter(instructor=user)


def active_student_ids(section) -> List[int]:
    return list(
        Enrollment.objects.filter(section=section, status="ACTIVE")
        .values_list("student_id", flat=True)
    )


# ------------------------------------------------------------------ #
# 分数聚合
# ------------------------------------------------------------------ #
def student_scores(section, student_ids=None) -> Dict[int, float]:
    """{student_id: 加权平均得分率 0–100}，按 Assessment.weight 加权。

    只统计有成绩记录的学生；权重缺失/为 0 时退化为等权。
    """
    qs = AssessmentScore.objects.filter(assessment__section=section)
    if student_ids is not None:
        qs = qs.filter(student_id__in=student_ids)
    acc: Dict[int, List[float]] = {}
    for sid, pct, weight in qs.values_list(
        "student_id", "percentage", "assessment__weight"
    ):
        pct = float(pct)
        w = float(weight) if weight and float(weight) > 0 else 1.0
        a = acc.setdefault(sid, [0.0, 0.0])
        a[0] += pct * w
        a[1] += w
    return {sid: v[0] / v[1] for sid, v in acc.items() if v[1]}


def score_distribution(scores: List[float]) -> List[dict]:
    return [
        {"range": label, "count": sum(1 for v in scores if lo <= v < hi)}
        for lo, hi, label in _BUCKETS
    ]


def weekly_trend(section) -> List[dict]:
    """班级每周平均得分率（按 assessment.week_no 分组）。"""
    rows = (
        AssessmentScore.objects.filter(
            assessment__section=section, assessment__week_no__isnull=False
        )
        .values("assessment__week_no")
        .annotate(avg=Avg("percentage"))
        .order_by("assessment__week_no")
    )
    return [{"week": r["assessment__week_no"], "average": round(float(r["avg"]), 1)}
            for r in rows]


def student_weekly_trend(section, student) -> List[dict]:
    """单个学生每周平均得分率。"""
    rows = (
        AssessmentScore.objects.filter(
            assessment__section=section, student=student,
            assessment__week_no__isnull=False,
        )
        .values("assessment__week_no")
        .annotate(avg=Avg("percentage"))
        .order_by("assessment__week_no")
    )
    return [{"week": r["assessment__week_no"], "score": round(float(r["avg"]), 1)}
            for r in rows]


# ------------------------------------------------------------------ #
# 活动（出勤 / 参与）
# ------------------------------------------------------------------ #
def attendance_rates(section, student_ids) -> Dict[int, float]:
    """{student_id: 出勤率 0–1}。metric_value 若为 0–100 的百分数自动归一。"""
    rows = (
        StudentActivity.objects.filter(
            section=section, activity_type="ATTENDANCE", student_id__in=student_ids
        )
        .values("student_id")
        .annotate(avg=Avg("metric_value"))
    )
    out = {}
    for r in rows:
        v = float(r["avg"])
        out[r["student_id"]] = round(v / 100.0 if v > 1 else v, 2)
    return out


def _participation_norm(section, student) -> float | None:
    """参与度归一到 0–1（按 0–4 量表封顶）。无数据返回 None。"""
    vals = [
        float(v)
        for v in StudentActivity.objects.filter(
            section=section, student=student, activity_type="PARTICIPATION"
        ).values_list("metric_value", flat=True)
    ]
    if not vals:
        return None
    return round(min(1.0, (sum(vals) / len(vals)) / 4.0), 2)


# ------------------------------------------------------------------ #
# 风险（来自最近一次成功预测运行）
# ------------------------------------------------------------------ #
def latest_success_run(section):
    return (
        PredictionRun.objects.filter(section=section, status="SUCCESS")
        .order_by("-created_at").first()
    )


def risk_by_student(section):
    """({student_id: {level, probability}}, run)；无成功运行时返回 ({}, None)。"""
    run = latest_success_run(section)
    if run is None:
        return {}, None
    m = {
        rp.student_id: {
            "level": rp.risk_level,
            "probability": float(rp.probability),
            "prediction_id": rp.id,
        }
        for rp in RiskPrediction.objects.filter(run=run)
    }
    return m, run


def risk_summary(section, student_ids) -> Dict[str, int]:
    """{high, medium, low} 计数；无预测的学生按 low 计（保证总数=学生数）。"""
    rmap, _ = risk_by_student(section)
    out = {"high": 0, "medium": 0, "low": 0}
    for sid in student_ids:
        level = (rmap.get(sid) or {}).get("level", "LOW").lower()
        out[level] = out.get(level, 0) + 1
    return out


# ------------------------------------------------------------------ #
# 学生多维指标（雷达图）
# ------------------------------------------------------------------ #
def student_indicators(section, student, percentages: List[float]) -> Dict[str, float]:
    """mastery/stability/engagement/improvement，取值区间与前端雷达图一致。"""
    mastery = round(mean(percentages) / 100.0, 2) if percentages else 0.0
    # stability：得分越稳定越高（1 - 归一化标准差）
    sd = pstdev(percentages) / 100.0 if len(percentages) > 1 else 0.0
    stability = round(max(0.0, 1.0 - sd), 2)
    # engagement：出勤率与参与度的均值
    att = attendance_rates(section, [student.id]).get(student.id)
    part = _participation_norm(section, student)
    eng = [x for x in (att, part) if x is not None]
    engagement = round(sum(eng) / len(eng), 2) if eng else 0.0
    # improvement：首末周得分率变化（归一为比例），夹到前端雷达量程 [-0.3, 0.5]
    trend = student_weekly_trend(section, student)
    if len(trend) >= 2:
        improvement = max(-0.3, min(0.5, round((trend[-1]["score"] - trend[0]["score"]) / 100.0, 2)))
    else:
        improvement = 0.0
    return {"mastery": mastery, "stability": stability,
            "engagement": engagement, "improvement": improvement}


# ------------------------------------------------------------------ #
# 对比分析
# ------------------------------------------------------------------ #
def comparison(user, dimension: str) -> dict:
    """按维度对比各群体在各考核类型上的平均得分率。

    返回 {labels, series:[{name, data}]}，data 与 labels 对齐（buildGroupedBar 约定）。
      SECTION/COURSE/TERM：labels=考核类型，series=各 section/course/term
      ASSESSMENT_TYPE   ：labels=各 section，series=各考核类型
    """
    sections = list(scoped_sections(user))
    meta = {s.id: s for s in sections}
    rows = list(
        AssessmentScore.objects.filter(assessment__section__in=sections)
        .values("assessment__section_id", "assessment__type")
        .annotate(avg=Avg("percentage"))
    )
    types_present = [t for t in _TYPE_ORDER
                     if any(r["assessment__type"] == t for r in rows)]
    # 只保留有成绩的 section（避免把空 section 也画进去）
    sections_with_data = [s for s in sections
                          if any(r["assessment__section_id"] == s.id for r in rows)]

    if dimension == "ASSESSMENT_TYPE":
        labels = [f"{s.course.code}-{s.section_code}" for s in sections_with_data]
        idx = {(r["assessment__section_id"], r["assessment__type"]): float(r["avg"])
               for r in rows}
        series = [
            {"name": t.title(),
             "data": [round(idx.get((s.id, t), 0.0), 1) for s in sections_with_data]}
            for t in types_present
        ]
        return {"labels": labels, "series": series}

    def group_of(section) -> str:
        if dimension == "COURSE":
            return section.course.code
        if dimension == "TERM":
            return section.course.term
        return f"{section.course.code}-{section.section_code}"  # SECTION 默认

    bucket = defaultdict(lambda: defaultdict(list))  # group -> type -> [avg,...]
    for r in rows:
        g = group_of(meta[r["assessment__section_id"]])
        bucket[g][r["assessment__type"]].append(float(r["avg"]))

    labels = [t.title() for t in types_present]
    series = []
    for g in sorted(bucket):
        data = []
        for t in types_present:
            vals = bucket[g].get(t, [])
            data.append(round(sum(vals) / len(vals), 1) if vals else 0.0)
        series.append({"name": g, "data": data})
    return {"labels": labels, "series": series}
