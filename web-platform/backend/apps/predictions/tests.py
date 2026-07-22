from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.courses.models import Course, CourseSection

User = get_user_model()


class RunPredictionValidationTests(APITestCase):
    """feature_cutoff_week 的边际校验：非整数 / 越界应 422，而非透传到
    services 里做 `week_no <= cutoff_week` 比较时抛 TypeError → 500。"""

    def setUp(self):
        self.user = User.objects.create_user(username="teacher", password="pw123456")
        self.client.force_authenticate(self.user)
        self.course = Course.objects.create(
            code="COMP8567", name="AI", term="S26", owner=self.user)
        self.section = CourseSection.objects.create(
            course=self.course, section_code="01", instructor=self.user)

    def _run(self, body):
        return self.client.post(
            f"/api/v1/sections/{self.section.id}/predictions/run", body, format="json")

    def test_non_integer_cutoff_rejected(self):
        resp = self._run({"feature_cutoff_week": "abc"})
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json()["error"]["code"], "VALIDATION_FAILED")

    def test_numeric_string_cutoff_out_of_range_rejected(self):
        resp = self._run({"feature_cutoff_week": "999"})
        self.assertEqual(resp.status_code, 422)

    def test_negative_cutoff_rejected(self):
        resp = self._run({"feature_cutoff_week": -3})
        self.assertEqual(resp.status_code, 422)

    def test_bool_cutoff_rejected(self):
        resp = self._run({"feature_cutoff_week": True})
        self.assertEqual(resp.status_code, 422)

    def test_missing_cutoff_ok(self):
        # 不传 cutoff 是合法的（不按周截断）；空班级下运行应成功（0 个学生）
        resp = self._run({})
        self.assertEqual(resp.status_code, 201)

    def test_valid_numeric_string_cutoff_accepted(self):
        resp = self._run({"feature_cutoff_week": "5"})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["data"]["feature_cutoff_week"], 5)
