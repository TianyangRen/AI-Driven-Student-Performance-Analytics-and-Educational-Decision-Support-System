from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

User = get_user_model()


class RegisterRoleEscalationTests(APITestCase):
    """自助注册不得自封 ADMIN：role 只读，一律落 INSTRUCTOR。"""

    def test_register_ignores_admin_role(self):
        resp = self.client.post("/api/v1/auth/register", {
            "username": "attacker",
            "password": "pw123456",
            "role": "ADMIN",  # 恶意提权尝试
        }, format="json")
        self.assertEqual(resp.status_code, 201)
        user = User.objects.get(username="attacker")
        self.assertEqual(user.role, "INSTRUCTOR")
        self.assertFalse(user.is_admin)

    def test_register_default_role_is_instructor(self):
        resp = self.client.post("/api/v1/auth/register", {
            "username": "teacher2",
            "password": "pw123456",
        }, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["data"]["user"]["role"], "INSTRUCTOR")
