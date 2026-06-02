"""ML inference service.

Responsibilities:
  * Load the trained model artifact (.pkl) ONCE at process start.
  * Expose a single ``predict()`` entry point used by the API views.
  * Degrade gracefully: if no trained model exists yet, fall back to a
    transparent rule-based predictor so the backend is usable immediately.

Training does NOT happen here — see analytics/ml/train.py for the offline
training script that produces the .pkl this module loads.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from django.conf import settings

from analytics.ml.features import FEATURE_COLUMNS, risk_level, to_feature_row

logger = logging.getLogger(__name__)

MODEL_FILENAME = "risk_model.pkl"


class MLService:
    """Singleton-style holder for the loaded model."""

    _model = None              # the fitted sklearn/xgboost estimator
    _version: str = "rule-based-fallback"
    _loaded: bool = False

    # -- lifecycle -----------------------------------------------------------
    @classmethod
    def load(cls) -> None:
        """Load the model artifact into memory. Safe to call repeatedly."""
        model_path: Path = settings.ML_MODELS_DIR / MODEL_FILENAME
        if not model_path.exists():
            logger.warning(
                "No trained model at %s — using rule-based fallback. "
                "Run `python -m analytics.ml.train` to create one.",
                model_path,
            )
            cls._model = None
            cls._version = "rule-based-fallback"
            cls._loaded = True
            return

        try:
            import joblib

            artifact = joblib.load(model_path)
            # train.py saves a dict: {"model": ..., "version": ...}
            cls._model = artifact["model"]
            cls._version = artifact.get("version", "unknown")
            logger.info("Loaded ML model '%s' from %s", cls._version, model_path)
        except Exception:  # noqa: BLE001 - never let model loading crash boot
            logger.exception("Failed to load model; falling back to rules.")
            cls._model = None
            cls._version = "rule-based-fallback"
        cls._loaded = True

    @classmethod
    def is_model_loaded(cls) -> bool:
        return cls._model is not None

    @classmethod
    def version(cls) -> str:
        return cls._version

    # -- inference -----------------------------------------------------------
    @classmethod
    def predict(cls, data: dict) -> dict:
        """Return risk for one student.

        Parameters
        ----------
        data: dict with feature keys (see features.FEATURE_COLUMNS).

        Returns
        -------
        dict: {risk_score, risk_level, model_version, explanation}
        """
        if not cls._loaded:
            cls.load()

        features = to_feature_row(data)

        if cls._model is None:
            return cls._rule_based(data, features)

        # Real model path -----------------------------------------------------
        import numpy as np

        X = np.array([features])
        proba = float(cls._model.predict_proba(X)[0][1])
        return {
            "risk_score": round(proba, 4),
            "risk_level": risk_level(proba),
            "model_version": cls._version,
            "explanation": cls._explain(X),
        }

    # -- helpers -------------------------------------------------------------
    @classmethod
    def _explain(cls, X) -> dict:
        """Per-feature contribution. Uses SHAP if available, else feature_importances_.

        Returns an empty dict if neither is available — the API contract stays
        the same regardless.
        """
        try:
            import shap  # optional dependency

            explainer = shap.TreeExplainer(cls._model)
            values = explainer.shap_values(X)
            # shap may return a list (per class) or array depending on model.
            row = values[1][0] if isinstance(values, list) else values[0]
            return {col: round(float(v), 4) for col, v in zip(FEATURE_COLUMNS, row)}
        except Exception:  # noqa: BLE001
            importances = getattr(cls._model, "feature_importances_", None)
            if importances is None:
                return {}
            return {
                col: round(float(v), 4)
                for col, v in zip(FEATURE_COLUMNS, importances)
            }

    @classmethod
    def _rule_based(cls, data: dict, features: list[float]) -> dict:
        """Transparent fallback matching the proposal's 'rule-based risk
        detection' step. Lets the API work before a model is trained.

        Features order (see features.FEATURE_COLUMNS):
            total_clicks, active_days, mean_clicks_per_day,
            early_avg_score, num_prev_attempts, studied_credits
        """
        total_clicks, active_days, _cpd, early_score, prev_attempts, _credits = features

        score = 0.0
        if early_score < 40:          # weak early assessment performance
            score += 0.4
        elif early_score < 55:
            score += 0.2
        if total_clicks < 100:        # low engagement
            score += 0.2
        if active_days < 5:           # rarely shows up
            score += 0.2
        if prev_attempts >= 1:        # repeating the module
            score += 0.2
        score = min(score, 1.0)

        return {
            "risk_score": round(score, 4),
            "risk_level": risk_level(score),
            "model_version": cls._version,
            "explanation": {
                "early_avg_score": early_score,
                "total_clicks": total_clicks,
                "active_days": active_days,
                "num_prev_attempts": prev_attempts,
            },
        }
