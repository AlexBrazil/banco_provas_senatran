from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from banco_questoes.models import Assinatura, ConviteCadastroPlano, Plano


@override_settings(REGISTER_COOLDOWN_ENABLED=False)
class CadastroPlanoTests(TestCase):
    def setUp(self):
        self.plano_free = Plano.objects.create(
            nome="Free",
            limite_qtd=3,
            limite_periodo=Plano.Periodo.DIARIO,
            validade_dias=30,
            preco="0.00",
            ativo=True,
        )
        self.plano_premium = Plano.objects.create(
            nome="Parceiro Premium",
            limite_qtd=None,
            limite_periodo=None,
            validade_dias=365,
            preco="9.90",
            ativo=True,
        )

    def test_registro_padrao_cria_assinatura_free(self):
        response = self.client.post(
            reverse("register"),
            data={
                "username": "aluno.free@example.com",
                "password1": "SenhaForte123!",
                "password2": "SenhaForte123!",
            },
        )
        self.assertEqual(response.status_code, 302)
        assinatura = Assinatura.objects.order_by("-id").first()
        self.assertIsNotNone(assinatura)
        self.assertEqual(assinatura.plano_id, self.plano_free.id)

    def test_registro_parceiro_com_token_valido_cria_plano_da_campanha(self):
        convite = ConviteCadastroPlano.objects.create(
            plano=self.plano_premium,
            ativo=True,
            inicio_vigencia=timezone.now() - timedelta(hours=1),
            fim_vigencia=timezone.now() + timedelta(hours=1),
            limite_usos=3,
            usos_realizados=0,
        )
        response = self.client.post(
            reverse("register_partner", kwargs={"token": convite.token}),
            data={
                "username": "aluno.parceiro@example.com",
                "password1": "SenhaForte123!",
                "password2": "SenhaForte123!",
            },
        )
        self.assertEqual(response.status_code, 302)
        assinatura = Assinatura.objects.order_by("-id").first()
        self.assertIsNotNone(assinatura)
        self.assertEqual(assinatura.plano_id, self.plano_premium.id)
        convite.refresh_from_db()
        self.assertEqual(convite.usos_realizados, 1)

    def test_registro_parceiro_invalido_redireciona_para_registro_padrao(self):
        response = self.client.get(reverse("register_partner", kwargs={"token": "token-invalido"}))
        self.assertRedirects(response, reverse("register"))

    def test_registro_parceiro_sem_saldo_redireciona_para_registro_padrao(self):
        convite = ConviteCadastroPlano.objects.create(
            plano=self.plano_premium,
            ativo=True,
            inicio_vigencia=timezone.now() - timedelta(hours=1),
            fim_vigencia=timezone.now() + timedelta(hours=1),
            limite_usos=1,
            usos_realizados=1,
        )
        response = self.client.get(reverse("register_partner", kwargs={"token": convite.token}))
        self.assertRedirects(response, reverse("register"))

    def test_registro_parceiro_sem_saldo_sem_fallback_exibe_tela_informativa(self):
        convite = ConviteCadastroPlano.objects.create(
            plano=self.plano_premium,
            ativo=True,
            permitir_fallback_free=False,
            inicio_vigencia=timezone.now() - timedelta(hours=1),
            fim_vigencia=timezone.now() + timedelta(hours=1),
            limite_usos=1,
            usos_realizados=1,
        )
        response = self.client.get(reverse("register_partner", kwargs={"token": convite.token}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/register_partner_unavailable.html")
        self.assertContains(response, "nao possui mais creditos")

    def test_login_parceiro_exibe_identidade_visual(self):
        convite = ConviteCadastroPlano.objects.create(
            plano=self.plano_premium,
            ativo=True,
            nome_representante="Representante Viviane",
            logo_url="https://exemplo.com/logo-viviane.png",
        )
        response = self.client.get(reverse("login_partner", kwargs={"token": convite.token}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Representante Viviane")
        self.assertContains(response, "https://exemplo.com/logo-viviane.png")
