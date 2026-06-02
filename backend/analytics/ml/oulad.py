"""OULAD dataset integration.

OULAD = Open University Learning Analytics Dataset (UK Open University),
hosted by the UCI ML Repository under CC BY 4.0. ~32k students, 7 related
CSV tables. We use it as the REAL training/benchmark dataset.

This module does two things:
  1. download_oulad()        -> fetch + unzip the 7 CSVs into data/oulad/
  2. load_oulad_features()   -> build the (features, label) table the model
                                trains on, using ONLY early-course data.

Run as a script to download and preview:
    python -m analytics.ml.oulad            # download (if missing) + summary
    python -m analytics.ml.oulad --no-download   # just build features from
                                                 # already-downloaded CSVs
"""
from __future__ import annotations

import argparse
import io
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

# data/oulad/ at the backend root (sibling of ml_models/)
DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "oulad"

# UCI static download (a single zip containing all 7 CSVs).
OULAD_URL = (
    "https://archive.ics.uci.edu/static/public/349/"
    "open+university+learning+analytics+dataset.zip"
)

# The CSV tables we actually use.
REQUIRED_FILES = [
    "studentInfo.csv",
    "studentVle.csv",
    "assessments.csv",
    "studentAssessment.csv",
]

# How many days from course start count as the "early" prediction window.
EARLY_WINDOW_DAYS = 28

# Keys that identify a single enrolment (one student in one course offering).
ENROLMENT_KEYS = ["code_module", "code_presentation", "id_student"]


# --------------------------------------------------------------------------- #
# 1. Download
# --------------------------------------------------------------------------- #
def is_downloaded() -> bool:
    return all((DATA_DIR / f).exists() for f in REQUIRED_FILES)


def download_oulad(force: bool = False) -> None:
    """Download and extract the OULAD zip into DATA_DIR."""
    if is_downloaded() and not force:
        print(f"OULAD already present in {DATA_DIR}")
        return

    import urllib.request

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading OULAD from {OULAD_URL}")
    print("(~85 MB zip, may take a few minutes the first time)")

    req = urllib.request.Request(OULAD_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        raw = resp.read()

    print(f"Downloaded {len(raw) / 1e6:.1f} MB, extracting...")
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        zf.extractall(DATA_DIR)
    print(f"Extracted to {DATA_DIR}")
    missing = [f for f in REQUIRED_FILES if not (DATA_DIR / f).exists()]
    if missing:
        raise FileNotFoundError(f"Expected files missing after extract: {missing}")


# --------------------------------------------------------------------------- #
# 2. Feature engineering
# --------------------------------------------------------------------------- #
def _engagement_features(cutoff: int) -> pd.DataFrame:
    """Aggregate early VLE clicks per enrolment.

    studentVle.csv is large (~430 MB), so we read it in chunks and keep only
    rows within the early window before aggregating.
    """
    path = DATA_DIR / "studentVle.csv"
    usecols = ENROLMENT_KEYS + ["date", "sum_click"]
    parts = []
    for chunk in pd.read_csv(path, usecols=usecols, chunksize=2_000_000):
        early = chunk[chunk["date"] < cutoff]
        if not early.empty:
            parts.append(early)
    vle = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=usecols)

    grouped = vle.groupby(ENROLMENT_KEYS)
    agg = grouped.agg(
        total_clicks=("sum_click", "sum"),
        active_days=("date", "nunique"),
    ).reset_index()
    agg["mean_clicks_per_day"] = (
        agg["total_clicks"] / agg["active_days"].replace(0, np.nan)
    ).fillna(0.0)
    return agg


def _early_score_features(cutoff: int) -> pd.DataFrame:
    """Mean score of assessments whose DEADLINE falls in the early window.

    Joining studentAssessment with assessments gives us each score plus the
    assessment's deadline date, so we can keep only early assessments.
    """
    assessments = pd.read_csv(DATA_DIR / "assessments.csv")
    student_assess = pd.read_csv(DATA_DIR / "studentAssessment.csv")

    # OULAD stores missing values as the string "?"; coerce to real numbers.
    assessments["date"] = pd.to_numeric(assessments["date"], errors="coerce")
    student_assess["score"] = pd.to_numeric(student_assess["score"], errors="coerce")

    merged = student_assess.merge(
        assessments[["id_assessment", "code_module", "code_presentation", "date"]],
        on="id_assessment",
        how="left",
    )
    # 'date' is the deadline; NaN for final exams -> exclude from early window.
    early = merged[merged["date"].notna() & (merged["date"] < cutoff)]
    early_score = (
        early.groupby(ENROLMENT_KEYS)["score"].mean().reset_index(name="early_avg_score")
    )
    return early_score


def load_oulad_features(cutoff: int = EARLY_WINDOW_DAYS) -> pd.DataFrame:
    """Build the training table: FEATURE_COLUMNS + TARGET_COLUMN, one row per
    enrolment.
    """
    if not is_downloaded():
        raise FileNotFoundError(
            f"OULAD CSVs not found in {DATA_DIR}. "
            f"Run `python -m analytics.ml.oulad` to download them first."
        )

    info = pd.read_csv(DATA_DIR / "studentInfo.csv")

    # Base table: one row per enrolment, with demographic-ish features + label.
    df = info[
        ENROLMENT_KEYS + ["num_of_prev_attempts", "studied_credits", "final_result"]
    ].copy()
    df = df.rename(columns={"num_of_prev_attempts": "num_prev_attempts"})

    # Label: Fail / Withdrawn -> at risk (1); Pass / Distinction -> not (0).
    df["at_risk"] = df["final_result"].isin(["Fail", "Withdrawn"]).astype(int)

    # Merge engagement + early score features.
    df = df.merge(_engagement_features(cutoff), on=ENROLMENT_KEYS, how="left")
    df = df.merge(_early_score_features(cutoff), on=ENROLMENT_KEYS, how="left")

    # Students with no early activity -> 0 clicks/days; no early score -> 0.
    fill = {
        "total_clicks": 0.0,
        "active_days": 0.0,
        "mean_clicks_per_day": 0.0,
        "early_avg_score": 0.0,
    }
    df = df.fillna(fill)

    from analytics.ml.features import FEATURE_COLUMNS, TARGET_COLUMN

    return df[FEATURE_COLUMNS + [TARGET_COLUMN]]


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main():
    parser = argparse.ArgumentParser(description="Download / inspect OULAD.")
    parser.add_argument("--no-download", action="store_true",
                        help="Skip download; just build features from local CSVs.")
    parser.add_argument("--cutoff", type=int, default=EARLY_WINDOW_DAYS,
                        help="Early-window length in days (default 28).")
    args = parser.parse_args()

    if not args.no_download:
        download_oulad()

    df = load_oulad_features(cutoff=args.cutoff)
    print("\n=== Feature table summary ===")
    print(f"rows (enrolments): {len(df)}")
    print(f"at-risk rate: {df['at_risk'].mean():.1%}")
    print("\nfeature stats:")
    print(df.describe().round(2).to_string())


if __name__ == "__main__":
    main()
