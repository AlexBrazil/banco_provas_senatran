from __future__ import annotations

import json
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

import fitz  # PyMuPDF
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from banco_questoes.models import AppModulo, Assinatura, Plano, PlanoPermissaoApp, UsoAppJanela

from .models import ApostilaDocumento, ApostilaPagina, ApostilaProgressoLeitura
from .services.ingestao_pdf import normalizar_texto_busca
from .storage import PrivateApostilaStorage


class ApostilaAccessBaseTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="apostila-user",
            email="apostila-user@example.com",
            password="safe-password-123",
        )
        self.app_modulo = AppModulo.objects.create(
            slug="apostila-cnh",
            nome="Apostila CNH",
            ativo=True,
            ordem_menu=10,
            rota_nome="apostila_cnh:index",
            em_construcao=False,
        )

    def criar_assinatura_com_permissao(self, *, permitido: bool, limite_qtd=5):
        plano = Plano.objects.create(nome=f"Plano Apostila {self._testMethodName}")
        assinatura = Assinatura.objects.create(
            usuario=self.user,
            plano=plano,
            nome_plano_snapshot=plano.nome,
            status=Assinatura.Status.ATIVO,
            inicio=timezone.now(),
            valid_until=None,
        )
        PlanoPermissaoApp.objects.create(
            plano=plano,
            app_modulo=self.app_modulo,
            permitido=permitido,
            limite_qtd=limite_qtd,
            limite_periodo=Plano.Periodo.MENSAL if limite_qtd is not None else None,
        )
        return assinatura

    def criar_documento_ativo(self, *, slug="apostila-cnh-brasil", total_paginas=20):
        return ApostilaDocumento.objects.create(
            slug=slug,
            titulo="Apostila CNH Brasil",
            arquivo_pdf=f"{slug}.pdf",
            ativo=True,
            total_paginas=total_paginas,
        )


@override_settings(APP_ACCESS_V2_ENABLED=True)
class ApostilaCnhAccessTests(ApostilaAccessBaseTestCase):
    def test_index_blocks_when_user_has_no_active_assinatura(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("apostila_cnh:index"))

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Assinatura inativa ou expirada.")

    def test_index_blocks_when_plan_does_not_allow_app(self):
        self.criar_assinatura_com_permissao(permitido=False)
        self.client.force_login(self.user)

        response = self.client.get(reverse("apostila_cnh:index"))

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Este modulo nao esta liberado no seu plano.")

    def test_index_consumes_credit_and_internal_api_does_not_consume(self):
        self.criar_assinatura_com_permissao(permitido=True, limite_qtd=5)
        self.client.force_login(self.user)

        index_response = self.client.get(reverse("apostila_cnh:index"))
        self.assertEqual(index_response.status_code, 200)

        uso = UsoAppJanela.objects.get(usuario=self.user, app_modulo=self.app_modulo)
        self.assertEqual(uso.contador, 1)

        api_response = self.client.get(reverse("apostila_cnh:api_documento_ativo"))
        self.assertEqual(api_response.status_code, 404)

        uso.refresh_from_db()
        self.assertEqual(uso.contador, 1)


@override_settings(APP_ACCESS_V2_ENABLED=True)
class ApostilaCnhProgressoApiTests(ApostilaAccessBaseTestCase):
    def setUp(self):
        super().setUp()
        self.criar_assinatura_com_permissao(permitido=True, limite_qtd=10)
        self.documento = self.criar_documento_ativo(total_paginas=30)
        self.client.force_login(self.user)

    def test_get_progresso_returns_default_page_when_empty(self):
        response = self.client.get(reverse("apostila_cnh:api_progresso"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["progresso"]["ultima_pagina_lida"], 1)
        self.assertEqual(payload["progresso"]["total_paginas_documento"], 30)

    def test_post_progresso_updates_progress(self):
        response = self.client.post(
            reverse("apostila_cnh:api_progresso"),
            data=json.dumps({"pagina": 7}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["progresso"]["ultima_pagina_lida"], 7)

        progresso = ApostilaProgressoLeitura.objects.get(usuario=self.user, documento=self.documento)
        self.assertEqual(progresso.ultima_pagina_lida, 7)

    def test_post_progresso_rejects_invalid_payloads(self):
        invalid_cases = [
            ({}, "Campo 'pagina' e obrigatorio."),
            ({"pagina": "abc"}, "Campo 'pagina' deve ser inteiro."),
            ({"pagina": 0}, "Campo 'pagina' deve ser >= 1."),
            ({"pagina": 999}, "Campo 'pagina' deve ser <= 30."),
        ]

        for body, expected_error in invalid_cases:
            with self.subTest(body=body):
                response = self.client.post(
                    reverse("apostila_cnh:api_progresso"),
                    data=json.dumps(body),
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"], expected_error)

    def test_post_progresso_rejects_invalid_json(self):
        response = self.client.post(
            reverse("apostila_cnh:api_progresso"),
            data="{json-invalido",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "JSON invalido.")


@override_settings(APP_ACCESS_V2_ENABLED=True)
class ApostilaCnhBuscaApiTests(ApostilaAccessBaseTestCase):
    def setUp(self):
        super().setUp()
        self.criar_assinatura_com_permissao(permitido=True, limite_qtd=10)
        self.documento_ativo = self.criar_documento_ativo(slug="doc-ativo", total_paginas=50)
        self.documento_inativo = ApostilaDocumento.objects.create(
            slug="doc-inativo",
            titulo="Apostila Inativa",
            arquivo_pdf="doc-inativo.pdf",
            ativo=False,
            total_paginas=50,
        )
        texto_ativo = "Seguranca no transito e prioridade nacional."
        texto_inativo = "termo-exclusivo-inativo deve ficar invisivel para a busca."
        ApostilaPagina.objects.create(
            documento=self.documento_ativo,
            numero_pagina=4,
            texto=texto_ativo,
            texto_normalizado=normalizar_texto_busca(texto_ativo),
        )
        ApostilaPagina.objects.create(
            documento=self.documento_inativo,
            numero_pagina=7,
            texto=texto_inativo,
            texto_normalizado=normalizar_texto_busca(texto_inativo),
        )
        self.client.force_login(self.user)

    def test_busca_requires_non_empty_q(self):
        response = self.client.get(reverse("apostila_cnh:api_busca"), {"q": "   "})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Parametro 'q' e obrigatorio.")

    def test_busca_returns_results_from_active_document_only(self):
        response = self.client.get(reverse("apostila_cnh:api_busca"), {"q": "seguranca"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["total_resultados"], 1)
        self.assertEqual(payload["resultados"][0]["pagina"], 4)

        response_inativo = self.client.get(
            reverse("apostila_cnh:api_busca"),
            {"q": "termo-exclusivo-inativo"},
        )
        self.assertEqual(response_inativo.status_code, 200)
        payload_inativo = response_inativo.json()
        self.assertEqual(payload_inativo["total_resultados"], 0)


class ImportApostilaPdfCommandSmokeTests(TestCase):
    @contextmanager
    def _temporary_storage(self, location: Path):
        field = ApostilaDocumento._meta.get_field("arquivo_pdf")
        previous_storage = field.storage
        field.storage = PrivateApostilaStorage(location=str(location))
        try:
            yield
        finally:
            field.storage = previous_storage

    def _create_sample_pdf(self, path: Path):
        pdf = fitz.open()
        page1 = pdf.new_page()
        page1.insert_text((72, 72), "Pagina 1: conteudo de transito.")
        page2 = pdf.new_page()
        page2.insert_text((72, 72), "Pagina 2: conducao defensiva.")
        pdf.save(path)
        pdf.close()

    def test_import_command_is_idempotent_for_same_pdf(self):
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_pdf = temp_path / "apostila_origem.pdf"
            storage_root = temp_path / "storage_privado"
            self._create_sample_pdf(source_pdf)

            with self._temporary_storage(storage_root):
                output_first = StringIO()
                call_command(
                    "import_apostila_pdf",
                    slug="apostila-cnh-brasil",
                    pdf_path=str(source_pdf),
                    titulo="Apostila CNH Brasil",
                    ativar=True,
                    stdout=output_first,
                )

                documento = ApostilaDocumento.objects.get(slug="apostila-cnh-brasil")
                self.assertTrue(documento.ativo)
                self.assertEqual(documento.total_paginas, 2)
                self.assertEqual(ApostilaPagina.objects.filter(documento=documento).count(), 2)
                self.assertIn("Criado agora: SIM", output_first.getvalue())
                self.assertIn("Paginas criadas: 2", output_first.getvalue())

                output_second = StringIO()
                call_command(
                    "import_apostila_pdf",
                    slug="apostila-cnh-brasil",
                    pdf_path=str(source_pdf),
                    titulo="Apostila CNH Brasil",
                    ativar=True,
                    stdout=output_second,
                )

                documento.refresh_from_db()
                self.assertEqual(documento.total_paginas, 2)
                self.assertEqual(ApostilaPagina.objects.filter(documento=documento).count(), 2)
                self.assertIn("Criado agora: NAO", output_second.getvalue())
                self.assertIn("Paginas criadas: 0", output_second.getvalue())
                self.assertIn("Paginas atualizadas: 2", output_second.getvalue())
