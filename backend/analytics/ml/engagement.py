"""Disengagement detector — the BEHAVIOURAL risk track.

Motivation (verified on the data): the single failing student (final 33) did
not "score low" — they STOPPED SUBMITTING mid-course (15 of 26 components
missing/zero from late February on, Midterm II never taken). That failure
mode is behavioural, is invisible to grade regression (one example teaches a
model nothing), and — crucially — is directly observable without any ML.

Key inversion of the CTT finding: labs/assignments sit at ceiling, so they
cannot measure ability — but that makes them PERFECT attendance sensors:
anyone who submits gets ~full marks, so a zero/missing value almost certainly
means "did not submit".

Rule (deterministic, disclosed):
  a component "miss" = missing OR zero score, over labs / assignments /
  quizzes / midterm parts (bonus, project, workshops excluded);
  LATE miss = lab >= 6, assignment >= 3, quiz >= 4 (by due date), Midterm II.
  disengaged  <=>  late misses >= 2  OR  total misses >= 5.

Zeros are treated as non-submission proxies — defensible for ceiling
components and for exams (a true attempted-zero is rare); disclosed in meta.

    python -m analytics.ml.engagement
"""
from __future__ import annotations

import re

import pandas as pd

try:
    from analytics.ml.real_data import (
        REAL_DATA_DIR, _extract_date, _final_grade, _parse_grade_header, _to_num,
    )
except ModuleNotFoundError:  # pragma: no cover
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from analytics.ml.real_data import (
        REAL_DATA_DIR, _extract_date, _final_grade, _parse_grade_header, _to_num,
    )

LATE_LAB, LATE_ASSIGN, LATE_QUIZ = 6, 3, 4
DISENGAGE_LATE, DISENGAGE_TOTAL = 3, 5   # severe: red alert
GAPS_LATE, GAPS_TOTAL = 2, 3             # watch level

RULE = (f"miss = missing/zero component (labs, assignments, quizzes, midterm "
        f"parts); late = lab>={LATE_LAB}, assignment>={LATE_ASSIGN}, "
        f"quiz>={LATE_QUIZ}, Midterm II. disengaged = late>={DISENGAGE_LATE} "
        f"or total>={DISENGAGE_TOTAL}; gaps = late>={GAPS_LATE} or "
        f"total>={GAPS_TOTAL}.")


def _tag(total: int, late: int) -> str:
    if late >= DISENGAGE_LATE or total >= DISENGAGE_TOTAL:
        return "disengaged"
    if late >= GAPS_LATE or total >= GAPS_TOTAL:
        return "gaps"
    return "ok"


def _components(df: pd.DataFrame) -> list[tuple[bool, str]]:
    """[(is_late, column)] for every countable component in one offering."""
    out, quizzes = [], []
    for col in df.columns:
        meta = _parse_grade_header(col)
        if not meta or "(Total)" in meta["name"]:
            continue
        name = meta["name"]
        if m := re.match(r"^Lab (\d+)$", name):
            out.append((int(m.group(1)) >= LATE_LAB, col))
        elif m := re.match(r"^Assignment (\d+)$", name):
            out.append((int(m.group(1)) >= LATE_ASSIGN, col))
        elif meta["category"] in ("RLQs", "Quizzes", "Quiz"):
            quizzes.append((_extract_date(name) or pd.Timestamp.max, col))
        elif name.startswith("Mid-Term Exam II"):
            out.append((True, col))
        elif name.startswith("Mid-Term Exam I"):
            out.append((False, col))
    quizzes.sort(key=lambda x: x[0])
    out.extend((i + 1 >= LATE_QUIZ, col) for i, (_, col) in enumerate(quizzes))
    return out


def engagement_table() -> pd.DataFrame:
    """Per-student engagement stats across all offerings."""
    rows = []
    for path in sorted(REAL_DATA_DIR.glob("Data-Part*.csv")):
        df = pd.read_csv(path)
        df = df[df.iloc[:, 0].notna()]
        comps = _components(df)
        final = _final_grade(df)
        ids = df.iloc[:, 0].astype(str).str.lstrip("#").str.strip()
        vals = {col: _to_num(df[col]) for _, col in comps}
        for i in df.index:
            total = late = 0
            for is_late, col in comps:
                v = vals[col][i]
                if pd.isna(v) or v == 0:
                    total += 1
                    late += int(is_late)
            rows.append({
                "student_id": ids[i], "offering": path.stem,
                "missed_total": total, "missed_late": late,
                "engagement": _tag(total, late),
                "final_grade": final[i],
            })
    return pd.DataFrame(rows)


def main():
    t = engagement_table()
    print(RULE, "\n")
    for tag in ("disengaged", "gaps"):
        d = t[t["engagement"] == tag].sort_values("missed_late", ascending=False)
        print(f"{tag}: {len(d)} students "
              f"(mean final {d['final_grade'].mean():.1f})")
        for r in d.itertuples():
            print(f"  {r.student_id} ({r.offering.replace('Data-','')}): "
                  f"{r.missed_total} misses ({r.missed_late} late), "
                  f"final {r.final_grade:.0f}")
    ok = t[t["engagement"] == "ok"]
    print(f"\nok: {len(ok)} students (mean final {ok['final_grade'].mean():.1f})")


if __name__ == "__main__":
    main()
