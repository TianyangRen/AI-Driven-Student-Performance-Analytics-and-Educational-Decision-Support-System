"""Controlled simulation: does cohort normalization help when semesters
genuinely differ in difficulty?

Motivation. On the real data (Experiment 2 in the report) cohort
normalization did NOT help, because the four semesters had almost identical
difficulty (means 77.9-80.3). That left RQ2 inconclusive. This script settles
it with a *controlled* experiment on clearly-labelled SYNTHETIC difficulty.

Mechanism (transparent, not rigged).
  We add a per-semester difficulty offset beta_c to the ABSOLUTE early features
  and the ABSOLUTE final grade of every student in that semester. This
  simulates "that semester's assessments were harder/easier, so everyone scored
  lower/higher." Crucially:
    * within-cohort PERCENTILE (the cohort-referenced / NORM track) is invariant
      to such a shift -- the same students stay strong/weak;
    * ABSOLUTE scores (the RAW track) move, so the same number now means a
      different standing in different cohorts.

We then predict each student's within-cohort final STANDING (final percentile)
under leave-one-semester-out, comparing:
    RAW  features (absolute early scores)        vs
    NORM features (within-cohort percentile)     -> same target, same splits.

Two conditions:
    SIMILAR    beta = 0 for all (the real data as-is)
    DIVERGENT  beta differs per semester (simulated difficulty gap)

    cd ml-service
    python -m analytics.ml.simulate_normalization
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

warnings.filterwarnings("ignore")

try:
    from analytics.ml.real_data import harmonize_all
except ModuleNotFoundError:  # pragma: no cover
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from analytics.ml.real_data import harmonize_all

RAW_FEATURES = ["early_lab_avg", "early_assignment_pct", "early_quiz_avg"]
NORM_FEATURES = ["early_lab_avg_pctl", "early_assignment_pct_pctl", "early_quiz_avg_pctl"]

# Simulated per-semester difficulty offsets (grade points). Clearly synthetic.
DIVERGENT_OFFSETS = {
    "Data-Part1": 0.0,    # reference
    "Data-Part2": -15.0,  # a hard semester: everyone ~15 pts lower
    "Data-Part3": +10.0,  # an easy semester
    "Data-Part4": -7.0,
}


def _pipe():
    return Pipeline([
        ("impute", SimpleImputer(strategy="mean")),
        ("scale", StandardScaler()),
        ("model", Ridge(alpha=1.0)),
    ])


def apply_difficulty(df: pd.DataFrame, offsets: dict[str, float]) -> pd.DataFrame:
    """Shift ABSOLUTE early features + absolute final grade by a per-semester
    offset. NORM (percentile) features and final_pctl come straight from the
    real data and are difficulty-invariant by construction.
    """
    out = df.copy()
    beta = out["offering"].map(offsets).fillna(0.0)
    # early absolute features are fractions [0,1]; offset is on a 0-100 scale.
    for col in RAW_FEATURES:
        out[col] = (out[col] + beta / 100.0).clip(0, 1)
    out["final_grade_sim"] = (out["final_grade"] + beta).clip(0, 100)
    return out


def loso_eval(df, features, target):
    """Leave-one-semester-out Ridge; return (MAE, R2, Spearman) pooled."""
    X = df[features].to_numpy()
    y = df[target].to_numpy()
    groups = df["offering"].to_numpy()
    gkf = GroupKFold(n_splits=df["offering"].nunique())
    preds, trues = [], []
    for tr, te in gkf.split(X, y, groups):
        pipe = _pipe()
        pipe.fit(X[tr], y[tr])
        preds.extend(pipe.predict(X[te]))
        trues.extend(y[te])
    preds, trues = np.array(preds), np.array(trues)
    return (mean_absolute_error(trues, preds),
            r2_score(trues, preds),
            spearmanr(preds, trues).correlation)


def run_condition(name, df):
    print(f"\n{'='*64}\nCONDITION: {name}\n{'='*64}")
    # --- headline: predict within-cohort STANDING (percentile) ----------- #
    raw = loso_eval(df, RAW_FEATURES, "final_pctl")
    norm = loso_eval(df, NORM_FEATURES, "final_pctl")
    print("Predict within-cohort final STANDING (target = final_pctl):")
    print(f"  {'feature track':24s} {'MAE(pctl pts)':>14s} {'R2':>7s} {'Spearman':>9s}")
    print(f"  {'RAW  (absolute early)':24s} {raw[0]*100:14.1f} {raw[1]:7.3f} {raw[2]:9.3f}")
    print(f"  {'NORM (cohort pctile)':24s} {norm[0]*100:14.1f} {norm[1]:7.3f} {norm[2]:9.3f}")

    # --- supporting: predict ABSOLUTE grade with RAW features ------------ #
    abs_mae, abs_r2, _ = loso_eval(df, RAW_FEATURES, "final_grade_sim")
    print("Predict ABSOLUTE grade with RAW features (target = final_grade):")
    print(f"  {'RAW -> absolute':24s} MAE(grade pts) = {abs_mae:5.2f}  R2 = {abs_r2:6.3f}")
    return raw, norm, (abs_mae, abs_r2)


def main():
    df = harmonize_all()

    similar = apply_difficulty(df, {o: 0.0 for o in df["offering"].unique()})
    divergent = apply_difficulty(df, DIVERGENT_OFFSETS)

    print("Simulated difficulty offsets (grade points):")
    for k, v in DIVERGENT_OFFSETS.items():
        print(f"  {k}: {v:+.0f}")

    r_sim, n_sim, a_sim = run_condition("SIMILAR (real data, no offset)", similar)
    r_div, n_div, a_div = run_condition("DIVERGENT (simulated difficulty gap)", divergent)

    print(f"\n{'='*64}\nSUMMARY — standing prediction (Spearman, higher=better)\n{'='*64}")
    print(f"  {'':10s} {'RAW':>8s} {'NORM':>8s}")
    print(f"  {'SIMILAR':10s} {r_sim[2]:8.3f} {n_sim[2]:8.3f}")
    print(f"  {'DIVERGENT':10s} {r_div[2]:8.3f} {n_div[2]:8.3f}")
    print(f"\n  RAW degradation (SIMILAR -> DIVERGENT): "
          f"{r_sim[2]:.3f} -> {r_div[2]:.3f}  (drop {r_sim[2]-r_div[2]:+.3f})")
    print(f"  NORM degradation (SIMILAR -> DIVERGENT): "
          f"{n_sim[2]:.3f} -> {n_div[2]:.3f}  (drop {n_sim[2]-n_div[2]:+.3f})")
    print(f"\n  Absolute-grade MAE blows up under divergence: "
          f"{a_sim[0]:.2f} -> {a_div[0]:.2f} grade pts")


if __name__ == "__main__":
    main()
