"""Offline model training script.

Run this OUTSIDE the web request cycle to produce the .pkl artifact that
MLService loads at startup.

    cd backend
    python -m analytics.ml.train                 # train on OULAD (downloads if needed)
    python -m analytics.ml.train --csv data.csv  # train on your own CSV instead

The CSV (if used) must contain the FEATURE_COLUMNS plus the TARGET_COLUMN.

Algorithm route (per the proposal): LogReg baseline -> RandomForest main ->
XGBoost advanced. This uses RandomForest as the default main model. To use
XGBoost, install xgboost and swap the estimator below.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split

# Allow running both as a module (-m) and as a plain script.
try:
    from analytics.ml.features import FEATURE_COLUMNS, TARGET_COLUMN
    from analytics.ml.oulad import load_oulad_features, download_oulad, is_downloaded
except ModuleNotFoundError:  # pragma: no cover
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from analytics.ml.features import FEATURE_COLUMNS, TARGET_COLUMN
    from analytics.ml.oulad import load_oulad_features, download_oulad, is_downloaded

MODEL_VERSION = "rf-oulad-v1"


def train(df: pd.DataFrame, out_dir: Path) -> Path:
    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    # class_weight balances the (usually) larger not-at-risk group.
    model = RandomForestClassifier(
        n_estimators=300, max_depth=12, class_weight="balanced", random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    # --- Evaluation (what you show in the report / defense) -----------------
    proba = model.predict_proba(X_test)[:, 1]
    pred = model.predict(X_test)
    print("ROC-AUC:", round(roc_auc_score(y_test, proba), 4))
    print(classification_report(y_test, pred, digits=3))
    print("Feature importances:")
    for col, imp in sorted(
        zip(FEATURE_COLUMNS, model.feature_importances_), key=lambda x: -x[1]
    ):
        print(f"  {col:22s} {imp:.4f}")

    # --- Persist ------------------------------------------------------------
    import joblib

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "risk_model.pkl"
    joblib.dump(
        {"model": model, "version": MODEL_VERSION, "features": FEATURE_COLUMNS},
        out_path,
    )
    print(f"\nSaved model -> {out_path}")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Train the risk prediction model.")
    parser.add_argument("--csv", type=str, default=None,
                        help="Train on this CSV instead of OULAD.")
    parser.add_argument("--out", type=str,
                        default=str(Path(__file__).resolve().parents[2] / "ml_models"),
                        help="Output directory for the .pkl artifact.")
    args = parser.parse_args()

    if args.csv:
        df = pd.read_csv(args.csv)
        df[FEATURE_COLUMNS] = df[FEATURE_COLUMNS].fillna(
            df[FEATURE_COLUMNS].mean(numeric_only=True)
        )
        print(f"Loaded {len(df)} rows from {args.csv}")
    else:
        if not is_downloaded():
            download_oulad()
        df = load_oulad_features()
        print(f"Loaded {len(df)} OULAD enrolments "
              f"(at-risk rate {df[TARGET_COLUMN].mean():.1%})")

    train(df, Path(args.out))


if __name__ == "__main__":
    main()
