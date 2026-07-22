from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.courses.models import Course, CourseSection, Enrollment, Student

User = get_user_model()

_URL = "/api/v1/analytics/cohort-profile"


class StudentsPaginationTests(APITestCase):
    """班级学生列表现在分页封顶：响应带分页 meta，且 page_size 可收窄。
    默认页很大，普通班级一页返回全部（前端读 data 数组行为不变）。"""

    def setUp(self):
        self.user = User.objects.create_user(username="teacher", password="pw123456")
        self.client.force_authenticate(self.user)
        self.course = Course.objects.create(
            code="COMP8567", name="AI", term="S26", owner=self.user)
        self.section = CourseSection.objects.create(
            course=self.course, section_code="01", instructor=self.user)
        for i in range(5):
            student = Student.objects.create(
                student_no=f"S-{i:03d}", anonymized_code=f"S-ANON-{i:03d}")
            Enrollment.objects.create(section=self.section, student=student, status="ACTIVE")

    def _url(self):
        return f"/api/v1/sections/{self.section.id}/students"

    def test_default_returns_all_with_pagination_meta(self):
        resp = self.client.get(self._url())
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body["data"]), 5)
        self.assertEqual(body["meta"]["total"], 5)
        self.assertIn("page", body["meta"])

    def test_page_size_caps_response(self):
        resp = self.client.get(self._url(), {"page_size": 2})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body["data"]), 2)
        self.assertEqual(body["meta"]["total"], 5)
        self.assertIsNotNone(body["meta"]["next"])


class CohortProfileKValidationTests(APITestCase):
    """聚类簇数 k 的边际校验：非整数 / 越界应在网关调用前 422，
    否则会透传给 ML 服务的 int(k) 抛 ValueError → 500，或让聚类崩溃。

    校验发生在调用 ML 网关之前，因此这些用例无需 ML 服务在线。
    """

    def setUp(self):
        self.user = User.objects.create_user(username="teacher", password="pw123456")
        self.client.force_authenticate(self.user)

    def test_non_integer_k_rejected(self):
        resp = self.client.get(_URL, {"clusters": 1, "k": "abc"})
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json()["error"]["code"], "VALIDATION_FAILED")

    def test_k_too_small_rejected(self):
        resp = self.client.get(_URL, {"clusters": 1, "k": 1})
        self.assertEqual(resp.status_code, 422)

    def test_k_too_large_rejected(self):
        resp = self.client.get(_URL, {"clusters": 1, "k": 9999})
        self.assertEqual(resp.status_code, 422)
