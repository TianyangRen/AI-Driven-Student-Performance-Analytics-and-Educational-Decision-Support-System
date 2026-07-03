"""生成真实感演示数据：分层能力的学生 + 跨周考核 + 成绩/出勤/参与，并跑预测。

用法：
    python manage.py seed_demo                 # 所有 section，每班 24 生，并跑预测
    python manage.py seed_demo --students 30
    python manage.py seed_demo --sections 10 12
    python manage.py seed_demo --no-predict    # 只造数据不跑预测

幂等：每次运行会先清掉目标 section 的选课/考核/活动/预测，并删除上一批
演示学生（student_no 以 'DEMO-' 开头），再重新生成。真实导入的数据不受影响。
"""
from __future__ import annotations

import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.courses.models import (
    Assessment,
    AssessmentScore,
    CourseSection,
    Enrollment,
    Student,
    StudentActivity,
)

# 考核蓝图：(名称, 类型, 满分, 权重%, 周次)。权重合计 100。
BLUEPRINT = [
    ("Lab 1", "LAB", 20, 4, 2), ("Lab 2", "LAB", 20, 4, 3),
    ("Lab 3", "LAB", 20, 4, 4), ("Lab 4", "LAB", 20, 4, 5),
    ("Lab 5", "LAB", 20, 4, 7), ("Lab 6", "LAB", 20, 4, 9),
    ("Quiz 1", "QUIZ", 25, 4, 2), ("Quiz 2", "QUIZ", 25, 4, 4),
    ("Quiz 3", "QUIZ", 25, 4, 8), ("Quiz 4", "QUIZ", 25, 4, 10),
    ("Assignment 1", "ASSIGNMENT", 100, 10, 5),
    ("Assignment 2", "ASSIGNMENT", 100, 10, 10),
    ("Midterm", "MIDTERM", 100, 20, 7),
    ("Final", "FINAL", 100, 20, 13),
]

# 学生画像：(标签, 占比, 能力区间, 每周趋势斜率区间, 参与度区间)
ARCHETYPES = [
    ("top", 0.15, (85, 95), (0.0, 1.0), (0.90, 0.99)),
    ("solid", 0.38, (72, 85), (-0.5, 1.0), (0.80, 0.95)),
    ("average", 0.25, (60, 72), (-1.0, 0.8), (0.65, 0.88)),
    ("at_risk", 0.14, (50, 62), (-1.5, 0.3), (0.50, 0.75)),
    ("failing", 0.08, (38, 52), (-2.0, -0.2), (0.35, 0.60)),
]

# 让数据有区分度（否则各 section 各类考核都卡在 ~70，热力图一片同色）：
# 每个 section 一个「生源强弱」偏移（行有别），每类考核一个「难易」偏移（列有别）。
SECTION_BIAS_RANGE = (-10, 12)
TYPE_DIFFICULTY = {
    "LAB": 6, "QUIZ": 1, "ASSIGNMENT": 3, "MIDTERM": -5, "FINAL": -8,
}

ACTIVITY_WEEKS = list(range(1, 11))
_TERM_START = date(2025, 1, 6)


class Command(BaseCommand):
    help = "生成真实感演示数据并跑预测（幂等，仅影响 DEMO- 学生与目标 section）。"

    def add_arguments(self, parser):
        parser.add_argument("--students", type=int, default=24, help="每个 section 的学生数")
        parser.add_argument("--sections", type=int, nargs="*", help="目标 section id（默认全部）")
        parser.add_argument("--no-predict", action="store_true", help="不自动跑预测")
        parser.add_argument("--seed", type=int, default=42, help="随机种子（可复现）")

    def handle(self, *args, **opts):
        random.seed(opts["seed"])
        sections = self._target_sections(opts.get("sections"))
        if not sections:
            self.stderr.write("没有匹配的 section。")
            return

        self._clear_previous(sections)

        gid = 1
        for section in sections:
            bias = random.uniform(*SECTION_BIAS_RANGE)  # 该 section 的生源强弱
            gid = self._seed_section(section, opts["students"], gid, bias)
            self.stdout.write(self.style.SUCCESS(
                f"  section {section.id} {section.course.code}-{section.section_code}: "
                f"{opts['students']} 生 + {len(BLUEPRINT)} 考核 (生源偏移 {bias:+.0f})"
            ))

        if not opts["no_predict"]:
            self._run_predictions(sections)

        self.stdout.write(self.style.SUCCESS(
            f"完成：{len(sections)} 个 section，共 {gid - 1} 名演示学生。"
        ))

    # ------------------------------------------------------------------ #
    def _target_sections(self, ids):
        qs = CourseSection.objects.select_related("course").order_by("id")
        return list(qs.filter(id__in=ids) if ids else qs.all())

    def _clear_previous(self, sections):
        section_ids = [s.id for s in sections]
        from apps.predictions.models import PredictionRun

        PredictionRun.objects.filter(section_id__in=section_ids).delete()
        StudentActivity.objects.filter(section_id__in=section_ids).delete()
        Assessment.objects.filter(section_id__in=section_ids).delete()  # 级联删分数
        Enrollment.objects.filter(section_id__in=section_ids).delete()
        Student.objects.filter(student_no__startswith="DEMO-").delete()  # 级联清演示学生残留

    # ------------------------------------------------------------------ #
    @transaction.atomic
    def _seed_section(self, section, n_students, gid_start, section_bias=0.0):
        assessments = [
            Assessment.objects.create(
                section=section, name=name, type=atype,
                max_score=maxs, weight=weight, week_no=week,
            )
            for name, atype, maxs, weight, week in BLUEPRINT
        ]

        gid = gid_start
        scores, activities = [], []
        for archetype in self._student_archetypes(n_students):
            label, base_ability, slope, engagement = archetype
            ability = base_ability + section_bias  # 叠加该 section 生源强弱
            student = Student.objects.create(
                student_no=f"DEMO-{gid:05d}",
                full_name=f"Demo Student {gid}",
                anonymized_code=f"S-{gid:06d}",
            )
            Enrollment.objects.create(section=section, student=student, status="ACTIVE")

            for a in assessments:
                pct, status = self._score_for(a, ability, slope, label)
                scores.append(AssessmentScore(
                    assessment=a, student=student,
                    percentage=round(pct, 2),
                    score=round(pct / 100.0 * float(a.max_score), 2),
                    submission_status=status,
                ))
            activities.extend(self._activities_for(section, student, engagement))
            gid += 1

        AssessmentScore.objects.bulk_create(scores)
        StudentActivity.objects.bulk_create(activities)
        return gid

    def _student_archetypes(self, n):
        """按占比分配画像，返回每个学生的 (label, ability, slope, engagement)。"""
        out = []
        for label, share, ab_rng, sl_rng, eng_rng in ARCHETYPES:
            for _ in range(round(n * share)):
                out.append((
                    label,
                    random.uniform(*ab_rng),
                    random.uniform(*sl_rng),
                    random.uniform(*eng_rng),
                ))
        # 数量凑到 n（四舍五入误差用 average 画像补/截）
        while len(out) < n:
            out.append(("average", random.uniform(60, 72), random.uniform(-1, 0.8), random.uniform(0.65, 0.88)))
        random.shuffle(out)
        return out[:n]

    def _score_for(self, assessment, ability, slope, label):
        """按能力 + 周趋势 + 噪声算得分率；failing 学生早期偶尔缺交（0 分）。"""
        if label == "failing" and random.random() < 0.15:
            return 0.0, "MISSING"
        week_adj = slope * (assessment.week_no - 1)
        difficulty = TYPE_DIFFICULTY.get(assessment.type, 0)  # 该考核类型难易
        pct = ability + difficulty + week_adj + random.gauss(0, 6)
        pct = max(3.0, min(100.0, pct))
        status = "LATE" if (label in ("at_risk", "failing") and random.random() < 0.2) else "SUBMITTED"
        return pct, status

    def _activities_for(self, section, student, engagement):
        acts = []
        for wk in ACTIVITY_WEEKS:
            attended = 1 if random.random() < engagement else 0
            acts.append(StudentActivity(
                section=section, student=student,
                activity_date=_TERM_START + timedelta(weeks=wk - 1),
                activity_type="ATTENDANCE", metric_value=attended,
            ))
            part = max(0, min(4, round(random.gauss(engagement * 4, 0.8))))
            acts.append(StudentActivity(
                section=section, student=student,
                activity_date=_TERM_START + timedelta(weeks=wk - 1),
                activity_type="PARTICIPATION", metric_value=part,
            ))
        return acts

    # ------------------------------------------------------------------ #
    def _run_predictions(self, sections):
        from apps.predictions import services

        self.stdout.write("跑预测…")
        for section in sections:
            try:
                run = services.run_section_prediction(section)
                dist = {}
                for rp in run.predictions.all():
                    dist[rp.risk_level] = dist.get(rp.risk_level, 0) + 1
                self.stdout.write(
                    f"  section {section.id}: run={run.id} risk={dist}"
                )
            except Exception as exc:  # noqa: BLE001
                self.stderr.write(f"  section {section.id} 预测失败: {exc}")
