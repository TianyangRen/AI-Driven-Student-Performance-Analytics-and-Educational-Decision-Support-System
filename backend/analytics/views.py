"""API views."""
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from analytics.ml.grade_service import GradeService
from analytics.ml.service import MLService
from analytics.models import RiskPrediction, Student
from analytics.serializers import (
    GradePredictRequestSerializer,
    PredictRequestSerializer,
)


@api_view(["GET"])
def health(request):
    """Liveness + model status, handy during development."""
    return Response(
        {
            "status": "ok",
            "risk_classifier": {
                "model_loaded": MLService.is_model_loaded(),
                "model_version": MLService.version(),
            },
            "grade_regressor": GradeService.info(),
        }
    )


@api_view(["POST"])
def predict_risk(request):
    """Predict risk for a single student from feature values.

    Body (all optional, numeric; OULAD early-window features):
        {"total_clicks": 40, "active_days": 3, "mean_clicks_per_day": 13,
         "early_avg_score": 35, "num_prev_attempts": 1, "studied_credits": 60}

    Optionally pass "student_id" to persist the prediction.
    """
    serializer = PredictRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    result = MLService.predict(serializer.validated_data)

    # Optionally store the prediction against an existing student.
    student_id = request.data.get("student_id")
    if student_id:
        try:
            student = Student.objects.get(student_id=student_id)
            RiskPrediction.objects.create(
                student=student,
                risk_score=result["risk_score"],
                risk_level=result["risk_level"],
                model_version=result["model_version"],
                explanation=result.get("explanation", {}),
            )
            result["persisted"] = True
        except Student.DoesNotExist:
            return Response(
                {"detail": f"Unknown student_id '{student_id}'."},
                status=status.HTTP_404_NOT_FOUND,
            )

    return Response(result)


@api_view(["POST"])
def predict_grade(request):
    """Project a student's FINAL grade from leakage-free EARLY features.

    Body (all optional, fractions in [0, 1]; local real-data model):
        {"early_lab_avg": 0.7, "early_assignment_pct": 0.8, "early_quiz_avg": 0.4}

    Returns the projected final grade (0-100) and a risk band
    (<60 high, 60-70 medium, >=70 low).
    """
    if not GradeService.is_loaded():
        return Response(
            {"detail": "Grade model not available. Run "
                       "`python -m analytics.ml.train_real --save`."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    serializer = GradePredictRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    return Response(GradeService.predict(serializer.validated_data))
