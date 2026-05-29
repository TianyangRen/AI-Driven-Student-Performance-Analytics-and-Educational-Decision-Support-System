"""DRF serializers."""
from rest_framework import serializers

from analytics.models import Assessment, RiskPrediction, Student
from analytics.ml.features import FEATURE_COLUMNS


class AssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assessment
        fields = ["id", "type", "score", "max_score", "week"]


class StudentSerializer(serializers.ModelSerializer):
    assessments = AssessmentSerializer(many=True, read_only=True)

    class Meta:
        model = Student
        fields = ["id", "student_id", "name", "group", "semester", "assessments"]


class RiskPredictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskPrediction
        fields = [
            "id",
            "student",
            "risk_score",
            "risk_level",
            "model_version",
            "explanation",
            "created_at",
        ]


class PredictRequestSerializer(serializers.Serializer):
    """Validates the body of POST /api/predict/.

    Every feature is optional (service.to_feature_row supplies defaults),
    but each must be numeric when present.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for col in FEATURE_COLUMNS:
            self.fields[col] = serializers.FloatField(required=False)
