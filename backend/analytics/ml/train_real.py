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
# context) predicting the absolute final grade.
# v2: artifact carries residual_std (LOSO) for intervals & risk probabilities.
# v3: adds a second, strictly-future head (exam average = Midterm I+II) with
#     ZERO input overlap, plus an explicit target note: the primary target is
#     the official COURSE TOTAL (there is no final exam in this course), and
#     the early inputs make up ~8.8% of that total (disclosed, not hidden).
# v4: robust loss (Huber) — the single lowest final (33) is a mid-course
#     disengagement case, not a measured-ability point; Huber keeps it in the
#     data without letting it distort the fit. Sensitivity (with/without that
#     case) is computed and shipped in the artifact.
GRADE_MODEL_VERSION = "huber-grade-v4"

TARGET_NOTE = (
    "Primary target = official course total (Adjusted Final Grade, /100). "
    "This course has NO final exam; the total = labs + assignments + quizzes "
    "+ midterm I & II + project. Early input components constitute ~8.8% of "
    "the total (disclosed overlap). The exam head predicts the strictly-"
    "future Midterm I+II average (% of max) with zero input overlap. "
    "Fitted with Huber (robust) loss; grades concentrate at 70-96, so the "
    "model separates relative standing among engaged students — behavioural "
    "dropout risk is handled by the separate disengagement track."
)


def make_estimator():
    """The deployed estimator: linear + robust (Huber) loss.

    Robust because the one catastrophic outcome in the data (final 33) is a
    disengagement artifact; least squares would let that single point tilt
    the coefficients. Still linear -> the exact per-feature explanation in
    GradeService keeps working.
    """
    from sklearn.linear_model import HuberRegressor

    return HuberRegressor(epsilon=1.35, alpha=1e-4, max_iter=2000)


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
        "Huber": make_estimator(),
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
    pipe = make_pipeline(make_estimator())
    pipe.fit(X, y)

    groups = df["offering"].to_numpy()
    gkf = GroupKFold(n_splits=df["offering"].nunique())

    def _loso(frame, estimator_factory):
        """LOSO MAE + residuals for an arbitrary subset / estimator."""
        Xf = frame[RAW_FEATURES].to_numpy()
        yf = frame[TARGET].to_numpy()
        gf = frame["offering"].to_numpy()
        kf = GroupKFold(n_splits=len(np.unique(gf)))
        res = []
        for tr, te in kf.split(Xf, yf, gf):
            p = make_pipeline(estimator_factory())
            p.fit(Xf[tr], yf[tr])
            res.extend(yf[te] - p.predict(Xf[te]))
        res = np.asarray(res)
        return float(np.mean(np.abs(res))), res

    # Honest cross-semester metric + uncertainty sigma (never in-sample).
    huber_mae, residuals = _loso(df, make_estimator)
    residual_std = float(np.std(residuals, ddof=1))
    loso = evaluate(df, RAW_FEATURES, gkf, groups)["Huber"]

    # Sensitivity: does the single disengagement outlier (final < 50) drive
    # the numbers? Compare Ridge/Huber on all data and Huber without it.
    ridge_mae, _ = _loso(df, lambda: Ridge(alpha=1.0))
    excl = df[df[TARGET] >= 50]
    huber_excl_mae, _ = _loso(excl, make_estimator)
    sensitivity = {
        "ridge_all_mae": round(ridge_mae, 2),
        "huber_all_mae": round(huber_mae, 2),
        "huber_excl_dropout_mae": round(huber_excl_mae, 2),
        "n_excluded": int(len(df) - len(excl)),
        "note": "excluded = final < 50 (the mid-course disengagement case)",
    }

    # --- Second head: strictly-future exam average (Midterm I+II, 0-100) ----
    # Zero overlap with the early inputs -> demonstrates genuine prediction.
    exam_y_all = df["abs_midterm"] * 100
    emask = exam_y_all.notna().to_numpy()
    Xe, ye, ge = X[emask], exam_y_all[emask].to_numpy(), groups[emask]
    exam_pipe = make_pipeline(make_estimator())
    exam_pipe.fit(Xe, ye)
    epreds, etrues, eres = [], [], []
    egkf = GroupKFold(n_splits=len(np.unique(ge)))
    for tr, te in egkf.split(Xe, ye, ge):
        p = make_pipeline(make_estimator())
        p.fit(Xe[tr], ye[tr])
        pr = p.predict(Xe[te])
        epreds.extend(pr); etrues.extend(ye[te]); eres.extend(ye[te] - pr)
    from sklearn.metrics import mean_absolute_error as _mae, r2_score as _r2
    exam_metrics = {"mae": float(_mae(etrues, epreds)),
                    "r2": float(_r2(etrues, epreds))}
    exam_residual_std = float(np.std(eres, ddof=1))

    out_dir = Path(__file__).resolve().parents[2] / "ml_models"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "grade_model.pkl"
    joblib.dump({
        "model": pipe,
        "version": GRADE_MODEL_VERSION,
        "features": RAW_FEATURES,
        "target": TARGET,
        "target_note": TARGET_NOTE,
        "feature_means": df[RAW_FEATURES].mean().to_dict(),
        "metrics_loso": {"mae": loso[0], "rmse": loso[1], "r2": loso[2]},
        "residual_std": residual_std,
        "sensitivity": sensitivity,
        "exam_model": exam_pipe,
        "exam_metrics_loso": exam_metrics,
        "exam_residual_std": exam_residual_std,
        "n_train": int(len(df)),
        "trained_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }, out_path)
    print(f"\nSaved grade regression model -> {out_path}")
    print(f"  course-total head (Huber): n={len(df)}  LOSO MAE={loso[0]:.2f}  "
          f"R2={loso[2]:.3f}  sigma={residual_std:.2f}")
    print(f"  exam head (strictly future): n={int(emask.sum())}  "
          f"LOSO MAE={exam_metrics['mae']:.2f}  R2={exam_metrics['r2']:.3f}  "
          f"sigma={exam_residual_std:.2f}")
    print(f"  sensitivity: Ridge-all {sensitivity['ridge_all_mae']} | "
          f"Huber-all {sensitivity['huber_all_mae']} | "
          f"Huber-excl-dropout {sensitivity['huber_excl_dropout_mae']} "
          f"(excluded {sensitivity['n_excluded']})")
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
