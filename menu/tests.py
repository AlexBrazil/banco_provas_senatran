from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class MenuSmokeTests(TestCase):
    def test_menu_requires_login(self):
        response = self.client.get(reverse("menu:home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_menu_returns_200_for_authenticated_user(self):
        user = get_user_model().objects.create_user(
            username="menu-user",
            email="menu@example.com",
            password="safe-password-123",
        )
        self.client.force_login(user)
        response = self.client.get(reverse("menu:home"))
        self.assertEqual(response.status_code, 200)
