from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import Course, CourseSection

User = get_user_model()


class CourseSerializerTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="teacher", password="pw123456")
        self.client.force_authenticate(self.user)

    def test_code_normalized_to_upper(self):
        resp = self.client.post("/api/v1/courses", {
            "code": "comp8567", "name": "AI", "term": "S26"}, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["code"], "COMP8567")


class CourseSectionOwnershipTests(APITestCase):
    """建 section 时 course 必须属于当前用户（非 admin）。"""

    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="pw123456")
        self.other = User.objects.create_user(username="other", password="pw123456")
        self.course = Course.objects.create(
            code="COMP8567", name="AI", term="S26", owner=self.owner)

    def test_cannot_attach_section_to_others_course(self):
        self.client.force_authenticate(self.other)
        resp = self.client.post("/api/v1/sections", {
            "course": self.course.id, "section_code": "01"}, format="json")
        # course 不在 other 的可选范围内 -> 校验失败
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(CourseSection.objects.count(), 0)

    def test_owner_can_attach_and_code_normalized(self):
        self.client.force_authenticate(self.owner)
        resp = self.client.post("/api/v1/sections", {
            "course": self.course.id, "section_code": "l01"}, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["section_code"], "L01")
        self.assertEqual(CourseSection.objects.get().instructor, self.owner)

    def test_admin_can_attach_to_any_course(self):
        admin = User.objects.create_user(
            username="boss", password="pw123456", role="ADMIN")
        self.client.force_authenticate(admin)
        resp = self.client.post("/api/v1/sections", {
            "course": self.course.id, "section_code": "02"}, format="json")
        self.assertEqual(resp.status_code, 201)
