"""Real local gradebook (D2L/Brightspace export) parser & harmonizer.

The raw CSVs have messy headers like:
    Lab 1 Points Grade <Numeric MaxPoints:5 Category:Labs>
    Labs Subtotal Numerator , Labs Subtotal Denominator
    RLQ (Ch 1 - 21 Jan 2025) Points Grade <Numeric MaxPoints:7 Category:RLQs>
    Adjusted Final Grade Numerator , Adjusted Final Grade Denominator

Each file is ONE offering (semester) of the same course, and the four
offerings have DIFFERENT structures (RLQ vs Quiz, midterm grouping, ...).

This module harmonizes them into one tidy per-student table that cleanly
separates THREE kinds of column (critical to avoid data leakage):

  1. TARGET           final_grade            (Adjusted Final Grade, /100)
  2. EARLY features   early_*                leakage-free: only first-few-weeks
                                             component scores (first labs,
                                             assignment 1, first quizzes)
  3. ABSOLUTE / full  abs_*                  official per-category % from the
                                             Subtotal columns (criterion-
                                             referenced) -- for dashboard /
                                             analysis, NOT for early prediction
  4. RELATIVE         *_pctl                 within-offering percentile rank
                                             (cohort-referenced) -- comparable
                                             across semesters

Usage:
    python -m analytics.ml.real_data                # parse + summary + save
    python -m analytics.ml.real_data --no-save
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd

# real_data/ lives at the repo root (sibling of backend/)
REAL_DATA_DIR = Path(__file__).resolve().parents[3] / "real_data"
OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "real"

# Map each semester's raw category name onto a unified taxonomy.
CATEGORY_TAXONOMY = {
    "Labs": "labs",
    "Assignments": "assignments",
    "RLQs": "quizzes",
    "Quizzes": "quizzes",
    "Quiz": "quizzes",
    "Mid-Term Exam I": "midterm",
    "Mid-Term Exam II": "midterm",
    "Mid-Term Exams": "midterm",
    "Final Project": "project",
    "Seminars & Workshops": "participation",
    "Bonus": "bonus",
}

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "june": 6,
    "jul": 7, "july": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11,
    "dec": 12,
}


# --------------------------------------------------------------------------- #
# Header parsing
# --------------------------------------------------------------------------- #
def _parse_grade_header(col: str) -> dict | None:
    """Parse a '<name> Points Grade <Numeric MaxPoints:X Category:Y>' column.

    Returns dict(name, category, max_points) or None if it isn't a numeric
    component column (skips Formula columns, subtotals, indicators, ...).
    """
    m = re.match(r"^(.*?)\s+Points Grade\s+<Numeric\s+MaxPoints:([\d.]+)(?:\s+Category:(.+?))?>\s*$", col)
    if not m:
        return None
    name, max_points, category = m.group(1), float(m.group(2)), m.group(3)
    return {"name": name.strip(), "max_points": max_points,
            "category": (category or "").strip()}


def _extract_date(name: str) -> pd.Timestamp | None:
    """Pull a date like '21 Jan 2025' / '23 Sept 2025' / '9 June 2025' out of
    a component name. Returns None if there is no date.
    """
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\.?\s+(\d{4})", name)
    if not m:
        return None
    day, mon, year = int(m.group(1)), m.group(2).lower(), int(m.group(3))
    month = _MONTHS.get(mon)
    if not month:
        return None
    try:
        return pd.Timestamp(year=year, month=month, day=day)
    except ValueError:
        return None


def _to_num(series: pd.Series) -> pd.Series:
    """Coerce a gradebook column to numbers (blanks/'?' -> NaN)."""
    return pd.to_numeric(series, errors="coerce")


# --------------------------------------------------------------------------- #
# Per-offering processing
# --------------------------------------------------------------------------- #
def _absolute_category_pct(df: pd.DataFrame) -> dict[str, pd.Series]:
    """Official per-category % from '<Cat> Subtotal Numerator/Denominator'.

    These already encode each semester's own weights and drop-lowest rules,
    so we use them directly instead of re-aggregating raw component scores.
    Categories are merged into the unified taxonomy (e.g. Midterm I + II).
    """
    num_cols = [c for c in df.columns if c.endswith("Subtotal Numerator")]
    out_num: dict[str, pd.Series] = {}
    out_den: dict[str, pd.Series] = {}
    for ncol in num_cols:
        raw_cat = ncol[: -len(" Subtotal Numerator")].strip()
        dcol = f"{raw_cat} Subtotal Denominator"
        if dcol not in df.columns:
            continue
        unified = CATEGORY_TAXONOMY.get(raw_cat)
        if unified is None or unified == "bonus":
            continue
        n, d = _to_num(df[ncol]).fillna(0), _to_num(df[dcol]).fillna(0)
        out_num[unified] = out_num.get(unified, 0) + n
        out_den[unified] = out_den.get(unified, 0) + d

    pct = {}
    for cat in out_num:
        den = out_den[cat].replace(0, np.nan)
        pct[f"abs_{cat}"] = (out_num[cat] / den).clip(0, 1)
    return pct


def _early_features(df: pd.DataFrame) -> dict[str, pd.Series]:
    """Leakage-free early-term features from COMPONENT-level columns.

    Early set (exists in all four offerings):
      * first up to 4 labs           -> early_lab_avg, early_lab_completion
      * assignment 1                 -> early_assignment_pct
      * first up to 2 quizzes/RLQs   -> early_quiz_avg  (selected by date)
    Everything is normalised to a fraction of its own max points, so the
    different weighting schemes across semesters cancel out.
    """
    components = []
    for col in df.columns:
        meta = _parse_grade_header(col)
        if not meta:
            continue
        meta["col"] = col
        meta["date"] = _extract_date(meta["name"])
        meta["unified"] = CATEGORY_TAXONOMY.get(meta["category"])
        components.append(meta)

    out: dict[str, pd.Series] = {}
    n = len(df)

    # --- first 4 individual labs (Lab 1..Lab 4); labs carry no date -------
    labs = [c for c in components if re.match(r"^Lab \d+$", c["name"])]
    labs.sort(key=lambda c: int(re.match(r"^Lab (\d+)$", c["name"]).group(1)))
    early_labs = labs[:4]
    if early_labs:
        fracs = [( _to_num(df[c["col"]]) / c["max_points"] ) for c in early_labs]
        mat = pd.concat(fracs, axis=1)
        out["early_lab_avg"] = mat.mean(axis=1).clip(0, 1)
        # completion = fraction of the early labs actually submitted (non-NaN)
        out["early_lab_completion"] = mat.notna().mean(axis=1)
    else:
        out["early_lab_avg"] = pd.Series(np.nan, index=df.index)
        out["early_lab_completion"] = pd.Series(0.0, index=df.index)

    # --- assignment 1 -----------------------------------------------------
    a1 = [c for c in components if re.match(r"^Assignment 1$", c["name"])]
    if a1:
        out["early_assignment_pct"] = (_to_num(df[a1[0]["col"]]) / a1[0]["max_points"]).clip(0, 1)
    else:
        out["early_assignment_pct"] = pd.Series(np.nan, index=df.index)

    # --- first up to 2 quizzes/RLQs by date -------------------------------
    quizzes = [c for c in components
               if c["unified"] == "quizzes" and "(Total)" not in c["name"]]
    quizzes.sort(key=lambda c: (c["date"] is None, c["date"]))
    early_q = quizzes[:2]
    if early_q:
        fracs = [(_to_num(df[c["col"]]) / c["max_points"]) for c in early_q]
        out["early_quiz_avg"] = pd.concat(fracs, axis=1).mean(axis=1).clip(0, 1)
    else:
        out["early_quiz_avg"] = pd.Series(np.nan, index=df.index)

    return out


def _final_grade(df: pd.DataFrame) -> pd.Series:
    """Target: Adjusted Final Grade as a 0-100 score."""
    num = [c for c in df.columns if c.startswith("Adjusted Final Grade Numerator")]
    den = [c for c in df.columns if c.startswith("Adjusted Final Grade Denominator")]
    if not num or not den:
        raise ValueError("No Adjusted Final Grade columns found.")
    g = _to_num(df[num[0]]) / _to_num(df[den[0]]).replace(0, np.nan) * 100
    return g.clip(0, 100)


def load_offering(path: Path) -> pd.DataFrame:
    """Parse one semester CSV into a tidy per-student frame."""
    df = pd.read_csv(path)
    df = df[df.iloc[:, 0].notna()]  # drop blank trailing rows

    id_col = df.columns[0]  # OrgDefinedId
    out = pd.DataFrame({
        "student_id": df[id_col].astype(str).str.lstrip("#").str.strip(),
        "offering": path.stem,
    })
    out["final_grade"] = _final_grade(df).values
    for k, v in _early_features(df).items():
        out[k] = v.values
    for k, v in _absolute_category_pct(df).items():
        out[k] = v.values

    out = out[out["final_grade"].notna()].reset_index(drop=True)
    return out


# --------------------------------------------------------------------------- #
# Harmonize all offerings + dual-track normalisation
# --------------------------------------------------------------------------- #
def harmonize_all() -> pd.DataFrame:
    files = sorted(REAL_DATA_DIR.glob("Data-Part*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSVs found in {REAL_DATA_DIR}")
    df = pd.concat([load_offering(f) for f in files], ignore_index=True)

    # --- within-offering relative (cohort-referenced) track ----------------
    g = df.groupby("offering")
    df["final_pctl"] = g["final_grade"].rank(pct=True)          # 0..1 percentile
    df["final_z"] = g["final_grade"].transform(
        lambda s: (s - s.mean()) / s.std(ddof=0) if s.std(ddof=0) else 0.0
    )
    # percentile of each leakage-free early feature, within its cohort
    for col in ["early_lab_avg", "early_assignment_pct", "early_quiz_avg"]:
        df[f"{col}_pctl"] = g[col].rank(pct=True)

    # --- two risk labels (per the merged plan) -----------------------------
    df["at_risk_absolute"] = (df["final_grade"] < 70).astype(int)   # criterion
    df["at_risk_relative"] = (df["final_pctl"] <= 0.25).astype(int)  # bottom 25%

    return df


def save(df: pd.DataFrame) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "harmonized.csv"
    df.to_csv(out, index=False)
    return out


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="Parse & harmonize real gradebooks.")
    ap.add_argument("--no-save", action="store_true")
    args = ap.parse_args()

    df = harmonize_all()

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 50)
    print(f"Harmonized {len(df)} students across {df['offering'].nunique()} offerings\n")

    print("=== per-offering ===")
    summ = df.groupby("offering").agg(
        students=("student_id", "size"),
        final_mean=("final_grade", "mean"),
        final_std=("final_grade", "std"),
        final_min=("final_grade", "min"),
        abs_risk=("at_risk_absolute", "sum"),
        rel_risk=("at_risk_relative", "sum"),
    ).round(1)
    print(summ.to_string())

    print("\n=== leakage-free EARLY features (head) ===")
    early = ["student_id", "offering", "early_lab_avg", "early_lab_completion",
             "early_assignment_pct", "early_quiz_avg", "final_grade", "final_pctl"]
    print(df[early].head(8).round(3).to_string(index=False))

    print("\n=== absolute (criterion) category %, full-term — NOT for early pred ===")
    abscols = [c for c in df.columns if c.startswith("abs_")]
    print(df[["offering"] + abscols].groupby("offering").mean().round(3).to_string())

    print("\n=== correlation: early features vs final_grade (predictive signal?) ===")
    for c in ["early_lab_avg", "early_assignment_pct", "early_quiz_avg",
              "early_lab_completion"]:
        r = df[[c, "final_grade"]].corr().iloc[0, 1]
        print(f"  {c:24s} r = {r:.3f}")

    if not args.no_save:
        out = save(df)
        print(f"\nSaved -> {out}")


if __name__ == "__main__":
    main()
