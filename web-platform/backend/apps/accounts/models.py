from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ("INSTRUCTOR", "Instructor"),
        ("ADMIN", "Administrator"),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="INSTRUCTOR")
    full_name = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = "account_user"

    def __str__(self):
        return f"{self.username} ({self.role})"
