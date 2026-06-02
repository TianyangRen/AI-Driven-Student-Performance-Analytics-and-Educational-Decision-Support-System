"""Feature definitions shared between training and inference.

Keeping the feature list in ONE place guarantees that the columns used to
train the model are exactly the columns the API feeds at prediction time.
Order matters: scikit-learn models expect features in the same order.

These features are derived from the OULAD dataset (see analytics/ml/oulad.py).
They are designed for EARLY prediction: everything is measured within the
first few weeks of a course (default: first 28 days), so the model predicts
the final outcome WITHOUT peeking at end-of-course data (avoids leakage).

When you later switch to your own local course data (quizzes, labs, ...),
redefine these columns and retrain — the rest of the system adapts
automatically because everyone imports from here.
"""
from __future__ import annotations

# The model's input features, in fixed order.
FEATURE_COLUMNS: list[str] = [
    "total_clicks",            # total VLE clicks in the early window
    "active_days",             # number of distinct days the student was active
    "mean_clicks_per_day",     # engagement intensity (clicks / active day)
    "early_avg_score",         # mean score of assessments due in the early window
    "num_prev_attempts",       # how many times the student took this module before
    "studied_credits",         # total credits the student is studying
]

# The label the model predicts: 1 = at risk (Fail/Withdrawn), 0 = not at risk.
TARGET_COLUMN = "at_risk"

# Risk thresholds applied to the predicted probability.
RISK_THRESHOLDS = {"high": 0.70, "medium": 0.40}

# Neutral defaults used when the API receives partial input. Tune to your data.
FEATURE_DEFAULTS = {
    "total_clicks": 200.0,
    "active_days": 10.0,
    "mean_clicks_per_day": 20.0,
    "early_avg_score": 65.0,
    "num_prev_attempts": 0.0,
    "studied_credits": 60.0,
}


def risk_level(probability: float) -> str:
    """Map a probability in [0, 1] to a low/medium/high label."""
    if probability >= RISK_THRESHOLDS["high"]:
        return "high"
    if probability >= RISK_THRESHOLDS["medium"]:
        return "medium"
    return "low"


def to_feature_row(data: dict) -> list[float]:
    """Turn an incoming dict into an ordered feature vector.

    Missing keys fall back to FEATURE_DEFAULTS so the API never 500s on
    partial input.
    """
    return [float(data.get(col, FEATURE_DEFAULTS[col])) for col in FEATURE_COLUMNS]
