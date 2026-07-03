import io

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.courses.models import (
    Assessment,
    AssessmentScore,
    Course,
    CourseSection,
    Enrollment,
    Student,
    StudentActivity,
)
from .models import ImportBatch

User = get_user_model()


def _csv_upload(name, text):
    return io.BytesIO(text.encode("utf-8")), name


class ImportFlowTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="teacher", password="pw123456")
        self.client.force_authenticate(self.user)
        self.course = Course.objects.create(code="COMP8567", name="AI", term="S26", owner=self.user)
        self.section = CourseSection.objects.create(
            course=self.course, section_code="01", instructor=self.user)

    def _upload(self, import_type, filename, text):
        buf = io.BytesIO(text.encode("utf-8"))
        buf.name = filename
        return self.client.post(
            f"/api/v1/sections/{self.section.id}/imports",
            {"file": buf, "import_type": import_type},
            format="multipart",
        )

    # ---------- ROSTER ----------
    def test_roster_happy_path(self):
        text = "student_no,full_name,email\nS-001,Alice,a@x.com\nS-002,Bob,b@x.com\n"
        resp = self._upload("ROSTER", "roster.csv", text)
        self.assertEqual(resp.status_code, 201)
        data = resp.json()["data"]
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["valid_rows"], 2)
        self.assertEqual(Student.objects.count(), 2)
        self.assertEqual(Enrollment.objects.filter(section=self.section).count(), 2)
        # anonymized_code 自动生成
        self.assertTrue(Student.objects.get(student_no="S-001").anonymized_code.startswith("S-ANON-"))

    def test_roster_missing_column_fails(self):
        text = "full_name,email\nAlice,a@x.com\n"  # 缺 student_no
        resp = self._upload("ROSTER", "roster.csv", text)
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(Student.objects.count(), 0)
        batch = ImportBatch.objects.latest("id")
        self.assertEqual(batch.status, "FAILED")

    # ---------- SCORE ----------
    def _seed_roster(self):
        self._upload("ROSTER", "roster.csv",
                     "student_no,full_name,email\nS-001,Alice,a@x.com\nS-002,Bob,b@x.com\n")

    def test_score_happy_path_computes_percentage(self):
        self._seed_roster()
        text = ("student_no,assessment_name,assessment_type,max_score,weight,week_no,score\n"
                "S-001,Quiz 1,QUIZ,50,5,1,40\n"
                "S-002,Quiz 1,QUIZ,50,5,1,25\n")
        resp = self._upload("SCORE", "score.csv", text)
        self.assertEqual(resp.status_code, 201)
        data = resp.json()["data"]
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["valid_rows"], 2)
        self.assertEqual(Assessment.objects.filter(section=self.section).count(), 1)
        score = AssessmentScore.objects.get(student__student_no="S-001")
        self.assertEqual(float(score.percentage), 80.0)  # 40/50*100

    def test_score_partial_bad_and_unknown_student(self):
        self._seed_roster()
        text = ("student_no,assessment_name,assessment_type,max_score,weight,week_no,score\n"
                "S-001,Quiz 1,QUIZ,50,5,1,40\n"      # ok
                "S-002,Quiz 1,QUIZ,50,5,1,abc\n"     # score 非数字
                "S-999,Quiz 1,QUIZ,50,5,1,30\n")     # 不在名单
        resp = self._upload("SCORE", "score.csv", text)
        data = resp.json()["data"]
        self.assertEqual(data["status"], "PARTIAL")
        self.assertEqual(data["valid_rows"], 1)
        self.assertEqual(data["error_count"], 2)
        # 拉错误明细
        err = self.client.get(f"/api/v1/imports/{data['batch_id']}/errors").json()["data"]["errors"]
        reasons = {(e["row"], e["column"]) for e in err}
        self.assertIn((3, "score"), reasons)
        self.assertIn((4, "student_no"), reasons)

    def test_score_exceeds_max(self):
        self._seed_roster()
        text = ("student_no,assessment_name,assessment_type,max_score,weight,week_no,score\n"
                "S-001,Quiz 1,QUIZ,50,5,1,60\n")  # score > max
        resp = self._upload("SCORE", "score.csv", text)
        data = resp.json()["data"]
        self.assertEqual(data["status"], "FAILED")
        self.assertEqual(data["valid_rows"], 0)

    # ---------- ACTIVITY ----------
    def test_activity_happy_path(self):
        self._seed_roster()
        text = ("student_no,activity_date,activity_type,metric_value\n"
                "S-001,2026-06-15,ATTENDANCE,1\n")
        resp = self._upload("ACTIVITY", "act.csv", text)
        data = resp.json()["data"]
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(StudentActivity.objects.count(), 1)

    def test_activity_bad_date_partial(self):
        self._seed_roster()
        text = ("student_no,activity_date,activity_type,metric_value\n"
                "S-001,2026-06-15,ATTENDANCE,1\n"
                "S-002,15/06/2026,ATTENDANCE,1\n")  # 日期格式错
        resp = self._upload("ACTIVITY", "act.csv", text)
        data = resp.json()["data"]
        self.assertEqual(data["status"], "PARTIAL")
        self.assertEqual(data["valid_rows"], 1)

    # ---------- 模板下载 ----------
    def test_template_download_csv(self):
        resp = self.client.get("/api/v1/imports/template?type=SCORE&fmt=csv")
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode("utf-8-sig")
        self.assertIn("assessment_type", body.splitlines()[0])

    def test_template_download_xlsx(self):
        resp = self.client.get("/api/v1/imports/template?type=ROSTER&fmt=xlsx")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("spreadsheetml", resp["Content-Type"])

    def test_template_bad_type(self):
        resp = self.client.get("/api/v1/imports/template?type=NOPE")
        self.assertEqual(resp.status_code, 422)
