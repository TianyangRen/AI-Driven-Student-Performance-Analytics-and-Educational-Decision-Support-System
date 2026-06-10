"""Reproduce the normalization effect on REAL divergent cohorts (OULAD).

The controlled simulation (simulate_normalization.py) showed cohort
normalization helps when cohorts differ in difficulty -- but it used a synthetic
additive shift, so NORM's invariance was partly by construction.

OULAD gives us *real* divergent cohorts: each (code_module, code_presentation)
is a separate offering, and modules/presentations genuinely differ in difficulty
and pass rate. Here the difficulty differences are multifaceted and real, so a
NORM advantage is a genuine empirical result, not a definitional one.

Design (parallel to the local experiment):
  cohort      = (code_module, code_presentation)
  early feat  = first-28-day engagement (clicks, active days) + early score
  target      = within-cohort STANDING (percentile) on LATE assessments
                (late = due on/after day 28, so it never overlaps the early
                 features -> leakage-free)
  RAW track   = absolute early features
  NORM track  = within-cohort percentile of the same early features
  validation  = leave-cohorts-out (GroupKFold by cohort)

    cd backend
    python -m analytics.ml.oulad_normalization
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

try:
    from analytics.ml.oulad import (
        DATA_DIR, EARLY_WINDOW_DAYS, ENROLMENT_KEYS, _engagement_features,
        download_oulad, is_downloaded,
    )
except ModuleNotFoundError:  # pragma: no cover
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from analytics.ml.oulad import (
        DATA_DIR, EARLY_WINDOW_DAYS, ENROLMENT_KEYS, _engagement_features,
        download_oulad, is_downloaded,
    )

warnings.filterwarnings("ignore")

COHORT = ["code_module", "code_presentation"]
RAW_FEATURES = ["total_clicks", "active_days", "early_score"]
NORM_FEATURES = [f"{c}_pctl" for c in RAW_FEATURES]
MIN_COHORT_SIZE = 50  # need enough students for stable within-cohort percentiles


def _score_features(cutoff: int) -> pd.DataFrame:
    """Per-enrolment mean score for early (date<cutoff) and late (date>=cutoff)
    assessments. Late mean is the leakage-free target proxy.
    """
    assessments = pd.read_csv(DATA_DIR / "assessments.csv")
    sa = pd.read_csv(DATA_DIR / "studentAssessment.csv")
    assessments["date"] = pd.to_numeric(assessments["date"], errors="coerce")
    sa["score"] = pd.to_numeric(sa["score"], errors="coerce")

    merged = sa.merge(
        assessments[["id_assessment", "code_module", "code_presentation", "date"]],
        on="id_assessment", how="left",
    )
    merged = merged[merged["date"].notna()]
    early = merged[merged["date"] < cutoff]
    late = merged[merged["date"] >= cutoff]

    early_s = early.groupby(ENROLMENT_KEYS)["score"].mean().reset_index(name="early_score")
    late_s = late.groupby(ENROLMENT_KEYS)["score"].mean().reset_index(name="final_score")
    return early_s.merge(late_s, on=ENROLMENT_KEYS, how="outer")


def build_dataset(cutoff: int = EARLY_WINDOW_DAYS) -> pd.DataFrame:
    if not is_downloaded():
        download_oulad()

    eng = _engagement_features(cutoff)          # total_clicks, active_days, ...
    scores = _score_features(cutoff)            # early_score, final_score
    df = eng.merge(scores, on=ENROLMENT_KEYS, how="outer")

    # Need a target: keep students with a late-assessment score.
    df = df[df["final_score"].notna()].copy()
    df[["total_clicks", "active_days"]] = df[["total_clicks", "active_days"]].fillna(0)

    # Drop tiny cohorts (unstable percentiles).
    df["cohort"] = df["code_module"] + "-" + df["code_presentation"]
    sizes = df.groupby("cohort")["id_student"].transform("size")
    df = df[sizes >= MIN_COHORT_SIZE].copy()

    # Within-cohort percentiles: NORM features + target standing.
    g = df.groupby("cohort")
    for c in RAW_FEATURES:
        df[f"{c}_pctl"] = g[c].rank(pct=True)
    df["final_standing"] = g["final_score"].rank(pct=True)
    return df.reset_index(drop=True)


def _pipe():
    return Pipeline([
        ("impute", SimpleImputer(strategy="mean")),
        ("scale", StandardScaler()),
        ("model", Ridge(alpha=1.0)),
    ])


def loso_eval(df, features, target, n_splits=5):
    X = df[features].to_numpy()
    y = df[target].to_numpy()
    groups = df["cohort"].to_numpy()
    gkf = GroupKFold(n_splits=n_splits)
    preds, trues = [], []
    for tr, te in gkf.split(X, y, groups):
        pipe = _pipe()
        pipe.fit(X[tr], y[tr])
        preds.extend(pipe.predict(X[te]))
        trues.extend(y[te])
    preds, trues = np.array(preds), np.array(trues)
    return (mean_absolute_error(trues, preds), r2_score(trues, preds),
            spearmanr(preds, trues).correlation)


def main():
    print("Building OULAD cohort dataset (reads the 453 MB VLE file, ~1-2 min)...")
    df = build_dataset()
    n_cohorts = df["cohort"].nunique()
    print(f"\n{len(df)} students across {n_cohorts} real cohorts "
          f"(>= {MIN_COHORT_SIZE} students each).")

    # Show that cohorts really do differ in difficulty.
    diff = df.groupby("cohort")["final_score"].mean().round(1)
    print(f"Cohort late-score means range from {diff.min()} to {diff.max()} "
          f"(spread {diff.max()-diff.min():.1f} pts) — REAL difficulty divergence.")

    print("\n" + "=" * 64)
    print("Predict within-cohort final STANDING (target = final_standing)")
    print("leave-cohorts-out (GroupKFold by cohort)")
    print("=" * 64)
    raw = loso_eval(df, RAW_FEATURES, "final_standing")
    norm = loso_eval(df, NORM_FEATURES, "final_standing")
    print(f"  {'feature track':26s} {'MAE(pctl pts)':>14s} {'R2':>7s} {'Spearman':>9s}")
    print(f"  {'RAW  (absolute early)':26s} {raw[0]*100:14.1f} {raw[1]:7.3f} {raw[2]:9.3f}")
    print(f"  {'NORM (cohort percentile)':26s} {norm[0]*100:14.1f} {norm[1]:7.3f} {norm[2]:9.3f}")

    gain = norm[2] - raw[2]
    print(f"\n  NORM - RAW Spearman gain: {gain:+.3f}")
    print("  Supporting view — predict ABSOLUTE late score with RAW features:")
    abs_mae, abs_r2, _ = loso_eval(df, RAW_FEATURES, "final_score")
    print(f"    RAW -> absolute: MAE = {abs_mae:.2f} pts, R2 = {abs_r2:.3f}")

    print("\nInterpretation:")
    if gain > 0.01:
        print("  On REAL divergent cohorts, cohort-referenced (NORM) features")
        print("  transfer better than absolute (RAW) features — reproducing the")
        print("  simulated effect with genuine difficulty differences.")
    else:
        print("  NORM did not beat RAW here; report honestly and inspect cohorts.")


if __name__ == "__main__":
    main()
