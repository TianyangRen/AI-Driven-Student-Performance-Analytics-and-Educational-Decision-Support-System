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

    def test_code_rejects_symbols(self):
        for bad in ["COMP!", "comp 8567", "a*b", "@@@"]:
            resp = self.client.post("/api/v1/courses", {
                "code": bad, "name": "AI", "term": "S26"}, format="json")
            self.assertEqual(resp.status_code, 400, bad)
            fields = [d["field"] for d in resp.json()["error"]["details"]]
            self.assertIn("code", fields, bad)

    def test_term_allows_space_and_hyphen_but_rejects_symbols(self):
        # 空格与连字符放行
        resp = self.client.post("/api/v1/courses", {
            "code": "COMP1000", "name": "AI", "term": "Summer 2026"}, format="json")
        self.assertEqual(resp.status_code, 201)
        resp = self.client.post("/api/v1/courses", {
            "code": "COMP1001", "name": "AI", "term": "2025-2026"}, format="json")
        self.assertEqual(resp.status_code, 201)
        # 符号拒绝
        for bad in ["S26!", "Fall@2025", "term#1"]:
            resp = self.client.post("/api/v1/courses", {
                "code": "COMP2000", "name": "AI", "term": bad}, format="json")
            self.assertEqual(resp.status_code, 400, bad)
            fields = [d["field"] for d in resp.json()["error"]["details"]]
            self.assertIn("term", fields, bad)


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

    def test_section_code_rejects_symbols(self):
        self.client.force_authenticate(self.owner)
        for bad in ["!@#$", "01;drop", "L 01", "a*b"]:
            resp = self.client.post("/api/v1/sections", {
                "course": self.course.id, "section_code": bad}, format="json")
            self.assertEqual(resp.status_code, 400, bad)
            fields = [d["field"] for d in resp.json()["error"]["details"]]
            self.assertIn("section_code", fields, bad)
        self.assertEqual(CourseSection.objects.count(), 0)

    def test_section_code_allows_hyphen(self):
        self.client.force_authenticate(self.owner)
        resp = self.client.post("/api/v1/sections", {
            "course": self.course.id, "section_code": "lec-01"}, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["section_code"], "LEC-01")

    def test_owner_can_update_section_code_and_status(self):
        self.client.force_authenticate(self.owner)
        sec = CourseSection.objects.create(
            course=self.course, section_code="01", instructor=self.owner)
        resp = self.client.patch(f"/api/v1/sections/{sec.id}", {
            "section_code": "l02", "status": "ARCHIVED"}, format="json")
        self.assertEqual(resp.status_code, 200)
        sec.refresh_from_db()
        self.assertEqual(sec.section_code, "L02")  # 更新时也做规范化
        self.assertEqual(sec.status, "ARCHIVED")

    def test_update_still_rejects_symbols(self):
        self.client.force_authenticate(self.owner)
        sec = CourseSection.objects.create(
            course=self.course, section_code="01", instructor=self.owner)
        resp = self.client.patch(f"/api/v1/sections/{sec.id}", {
            "section_code": "0*1"}, format="json")
        self.assertEqual(resp.status_code, 400)
        sec.refresh_from_db()
        self.assertEqual(sec.section_code, "01")  # 未被污染

    def test_cannot_update_others_section(self):
        self.client.force_authenticate(self.other)
        sec = CourseSection.objects.create(
            course=self.course, section_code="01", instructor=self.owner)
        # other 的可见队列被 get_queryset 过滤掉该 section -> 404
        resp = self.client.patch(f"/api/v1/sections/{sec.id}", {
            "section_code": "hacked"}, format="json")
        self.assertEqual(resp.status_code, 404)
