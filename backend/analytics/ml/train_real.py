"""Early-grade REGRESSION on the real local gradebooks, with rigorous
cross-semester validation.

Predict a student's FINAL grade from leakage-free EARLY-term features
(first labs / assignment 1 / first quizzes). Regression is used instead of
risk-classification because the real data has almost no failing students
(only ~1 below 50), but every student carries a usable final score.

Two experiments:
  1. Viability + honesty:
       random K-fold  (optimistic)  vs
       leave-one-semester-out       (honest cross-cohort generalization)
  2. Normalization before/after:
       RAW absolute early features  vs
       cohort-referenced percentile early features
     -- same target, same validation, so MAE is directly comparable. This is
        the controlled experiment that shows whether cohort normalization
        improves cross-semester transfer.

    cd backend
    python -m analytics.ml.train_real
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold, KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

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
TARGET = "final_grade"

# Deployable model: RAW features (available for a single student without cohort
# context) predicting the absolute final grade. Ridge won every comparison.
GRADE_MODEL_VERSION = "ridge-grade-v1"


def make_pipeline(model):
    """Impute (train-only) -> scale -> model. Prevents leakage inside CV."""
    return Pipeline([
        ("impute", SimpleImputer(strategy="mean")),
        ("scale", StandardScaler()),
        ("model", model),
    ])


def _models():
    return {
        "Ridge": Ridge(alpha=1.0),
        "RandomForest": RandomForestRegressor(
            n_estimators=300, max_depth=4, random_state=42, n_jobs=-1
        ),
    }


def evaluate(df, features, splitter, groups=None):
    """Run CV with the given splitter; return {model: (MAE, RMSE, R2)}."""
    X = df[features].to_numpy()
    y = df[TARGET].to_numpy()
    results = {}
    for name, model in _models().items():
        maes, rmses, preds, trues = [], [], [], []
        split_args = (X, y, groups) if groups is not None else (X, y)
        for tr, te in splitter.split(*split_args):
            pipe = make_pipeline(_models()[name])
            pipe.fit(X[tr], y[tr])
            p = pipe.predict(X[te])
            maes.append(mean_absolute_error(y[te], p))
            rmses.append(np.sqrt(mean_squared_error(y[te], p)))
            preds.extend(p); trues.extend(y[te])
        results[name] = (
            float(np.mean(maes)),
            float(np.mean(rmses)),
            float(r2_score(trues, preds)),
        )
    return results


def _print_table(title, results):
    print(f"\n{title}")
    print(f"  {'model':14s} {'MAE':>7s} {'RMSE':>7s} {'R2':>7s}")
    for name, (mae, rmse, r2) in results.items():
        print(f"  {name:14s} {mae:7.2f} {rmse:7.2f} {r2:7.3f}")


def per_semester_breakdown(df, features):
    """Leave-one-semester-out: report error on each held-out semester."""
    X, y = df[features].to_numpy(), df[TARGET].to_numpy()
    offerings = df["offering"].to_numpy()
    print("\n=== leave-one-semester-out, per held-out semester (Ridge) ===")
    print(f"  {'held-out':14s} {'n':>4s} {'MAE':>7s} {'RMSE':>7s}")
    gkf = GroupKFold(n_splits=df["offering"].nunique())
    for tr, te in gkf.split(X, y, offerings):
        pipe = make_pipeline(Ridge(alpha=1.0))
        pipe.fit(X[tr], y[tr])
        p = pipe.predict(X[te])
        sem = offerings[te][0]
        mae = mean_absolute_error(y[te], p)
        rmse = np.sqrt(mean_squared_error(y[te], p))
        print(f"  {sem:14s} {len(te):4d} {mae:7.2f} {rmse:7.2f}")


def save_grade_model(df):
    """Fit Ridge on ALL real data and persist a deployable artifact for the API.

    Saves a dict the GradeService loads: the fitted pipeline plus the metadata
    needed for defaults and explanations.
    """
    import datetime
    from pathlib import Path

    import joblib

    X = df[RAW_FEATURES].to_numpy()
    y = df[TARGET].to_numpy()
    pipe = make_pipeline(Ridge(alpha=1.0))
    pipe.fit(X, y)

    # Honest cross-semester metric to ship alongside the model.
    gkf = GroupKFold(n_splits=df["offering"].nunique())
    loso = evaluate(df, RAW_FEATURES, gkf, df["offering"].to_numpy())["Ridge"]

    out_dir = Path(__file__).resolve().parents[2] / "ml_models"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "grade_model.pkl"
    joblib.dump({
        "model": pipe,
        "version": GRADE_MODEL_VERSION,
        "features": RAW_FEATURES,
        "target": TARGET,
        "feature_means": df[RAW_FEATURES].mean().to_dict(),
        "metrics_loso": {"mae": loso[0], "rmse": loso[1], "r2": loso[2]},
        "n_train": int(len(df)),
        "trained_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }, out_path)
    print(f"\nSaved grade regression model -> {out_path}")
    print(f"  version={GRADE_MODEL_VERSION}  n={len(df)}  "
          f"LOSO MAE={loso[0]:.2f}  R2={loso[2]:.3f}")
    return out_path


def main():
    import argparse

    ap = argparse.ArgumentParser(description="Real-data early-grade regression.")
    ap.add_argument("--save", action="store_true",
                    help="Also fit on all data and save grade_model.pkl for the API.")
    args = ap.parse_args()

    df = harmonize_all()
    n_off = df["offering"].nunique()
    print(f"Loaded {len(df)} students across {n_off} semesters.")
    print(f"Target: {TARGET} (mean {df[TARGET].mean():.1f}, std {df[TARGET].std():.1f})")

    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    gkf = GroupKFold(n_splits=n_off)
    groups = df["offering"].to_numpy()

    # --- Experiment 1: viability + honesty -------------------------------- #
    print("\n" + "=" * 64)
    print("EXPERIMENT 1 — does early data predict the final grade?")
    print("=" * 64)
    _print_table("[A] random 5-fold CV (optimistic: mixes semesters)",
                 evaluate(df, RAW_FEATURES, kf))
    _print_table("[B] leave-one-semester-out (honest cross-cohort)",
                 evaluate(df, RAW_FEATURES, gkf, groups))
    per_semester_breakdown(df, RAW_FEATURES)

    # --- Experiment 2: normalization before/after ------------------------- #
    print("\n" + "=" * 64)
    print("EXPERIMENT 2 — does cohort normalization help cross-semester?")
    print("(same target & validation; only the feature track changes)")
    print("=" * 64)
    _print_table("[RAW]  absolute early features, leave-one-semester-out",
                 evaluate(df, RAW_FEATURES, gkf, groups))
    _print_table("[NORM] within-cohort percentile features, leave-one-semester-out",
                 evaluate(df, NORM_FEATURES, gkf, groups))

    print("\nInterpretation hints:")
    print("  * B should be worse than A — that gap is the real cost of")
    print("    generalizing to an unseen semester (the honest number).")
    print("  * If NORM beats RAW in Experiment 2, cohort normalization")
    print("    improves cross-semester transfer (your key evidence).")

    if args.save:
        save_grade_model(df)


if __name__ == "__main__":
    main()
