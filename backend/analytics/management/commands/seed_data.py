"""Populate the database with sample students, assessments, and predictions
so you have something to look at.

    python manage.py seed_data            # add ~12 sample students
    python manage.py seed_data --clear    # wipe existing data first
"""
import random

from django.core.management.base import BaseCommand

from analytics.ml.service import MLService
from analytics.models import Assessment, RiskPrediction, Student

FIRST_NAMES = ["Alex", "Sam", "Jordan", "Taylor", "Casey", "Riley",
               "Morgan", "Jamie", "Avery", "Quinn", "Drew", "Reese"]
GROUPS = ["A", "B", "C"]


class Command(BaseCommand):
    help = "Seed sample students, assessments, and risk predictions."

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true",
                            help="Delete existing data before seeding.")
        parser.add_argument("--n", type=int, default=12,
                            help="Number of students to create.")

    def handle(self, *args, **opts):
        if opts["clear"]:
            RiskPrediction.objects.all().delete()
            Assessment.objects.all().delete()
            Student.objects.all().delete()
            self.stdout.write(self.style.WARNING("Cleared existing data."))

        rng = random.Random(42)
        created = 0
        for i in range(opts["n"]):
            sid = f"S{1000 + i}"
            student, was_new = Student.objects.get_or_create(
                student_id=sid,
                defaults={
                    "name": f"{FIRST_NAMES[i % len(FIRST_NAMES)]} {sid}",
                    "group": rng.choice(GROUPS),
                    "semester": "2026-Spring",
                },
            )
            if not was_new:
                continue

            # Some students strong, some weak -> varied risk.
            base = rng.uniform(35, 90)
            feats = {
                "quiz_avg": max(0, min(100, base + rng.uniform(-10, 10))),
                "lab_avg": max(0, min(100, base + rng.uniform(-10, 10))),
                "assignment_avg": max(0, min(100, base + rng.uniform(-10, 10))),
                "midterm": max(0, min(100, base + rng.uniform(-15, 10))),
                "participation": max(0, min(100, base + rng.uniform(-20, 20))),
                "days_since_login": rng.uniform(0, 25),
            }
            for t in ["quiz", "lab", "assignment", "midterm"]:
                Assessment.objects.create(
                    student=student, type=t,
                    score=round(feats[f"{t}_avg" if t != "midterm" else "midterm"], 1),
                    week=rng.randint(1, 12),
                )

            result = MLService.predict(feats)
            RiskPrediction.objects.create(
                student=student,
                risk_score=result["risk_score"],
                risk_level=result["risk_level"],
                model_version=result["model_version"],
                explanation=result.get("explanation", {}),
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {created} students with assessments and predictions."
        ))
