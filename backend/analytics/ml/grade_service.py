"""Inference service for the early-grade REGRESSION model.

Parallel to MLService (which serves the OULAD risk classifier), GradeService
serves the local real-data model: it takes a student's leakage-free EARLY
features and returns a PROJECTED final grade plus a risk band.

The artifact (ml_models/grade_model.pkl) is produced offline by:
    python -m analytics.ml.train_real --save
"""
from __future__ import annotations

import logging
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

MODEL_FILENAME = "grade_model.pkl"

# Grade -> risk band thresholds (on the 0-100 final-grade scale).
GRADE_RISK_THRESHOLDS = {"high": 60.0, "medium": 70.0}


def grade_risk_band(predicted_grade: float) -> str:
    """Map a projected final grade to a low/medium/high risk band."""
    if predicted_grade < GRADE_RISK_THRESHOLDS["high"]:
        return "high"
    if predicted_grade < GRADE_RISK_THRESHOLDS["medium"]:
        return "medium"
    return "low"


class GradeService:
    """Singleton-style holder for the loaded regression pipeline."""

    _pipe = None
    _features: list[str] = []
    _feature_means: dict = {}
    _version: str = "not-loaded"
    _metrics: dict = {}
    _loaded: bool = False

    # -- lifecycle -----------------------------------------------------------
    @classmethod
    def load(cls) -> None:
        path: Path = settings.ML_MODELS_DIR / MODEL_FILENAME
        if not path.exists():
            logger.warning(
                "No grade model at %s — /api/predict-grade/ will be unavailable. "
                "Run `python -m analytics.ml.train_real --save`.", path,
            )
            cls._loaded = True
            return
        try:
            import joblib

            art = joblib.load(path)
            cls._pipe = art["model"]
            cls._features = art["features"]
            cls._feature_means = art.get("feature_means", {})
            cls._version = art.get("version", "unknown")
            cls._metrics = art.get("metrics_loso", {})
            logger.info("Loaded grade model '%s' from %s", cls._version, path)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to load grade model.")
            cls._pipe = None
        cls._loaded = True

    @classmethod
    def is_loaded(cls) -> bool:
        return cls._pipe is not None

    @classmethod
    def info(cls) -> dict:
        return {
            "loaded": cls.is_loaded(),
            "version": cls._version,
            "features": cls._features,
            "metrics_loso": cls._metrics,
        }

    # -- inference -----------------------------------------------------------
    @classmethod
    def predict(cls, data: dict) -> dict:
        """Project the final grade from a student's early features.

        Parameters
        ----------
        data: dict with keys in cls._features (fractions in [0, 1]). Missing
            keys fall back to the training mean.

        Returns
        -------
        dict: predicted_final_grade, risk_level, model_version, explanation,
              thresholds.
        """
        if not cls._loaded:
            cls.load()
        if cls._pipe is None:
            raise RuntimeError("Grade model is not available.")

        import numpy as np

        row = [float(data.get(f, cls._feature_means.get(f, 0.7))) for f in cls._features]
        X = np.array([row])
        pred = float(cls._pipe.predict(X)[0])
        pred = max(0.0, min(100.0, pred))

        return {
            "predicted_final_grade": round(pred, 1),
            "risk_level": grade_risk_band(pred),
            "model_version": cls._version,
            "explanation": cls._explain(X),
            "thresholds": {"high": "<60", "medium": "60-70", "low": ">=70"},
        }

    # -- helpers -------------------------------------------------------------
    @classmethod
    def _explain(cls, X) -> dict:
        """Exact per-feature contribution for the linear model (in grade points).

        For a Ridge-in-Pipeline, prediction = intercept + sum(coef_j * z_j),
        where z is the standardized feature. contribution_j = coef_j * z_j tells
        how many grade points feature j pushes the projection above/below the
        baseline. (No SHAP needed — linear models are exactly decomposable.)
        """
        try:
            imp = cls._pipe.named_steps["impute"]
            scaler = cls._pipe.named_steps["scale"]
            model = cls._pipe.named_steps["model"]
            z = scaler.transform(imp.transform(X))[0]
            contribs = model.coef_ * z
            return {f: round(float(c), 2) for f, c in zip(cls._features, contribs)}
        except Exception:  # noqa: BLE001
            return {}
