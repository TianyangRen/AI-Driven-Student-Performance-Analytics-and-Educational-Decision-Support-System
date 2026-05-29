"""Offline model training script.

Run this OUTSIDE the web request cycle to produce the .pkl artifact that
MLService loads at startup:

    cd backend
    python -m analytics.ml.train                # train on synthetic demo data
    python -m analytics.ml.train --csv data.csv # train on your real CSV

The CSV must contain the FEATURE_COLUMNS plus the TARGET_COLUMN (at_risk).

This intentionally uses scikit-learn's RandomForest as the default main model
(per the proposal: LogReg baseline -> RandomForest main -> XGBoost advanced).
Swap in XGBClassifier once you install xgboost.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split

# Allow running both as a module (-m) and as a plain script.
try:
    from analytics.ml.features import FEATURE_COLUMNS, TARGET_COLUMN
except ModuleNotFoundError:  # pragma: no cover
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from analytics.ml.features import FEATURE_COLUMNS, TARGET_COLUMN

MODEL_VERSION = "rf-v1"


def make_synthetic_data(n: int = 1000, seed: int = 42) -> pd.DataFrame:
    """Generate plausible student data so the pipeline is runnable with no CSV.

    Replace this with real / OULAD-derived data for actual results.
    """
    rng = np.random.default_rng(seed)
    quiz = rng.normal(65, 18, n).clip(0, 100)
    lab = rng.normal(70, 15, n).clip(0, 100)
    assignment = rng.normal(68, 16, n).clip(0, 100)
    midterm = rng.normal(62, 20, n).clip(0, 100)
    participation = rng.normal(60, 22, n).clip(0, 100)
    days_since_login = rng.exponential(6, n).clip(0, 60)

    # "True" final outcome driven by the features (+ noise), then thresholded.
    final = (
        0.30 * quiz + 0.20 * lab + 0.20 * assignment + 0.30 * midterm
        - 0.15 * days_since_login + 0.10 * participation
    )
    final += rng.normal(0, 6, n)
    at_risk = (final < 55).astype(int)

    return pd.DataFrame(
        {
            "quiz_avg": quiz,
            "lab_avg": lab,
            "assignment_avg": assignment,
            "midterm": midterm,
            "participation": participation,
            "days_since_login": days_since_login,
            TARGET_COLUMN: at_risk,
        }
    )


def train(df: pd.DataFrame, out_dir: Path) -> Path:
    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    model = RandomForestClassifier(n_estimators=200, max_depth=8, random_state=42)
    model.fit(X_train, y_train)

    # --- Evaluation (what you show in the report / defense) -----------------
    proba = model.predict_proba(X_test)[:, 1]
    pred = model.predict(X_test)
    print("ROC-AUC:", round(roc_auc_score(y_test, proba), 4))
    print(classification_report(y_test, pred, digits=3))

    # --- Persist ------------------------------------------------------------
    import joblib

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "risk_model.pkl"
    joblib.dump(
        {"model": model, "version": MODEL_VERSION, "features": FEATURE_COLUMNS},
        out_path,
    )
    print(f"Saved model -> {out_path}")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Train the risk prediction model.")
    parser.add_argument("--csv", type=str, default=None, help="Path to training CSV.")
    parser.add_argument(
        "--out",
        type=str,
        default=str(Path(__file__).resolve().parents[2] / "ml_models"),
        help="Output directory for the .pkl artifact.",
    )
    args = parser.parse_args()

    if args.csv:
        df = pd.read_csv(args.csv)
        # Basic cleaning: fill numeric NaNs with column means.
        df[FEATURE_COLUMNS] = df[FEATURE_COLUMNS].fillna(
            df[FEATURE_COLUMNS].mean(numeric_only=True)
        )
        print(f"Loaded {len(df)} rows from {args.csv}")
    else:
        df = make_synthetic_data()
        print(f"Using {len(df)} synthetic rows (no --csv provided)")

    train(df, Path(args.out))


if __name__ == "__main__":
    main()
