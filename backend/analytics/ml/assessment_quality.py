"""Assessment quality panel — Classical Test Theory (CTT) item analysis.

Analyzes the COURSE'S OWN assessment instruments, not the students: for every
component (Lab 1..10, Assignment 1..4, Quiz 1..5, Midterm parts, Project) it
computes

  * difficulty        mean score fraction (higher = easier)
  * discrimination    Pearson r between the item fraction and the final course
                      total (does scoring well on this item track scoring well
                      overall?)
  * ceiling_pct       share of students at >= 95% of the item's max points
  * verdict           good / weak / poor discriminator, or "ceiling"

Motivation: the data itself showed labs/assignments barely discriminate
(near-universal full marks). This panel quantifies that per item so the
instructor can redesign assessments — decision support for the COURSE, not
just the students. IRT would need item-level response data we don't have;
CTT is the appropriate tool at this granularity (documented choice).

Honesty note: discrimination uses the final total, of which each item is a
small part (labs ~0.4 pts, assignments ~5 pts of 100), so part-whole inflation
is negligible except for midterm parts (~10-20 pts) — disclosed in the output.

    python -m analytics.ml.assessment_quality
"""
from __future__ import annotations

import re

import numpy as np
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

MIN_N = 10          # skip items answered by fewer students
CEILING_FRAC = 0.95
GOOD_R, WEAK_R = 0.30, 0.15


def _normalized_label(meta: dict, quiz_rank: int | None) -> str | None:
    """Map a raw component name onto a cross-semester label."""
    name = meta["name"]
    if re.match(r"^Lab \d+$", name):
        return name
    if re.match(r"^Assignment \d+$", name):
        return name
    if quiz_rank is not None:
        return f"Quiz {quiz_rank}"          # covers both RLQ and Quiz naming
    m = re.match(r"^(Mid-Term Exam I{1,2}) \((Part I{1,2})\)$", name)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    if "Project" in name and "BONUS" not in name.upper():
        return "Final Project"
    if "Workshop" in name:
        return "Workshops"
    return None                              # totals, bonus, formula, misc


def _iter_components(df: pd.DataFrame):
    """Yield (meta, normalized_label) for every analyzable component column."""
    quizzes = []
    metas = []
    for col in df.columns:
        meta = _parse_grade_header(col)
        if not meta or "(Total)" in meta["name"]:
            continue
        meta["col"] = col
        cat = meta["category"]
        if cat in ("RLQs", "Quizzes", "Quiz"):
            meta["date"] = _extract_date(meta["name"])
            quizzes.append(meta)
        metas.append(meta)
    quizzes.sort(key=lambda m: (m["date"] is None, m["date"]))
    quiz_rank = {m["col"]: i + 1 for i, m in enumerate(quizzes)}
    for meta in metas:
        yield meta, _normalized_label(meta, quiz_rank.get(meta["col"]))


def _verdict(r: float | None, ceiling: float, spread: float) -> str:
    if spread < 1e-9:
        return "no variance"
    if ceiling >= 70:
        return "ceiling"
    if r is None:
        return "n/a"
    if r >= GOOD_R:
        return "good discriminator"
    if r >= WEAK_R:
        return "weak"
    return "poor"


def analyze() -> dict:
    rows = []
    for path in sorted(REAL_DATA_DIR.glob("Data-Part*.csv")):
        df = pd.read_csv(path)
        df = df[df.iloc[:, 0].notna()]
        final = _final_grade(df)
        for meta, label in _iter_components(df):
            if label is None:
                continue
            frac = (_to_num(df[meta["col"]]) / meta["max_points"]).clip(0, 1.5)
            ok = frac.notna() & final.notna()
            if ok.sum() < MIN_N:
                continue
            f, y = frac[ok], final[ok]
            r = float(np.corrcoef(f, y)[0, 1]) if f.std() > 1e-9 else None
            rows.append({
                "label": label,
                "category": _category_of(label),
                "offering": path.stem,
                "n": int(ok.sum()),
                "difficulty_pct": round(float(f.mean()) * 100, 1),
                "discrimination_r": None if r is None else round(r, 3),
                "ceiling_pct": round(float((f >= CEILING_FRAC).mean()) * 100, 1),
                "spread": float(f.std()),
            })

    detail = pd.DataFrame(rows)

    # ---- pool across offerings by normalized label ------------------------ #
    pooled = []
    for label, g in detail.groupby("label"):
        w = g["n"]
        rs = g["discrimination_r"].dropna()
        r = float(np.average(rs, weights=g.loc[rs.index, "n"])) if len(rs) else None
        ceiling = float(np.average(g["ceiling_pct"], weights=w))
        spread = float(np.average(g["spread"], weights=w))
        pooled.append({
            "label": label,
            "category": _category_of(label),
            "offerings": int(g["offering"].nunique()),
            "n": int(w.sum()),
            "difficulty_pct": round(float(np.average(g["difficulty_pct"], weights=w)), 1),
            "discrimination_r": None if r is None else round(r, 3),
            "ceiling_pct": round(ceiling, 1),
            "verdict": _verdict(r, ceiling, spread),
        })
    order = {"labs": 0, "assignments": 1, "quizzes": 2, "midterm": 3,
             "project": 4, "participation": 5}
    pooled.sort(key=lambda x: (order.get(x["category"], 9), x["label"]))

    # ---- category summary + auto insights --------------------------------- #
    cat_rows = []
    pf = pd.DataFrame(pooled)
    for cat, g in pf.groupby("category"):
        rs = g["discrimination_r"].dropna()
        cat_rows.append({
            "category": cat,
            "avg_discrimination_r": round(float(rs.mean()), 3) if len(rs) else None,
            "avg_ceiling_pct": round(float(g["ceiling_pct"].mean()), 1),
        })
    cat_rows.sort(key=lambda x: -(x["avg_discrimination_r"] or -1))

    good = pf[pf["verdict"] == "good discriminator"].nlargest(3, "discrimination_r")
    dead = pf[pf["verdict"].isin(["ceiling", "no variance"])]
    insights = []
    if len(good):
        insights.append("Best early signals: "
                        + ", ".join(f"{r.label} (r={r.discrimination_r})"
                                    for r in good.itertuples()))
    if len(dead):
        insights.append(f"{len(dead)} components are at ceiling / zero variance "
                        f"(mostly {dead['category'].mode()[0]}) — they measure "
                        f"compliance, not ability; consider pass/fail marking.")

    return {
        "meta": {
            "method": "Classical Test Theory item analysis (difficulty, "
                      "item-total discrimination, ceiling rate), pooled across "
                      "4 offerings by normalized component label.",
            "caveat": "Discrimination correlates each item with the final "
                      "course total; part-whole overlap is negligible for "
                      "small items but inflates midterm parts (~10-20% of the "
                      "total) — read midterm r as an upper bound. IRT is not "
                      "applicable (no item-level response data).",
        },
        "components": pooled,
        "category_summary": cat_rows,
        "insights": insights,
    }


def _category_of(label: str) -> str:
    if label.startswith("Lab"):
        return "labs"
    if label.startswith("Assignment"):
        return "assignments"
    if label.startswith("Quiz"):
        return "quizzes"
    if label.startswith("Mid-Term"):
        return "midterm"
    if label == "Final Project":
        return "project"
    return "participation"


class AssessmentQualityService:
    _cache: dict | None = None

    @classmethod
    def get(cls, refresh: bool = False) -> dict:
        if refresh or cls._cache is None:
            cls._cache = analyze()
        return cls._cache


def main():
    q = analyze()
    print(q["meta"]["method"], "\n")
    print(f"{'component':22s} {'sems':>4s} {'n':>4s} {'diff%':>6s} "
          f"{'discr r':>8s} {'ceil%':>6s}  verdict")
    for c in q["components"]:
        r = "  --" if c["discrimination_r"] is None else f"{c['discrimination_r']:+.3f}"
        print(f"{c['label']:22s} {c['offerings']:4d} {c['n']:4d} "
              f"{c['difficulty_pct']:6.1f} {r:>8s} {c['ceiling_pct']:6.1f}  {c['verdict']}")
    print("\ncategory summary:")
    for c in q["category_summary"]:
        print(f"  {c['category']:14s} avg r={c['avg_discrimination_r']}  "
              f"avg ceiling={c['avg_ceiling_pct']}%")
    print("\ninsights:")
    for i in q["insights"]:
        print("  *", i)


if __name__ == "__main__":
    main()
