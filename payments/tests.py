from datetime import timedelta
import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from banco_questoes.models import Assinatura, EventoAuditoria, Plano
from payments.models import Billing
from payments.views import _ativar_plano_upgrade


class UpgradePixEligibilityTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="aluno@example.com",
            password="SenhaForte123!",
        )
        self.upgrade_plan = Plano.objects.create(
            nome="Aprova DETRAN",
            limite_qtd=None,
            limite_periodo=None,
            validade_dias=365,
            preco="9.90",
            ativo=True,
            permite_upgrade_pix=False,
        )
        self.url = reverse("payments:upgrade_free")

    def _login(self):
        self.client.login(username="aluno@example.com", password="SenhaForte123!")

    def _create_active_assinatura(self, plano: Plano):
        return Assinatura.objects.create(
            usuario=self.user,
            plano=plano,
            nome_plano_snapshot=plano.nome,
            limite_qtd_snapshot=plano.limite_qtd,
            limite_periodo_snapshot=plano.limite_periodo,
            validade_dias_snapshot=plano.validade_dias,
            ciclo_cobranca_snapshot=plano.ciclo_cobranca,
            preco_snapshot=plano.preco,
            status=Assinatura.Status.ATIVO,
            inicio=timezone.now() - timedelta(days=1),
            valid_until=timezone.now() + timedelta(days=30),
        )

    def test_upgrade_free_permite_plano_free_quando_flag_true(self):
        plano = Plano.objects.create(
            nome="Free",
            limite_qtd=25,
            limite_periodo=Plano.Periodo.SEMANAL,
            validade_dias=30,
            preco="0.00",
            ativo=True,
            permite_upgrade_pix=True,
        )
        self._create_active_assinatura(plano)
        self._login()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "payments/checkout_free_pix.html")
        self.assertContains(response, "Aprova DETRAN")

    def test_upgrade_free_permite_plano_nao_free_quando_flag_true(self):
        plano = Plano.objects.create(
            nome="Apostila_Free_cfc",
            limite_qtd=1,
            limite_periodo=Plano.Periodo.SEMANAL,
            validade_dias=365,
            preco="0.00",
            ativo=True,
            permite_upgrade_pix=True,
        )
        self._create_active_assinatura(plano)
        self._login()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "payments/checkout_free_pix.html")

    def test_upgrade_free_bloqueia_plano_com_flag_false(self):
        plano = Plano.objects.create(
            nome="Representante Viviane",
            limite_qtd=25,
            limite_periodo=Plano.Periodo.SEMANAL,
            validade_dias=30,
            preco="0.00",
            ativo=True,
            permite_upgrade_pix=False,
        )
        self._create_active_assinatura(plano)
        self._login()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Upgrade via PIX indisponivel")

    def test_upgrade_free_bloqueia_quando_usuario_ja_esta_no_plano_destino(self):
        self.upgrade_plan.permite_upgrade_pix = True
        self.upgrade_plan.save(update_fields=["permite_upgrade_pix", "atualizado_em"])
        self._create_active_assinatura(self.upgrade_plan)
        self._login()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "ja e o Aprova DETRAN")

    def test_ativar_plano_upgrade_registra_plano_origem_real(self):
        plano_origem = Plano.objects.create(
            nome="Apostila_Free_cfc",
            limite_qtd=1,
            limite_periodo=Plano.Periodo.SEMANAL,
            validade_dias=365,
            preco="0.00",
            ativo=True,
            permite_upgrade_pix=True,
        )
        self._create_active_assinatura(plano_origem)
        billing = Billing.objects.create(
            usuario=self.user,
            plano_destino=self.upgrade_plan,
            billing_ref=uuid.uuid4().hex,
            valor_centavos=990,
            status=Billing.Status.PAID,
        )

        _ativar_plano_upgrade(user=self.user, plano_upgrade=self.upgrade_plan, billing=billing)

        evento = EventoAuditoria.objects.filter(tipo="plano_trocado_pix").order_by("-id").first()
        self.assertIsNotNone(evento)
        self.assertEqual(evento.contexto_json.get("plano_origem"), "Apostila_Free_cfc")
