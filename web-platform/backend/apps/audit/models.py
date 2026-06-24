from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    RESULT_CHOICES = [("SUCCESS", "SUCCESS"), ("FAILED", "FAILED")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=60)
    target_type = models.CharField(max_length=60, blank=True, null=True)
    target_id = models.BigIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    request_id = models.CharField(max_length=64, blank=True, null=True)
    result = models.CharField(max_length=20, choices=RESULT_CHOICES, default="SUCCESS")

    class Meta:
        db_table = "audit_log"
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["action", "-created_at"]),
        ]
