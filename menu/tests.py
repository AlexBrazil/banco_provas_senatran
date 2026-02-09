from django.contrib.auth import get_user_model
from django.conf import settings
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from banco_questoes.models import AppModulo, Assinatura, Plano, PlanoPermissaoApp


class MenuSmokeTests(TestCase):
    def _protected_urls(self):
        return [
            reverse("menu:home"),
            reverse("simulado:inicio"),
            reverse("perguntas_respostas:index"),
            reverse("apostila_cnh:index"),
            reverse("simulacao_prova:index"),
            reverse("manual_pratico:index"),
            reverse("aprenda_jogando:index"),
            reverse("oraculo:index"),
            reverse("aprova_plus:index"),
        ]

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

    def test_root_is_menu_in_phase_b(self):
        user = get_user_model().objects.create_user(
            username="menu-user-3",
            email="menu3@example.com",
            password="safe-password-123",
        )
        self.client.force_login(user)
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Menu de Apps")

    def test_menu_alias_redirects_to_root_in_phase_b(self):
        response = self.client.get("/menu/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")

    def test_active_app_card_is_rendered_before_under_construction_cards(self):
        user = get_user_model().objects.create_user(
            username="menu-user-4",
            email="menu4@example.com",
            password="safe-password-123",
        )
        self.client.force_login(user)
        response = self.client.get(reverse("menu:home"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertLess(
            content.find("Simulado de Provas"),
            content.find("Perguntas e Respostas para Estudos"),
        )

    def test_all_phase_a_protected_routes_redirect_when_logged_out(self):
        for url in self._protected_urls():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn(settings.LOGIN_URL, response.url)

    def test_all_phase_a_routes_return_200_when_logged_in(self):
        user = get_user_model().objects.create_user(
            username="menu-user-5",
            email="menu5@example.com",
            password="safe-password-123",
        )
        self.client.force_login(user)
        for url in self._protected_urls():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

    @override_settings(APP_ACCESS_V2_ENABLED=True)
    def test_menu_shows_liberado_and_bloqueado_status_with_v2(self):
        user = get_user_model().objects.create_user(
            username="menu-user-6",
            email="menu6@example.com",
            password="safe-password-123",
        )
        plano = Plano.objects.create(nome="Plano Teste Menu V2")
        Assinatura.objects.create(
            usuario=user,
            plano=plano,
            nome_plano_snapshot=plano.nome,
            status=Assinatura.Status.ATIVO,
            inicio=timezone.now(),
            valid_until=None,
        )
        app_liberado = AppModulo.objects.create(
            slug="simulado-digital",
            nome="Simulado de Provas",
            ordem_menu=1,
            icone_path="menu_app/icons/icon_app_1.png",
            rota_nome="simulado:inicio",
            em_construcao=False,
            ativo=True,
        )
        app_bloqueado = AppModulo.objects.create(
            slug="oraculo",
            nome="Oraculo",
            ordem_menu=2,
            icone_path="menu_app/icons/icon_app_7.png",
            rota_nome="oraculo:index",
            em_construcao=False,
            ativo=True,
        )
        PlanoPermissaoApp.objects.create(
            plano=plano,
            app_modulo=app_liberado,
            permitido=True,
        )
        PlanoPermissaoApp.objects.create(
            plano=plano,
            app_modulo=app_bloqueado,
            permitido=False,
        )

        self.client.force_login(user)
        response = self.client.get(reverse("menu:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Liberado")
        self.assertContains(response, "Bloqueado pelo plano")

    @override_settings(APP_ACCESS_V2_ENABLED=True)
    def test_menu_blocked_card_is_not_clickable_with_v2(self):
        user = get_user_model().objects.create_user(
            username="menu-user-7",
            email="menu7@example.com",
            password="safe-password-123",
        )
        plano = Plano.objects.create(nome="Plano Teste Menu V2 Bloqueio")
        Assinatura.objects.create(
            usuario=user,
            plano=plano,
            nome_plano_snapshot=plano.nome,
            status=Assinatura.Status.ATIVO,
            inicio=timezone.now(),
            valid_until=None,
        )
        app_bloqueado = AppModulo.objects.create(
            slug="oraculo",
            nome="Oraculo",
            ordem_menu=1,
            icone_path="menu_app/icons/icon_app_7.png",
            rota_nome="oraculo:index",
            em_construcao=False,
            ativo=True,
        )
        PlanoPermissaoApp.objects.create(
            plano=plano,
            app_modulo=app_bloqueado,
            permitido=False,
        )

        self.client.force_login(user)
        response = self.client.get(reverse("menu:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-disabled="true"')
        self.assertNotContains(response, 'href="/oraculo/"')

    @override_settings(APP_ACCESS_V2_ENABLED=True)
    def test_menu_em_construcao_badge_when_liberado_but_under_construction(self):
        user = get_user_model().objects.create_user(
            username="menu-user-8",
            email="menu8@example.com",
            password="safe-password-123",
        )
        plano = Plano.objects.create(nome="Plano Teste Menu V2 EmConstrucao")
        Assinatura.objects.create(
            usuario=user,
            plano=plano,
            nome_plano_snapshot=plano.nome,
            status=Assinatura.Status.ATIVO,
            inicio=timezone.now(),
            valid_until=None,
        )
        app_em_construcao = AppModulo.objects.create(
            slug="oraculo",
            nome="Oraculo",
            ordem_menu=1,
            icone_path="menu_app/icons/icon_app_7.png",
            rota_nome="oraculo:index",
            em_construcao=True,
            ativo=True,
        )
        PlanoPermissaoApp.objects.create(
            plano=plano,
            app_modulo=app_em_construcao,
            permitido=True,
        )

        self.client.force_login(user)
        response = self.client.get(reverse("menu:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Em construcao")
        self.assertContains(response, 'href="/oraculo/"')
