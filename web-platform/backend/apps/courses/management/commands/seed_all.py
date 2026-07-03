"""一键初始化演示环境：账号 + 课程 + 教学班 + 学生数据 + 预测。

新机器 clone 代码后：
    python manage.py migrate      # 建表
    python manage.py seed_all     # 灌入完整可用的演示数据

本命令负责创建【基础实体】（超级用户、教师、课程、教学班），再调用
seed_demo 填充【学生/成绩/出勤/预测】。全程幂等，可反复运行。

注意：数据库文件 db.sqlite3 不入库（.gitignore），所以数据不会随代码下载——
必须靠本命令重建。真实预测需要 ML 服务(:8000) 在线；不在线时 seed_demo 会
自动降级为 mock 风险，应用照样可用。
"""
from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.courses.models import Course, CourseSection

# 7 门课，每门 2 个 section（与既有演示数据一致）
COURSES = [
    ("COMP8117", "Advanced Software Engineering Topics"),
    ("COMP8157", "Advanced Database Topics"),
    ("COMP8547", "Advanced Computing Concepts"),
    ("COMP8347", "Internet Applications and Distributed Systems"),
    ("COMP8567", "Advanced Systems Programming"),
    ("COMP8967", "Advanced Software Quality Assurance"),
    ("COMP8677", "Advanced Computer Networks"),
]
TERM = "2025 Winter"
INSTRUCTORS = [
    ("TeacherA", "Teacher A"), ("TeacherB", "Teacher B"),
    ("TeacherC", "Teacher C"), ("TeacherD", "Teacher D"),
    ("TeacherE", "Teacher E"), ("TeacherF", "Teacher F"),
]


class Command(BaseCommand):
    help = "一键初始化演示环境（账号 + 课程 + 教学班 + 学生数据 + 预测）。"

    def add_arguments(self, parser):
        parser.add_argument("--admin", default="superuser", help="超级用户名")
        parser.add_argument("--password", default="Passw0rd!", help="所有演示账号的默认密码")
        parser.add_argument("--students", type=int, default=26, help="每个 section 的学生数")
        parser.add_argument("--no-predict", action="store_true", help="不自动跑预测")
        parser.add_argument("--reset-password", action="store_true",
                            help="已存在的账号也重置为默认密码")

    def handle(self, *args, **opts):
        password = opts["password"]
        reset = opts["reset_password"]

        admin = self._ensure_user(opts["admin"], "Administrator", password, reset,
                                  role="ADMIN", is_staff=True, is_superuser=True)
        instructors = [
            self._ensure_user(u, full, password, reset, role="INSTRUCTOR")
            for u, full in INSTRUCTORS
        ]
        self.stdout.write(self.style.SUCCESS(
            f"账号就绪：1 超级用户 + {len(instructors)} 教师（密码 {password}）"
        ))

        self._ensure_courses_sections(admin, instructors)
        n_sec = CourseSection.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"课程/教学班就绪：{Course.objects.count()} 课 · {n_sec} 教学班"
        ))

        # 复用 seed_demo 填充学生/成绩/出勤/预测（幂等）
        self.stdout.write("填充学生数据…")
        call_command("seed_demo", students=opts["students"], no_predict=opts["no_predict"])

        self.stdout.write(self.style.SUCCESS("\n✔ 初始化完成。登录信息："))
        self.stdout.write(f"    管理员：{opts['admin']} / {password}")
        self.stdout.write(f"    教师  ：TeacherA … TeacherF / {password}")

    # ------------------------------------------------------------------ #
    def _ensure_user(self, username, full_name, password, reset,
                     role="INSTRUCTOR", is_staff=False, is_superuser=False):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"role": role, "full_name": full_name,
                      "is_staff": is_staff, "is_superuser": is_superuser},
        )
        if created or reset:
            user.set_password(password)
            user.role = role
            user.full_name = full_name
            user.is_staff = is_staff
            user.is_superuser = is_superuser
            user.save()
        return user

    @transaction.atomic
    def _ensure_courses_sections(self, admin, instructors):
        for i, (code, name) in enumerate(COURSES):
            course, _ = Course.objects.get_or_create(
                code=code, term=TERM, owner=admin,
                defaults={"name": name},
            )
            for j, section_code in enumerate(("01", "02")):
                instructor = instructors[(i + j) % len(instructors)]
                CourseSection.objects.get_or_create(
                    course=course, section_code=section_code,
                    defaults={"instructor": instructor, "status": "ACTIVE"},
                )
