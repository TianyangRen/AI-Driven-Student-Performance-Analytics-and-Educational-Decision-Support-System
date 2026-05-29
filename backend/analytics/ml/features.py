"""Feature definitions shared between training and inference.

Keeping the feature list in ONE place guarantees that the columns used to
train the model are exactly the columns the API feeds at prediction time.
Order matters: scikit-learn models expect features in the same order.
"""
from __future__ import annotations

# The model's input features, in fixed order.
FEATURE_COLUMNS: list[str] = [
    "quiz_avg",          # average quiz score (0-100)
    "lab_avg",           # average lab score (0-100)
    "assignment_avg",    # average assignment score (0-100)
    "midterm",           # midterm score (0-100)
    "participation",     # participation / engagement score (0-100)
    "days_since_login",  # recency of last activity (days)
]

# The label the model predicts.
TARGET_COLUMN = "at_risk"  # 1 = at risk, 0 = not at risk

# Risk thresholds applied to the predicted probability.
RISK_THRESHOLDS = {"high": 0.70, "medium": 0.40}


def risk_level(probability: float) -> str:
    """Map a probability in [0, 1] to a low/medium/high label."""
    if probability >= RISK_THRESHOLDS["high"]:
        return "high"
    if probability >= RISK_THRESHOLDS["medium"]:
        return "medium"
    return "low"


def to_feature_row(data: dict) -> list[float]:
    """Turn an incoming dict into an ordered feature vector.

    Missing keys default to a neutral value so the API never 500s on
    partial input. Tune the defaults to match your data.
    """
    defaults = {
        "quiz_avg": 60.0,
        "lab_avg": 60.0,
        "assignment_avg": 60.0,
        "midterm": 60.0,
        "participation": 50.0,
        "days_since_login": 7.0,
    }
    return [float(data.get(col, defaults[col])) for col in FEATURE_COLUMNS]
