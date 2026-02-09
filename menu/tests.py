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

    def test_menu_card_simulado_points_to_canonical_url(self):
        user = get_user_model().objects.create_user(
            username="menu-user-2",
            email="menu2@example.com",
            password="safe-password-123",
        )
        self.client.force_login(user)
        response = self.client.get(reverse("menu:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/simulado/"')

    def test_legacy_root_kept_as_fallback_for_phase_a(self):
        user = get_user_model().objects.create_user(
            username="menu-user-3",
            email="menu3@example.com",
            password="safe-password-123",
        )
        self.client.force_login(user)
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
