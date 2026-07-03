from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "analytics"

    def ready(self):
        """Warm up the ML model when the server starts.

        Loading the model once at startup (instead of per-request) keeps
        prediction latency low. Loading is best-effort: if no trained model
        exists yet, the service falls back to a rule-based predictor so the
        API still works before you run train.py.
        """
        # Import here to avoid side effects during migrations / management cmds.
        # (The OULAD classifier is a research benchmark and is no longer
        # loaded at startup — see analytics/ml/service.py.)
        from analytics.ml.grade_service import GradeService

        GradeService.load()
