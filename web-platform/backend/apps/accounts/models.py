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

    @property
    def is_admin(self) -> bool:
        """业务层的最高权限：显式 ADMIN 角色，或 Django 超级用户。"""
        return self.role == "ADMIN" or self.is_superuser
