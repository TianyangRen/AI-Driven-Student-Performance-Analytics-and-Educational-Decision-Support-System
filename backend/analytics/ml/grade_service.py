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
    _residual_std: float | None = None  # honest LOSO sigma for uncertainty
    _target_note: str = ""
    _exam_pipe = None                    # strictly-future head (Midterm I+II avg)
    _exam_metrics: dict = {}
    _exam_residual_std: float | None = None
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
            cls._residual_std = art.get("residual_std")
            cls._target_note = art.get("target_note", "")
            cls._exam_pipe = art.get("exam_model")
            cls._exam_metrics = art.get("exam_metrics_loso", {})
            cls._exam_residual_std = art.get("exam_residual_std")
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
            "exam_head_loaded": cls._exam_pipe is not None,
            "exam_metrics_loso": cls._exam_metrics,
            "target_note": cls._target_note,
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

        # Honest missing-data handling: features absent from the request are
        # imputed with training means, but NEVER silently — a student with no
        # early submissions is not an "average" student; missing work is
        # itself a risk signal. The response says exactly what was imputed.
        row, missing = [], []
        for f in cls._features:
            if f in data and data[f] is not None:
                row.append(float(data[f]))
            else:
                row.append(float(cls._feature_means.get(f, 0.7)))
                missing.append(f)

        X = np.array([row])
        pred = float(cls._pipe.predict(X)[0])
        pred = max(0.0, min(100.0, pred))

        result = {
            "predicted_course_total": round(pred, 1),
            "target_note": cls._target_note,
            "risk_level": grade_risk_band(pred),
            "model_version": cls._version,
            "explanation": cls._explain(X),
            "thresholds": {"high": "<60", "medium": "60-70", "low": ">=70"},
        }
        result.update(cls._uncertainty(pred))

        # Strictly-future head: projected Midterm I+II average (zero overlap
        # with the early inputs -> genuine forward prediction).
        if cls._exam_pipe is not None:
            import math

            epred = float(cls._exam_pipe.predict(X)[0])
            epred = max(0.0, min(100.0, epred))
            exam = {"predicted_exam_avg": round(epred, 1)}
            if cls._exam_residual_std:
                z80 = 1.2816
                s = cls._exam_residual_std
                exam["exam_interval_80"] = [
                    round(max(0.0, epred - z80 * s), 1),
                    round(min(100.0, epred + z80 * s), 1)]
            result["exam_head"] = exam

        if not missing:
            result["data_coverage"] = "full"
        else:
            result["data_coverage"] = "partial" if len(missing) == 1 else "insufficient"
            result["missing_features"] = missing
            result["warning"] = (
                "Missing early-work data was imputed with training averages, so "
                "the projection may be too optimistic. Missing submissions can "
                "themselves signal risk — verify before relying on this estimate."
            )
        return result

    @classmethod
    def _uncertainty(cls, pred: float) -> dict:
        """Probabilistic outputs from the Gaussian predictive distribution
        N(pred, sigma^2), with sigma estimated from honest leave-one-semester-
        out residuals at training time (Variant A: probabilistic forecasting).

        Returns an 80% central prediction interval and P(final < threshold)
        for the risk thresholds — a failure probability that needs NO failing
        samples in a classification sense.
        """
        sigma = cls._residual_std
        if not sigma:  # old artifact without residual_std
            return {}
        import math

        z80 = 1.2816  # 80% central interval
        lo = max(0.0, pred - z80 * sigma)
        hi = min(100.0, pred + z80 * sigma)

        def p_below(t: float) -> float:
            return 0.5 * (1.0 + math.erf((t - pred) / (sigma * math.sqrt(2))))

        return {
            "prediction_interval_80": [round(lo, 1), round(hi, 1)],
            "prob_below_60": round(p_below(60.0), 3),
            "prob_below_70": round(p_below(70.0), 3),
            "uncertainty_sigma": round(sigma, 2),
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
