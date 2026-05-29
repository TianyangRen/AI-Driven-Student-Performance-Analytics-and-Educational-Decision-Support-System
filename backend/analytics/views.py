"""API views."""
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from analytics.ml.service import MLService
from analytics.models import RiskPrediction, Student
from analytics.serializers import PredictRequestSerializer


@api_view(["GET"])
def health(request):
    """Liveness + model status, handy during development."""
    return Response(
        {
            "status": "ok",
            "model_loaded": MLService.is_model_loaded(),
            "model_version": MLService.version(),
        }
    )


@api_view(["POST"])
def predict_risk(request):
    """Predict risk for a single student from feature values.

    Body (all optional, numeric):
        {"quiz_avg": 55, "lab_avg": 60, "assignment_avg": 48,
         "midterm": 50, "participation": 30, "days_since_login": 20}

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
