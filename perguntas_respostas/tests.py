from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from banco_questoes.models import (
    Alternativa,
    AppModulo,
    Assinatura,
    Curso,
    CursoModulo,
    Documento,
    Plano,
    PlanoPermissaoApp,
    Questao,
    UsoAppJanela,
)
from .models import PerguntaRespostaEstudo, PerguntaRespostaPreferenciaUsuario


class PerguntasRespostasFlowTests(TestCase):
    def _create_user(self, username: str = "pr-user", email: str = "pr@example.com"):
        return get_user_model().objects.create_user(
            username=username,
            email=email,
            password="safe-password-123",
        )

    def _seed_question(self):
        curso = Curso.objects.create(nome="Primeira Habilitacao", slug="primeira-habilitacao")
        modulo = CursoModulo.objects.create(
            curso=curso,
            ordem=1,
            nome="Sinalizacao",
            categoria=CursoModulo.Categoria.CONTEUDO,
            ativo=True,
        )
        documento = Documento.objects.create(titulo="Banco SENATRAN", ano=2025)
        questao = Questao.objects.create(
            curso=curso,
            modulo=modulo,
            documento=documento,
            numero_no_modulo=1,
            dificuldade=Questao.Dificuldade.FACIL,
            enunciado="Qual e o significado da placa R-1?",
            comentario="Indica parada obrigatoria.",
            codigo_placa="R-1",
            imagem_arquivo="R-1.png",
        )
        Alternativa.objects.create(
            questao=questao,
            texto="Parada obrigatoria",
            is_correta=True,
            ordem=1,
        )
        Alternativa.objects.create(
            questao=questao,
            texto="Proibido estacionar",
            is_correta=False,
            ordem=2,
        )
        return curso, modulo, questao

    def _seed_two_questions(self):
        curso = Curso.objects.create(nome="Primeira Habilitacao", slug="primeira-habilitacao")
        modulo = CursoModulo.objects.create(
            curso=curso,
            ordem=1,
            nome="Sinalizacao",
            categoria=CursoModulo.Categoria.CONTEUDO,
            ativo=True,
        )
        documento = Documento.objects.create(titulo="Banco SENATRAN", ano=2025)

        q1 = Questao.objects.create(
            curso=curso,
            modulo=modulo,
            documento=documento,
            numero_no_modulo=1,
            dificuldade=Questao.Dificuldade.FACIL,
            enunciado="Pergunta 1",
            comentario="Comentario 1",
            codigo_placa="R-1",
            imagem_arquivo="R-1.png",
        )
        Alternativa.objects.create(questao=q1, texto="Resposta 1", is_correta=True, ordem=1)
        Alternativa.objects.create(questao=q1, texto="Distrator 1", is_correta=False, ordem=2)

        q2 = Questao.objects.create(
            curso=curso,
            modulo=modulo,
            documento=documento,
            numero_no_modulo=2,
            dificuldade=Questao.Dificuldade.FACIL,
            enunciado="Pergunta 2",
            comentario="Comentario 2",
            codigo_placa="R-2",
            imagem_arquivo="R-2.png",
        )
        Alternativa.objects.create(questao=q2, texto="Resposta 2", is_correta=True, ordem=1)
        Alternativa.objects.create(questao=q2, texto="Distrator 2", is_correta=False, ordem=2)
        return curso, modulo, q1, q2

    def _seed_access_rule_v2(self, user, *, permitido: bool, limite_qtd: int | None, limite_periodo: str | None):
        plano = Plano.objects.create(nome=f"Plano PR V2 {user.id}")
        Assinatura.objects.create(
            usuario=user,
            plano=plano,
            nome_plano_snapshot=plano.nome,
            status=Assinatura.Status.ATIVO,
            inicio=timezone.now(),
            valid_until=None,
        )
        app = AppModulo.objects.create(
            slug="perguntas-respostas",
            nome="Perguntas e Respostas para Estudos",
            ordem_menu=2,
            icone_path="menu_app/icons/icon_app_2.png",
            rota_nome="perguntas_respostas:index",
            em_construcao=False,
            ativo=True,
        )
        PlanoPermissaoApp.objects.create(
            plano=plano,
            app_modulo=app,
            permitido=permitido,
            limite_qtd=limite_qtd,
            limite_periodo=limite_periodo,
        )

    def test_index_requires_login(self):
        response = self.client.get(reverse("perguntas_respostas:index"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_logged_user_can_start_and_register_estudo(self):
        user = self._create_user()
        self._seed_question()
        self.client.force_login(user)

        start_resp = self.client.post(
            reverse("perguntas_respostas:iniciar"),
            {"qtd_questoes": "1", "study_mode": "manual", "voice_enabled": "0"},
        )
        self.assertEqual(start_resp.status_code, 302)
        self.assertIn("/perguntas-respostas/estudar/", start_resp.url)

        study_resp = self.client.get(start_resp.url)
        self.assertEqual(study_resp.status_code, 200)
        self.assertContains(study_resp, "Resposta correta")
        self.assertContains(study_resp, "Comentario")
        self.assertEqual(PerguntaRespostaEstudo.objects.filter(usuario=user).count(), 1)

    def test_save_tempo_preferencia(self):
        user = self._create_user(username="pr-pref", email="pr-pref@example.com")
        self.client.force_login(user)
        response = self.client.post(reverse("perguntas_respostas:salvar_tempo"), {"tempo": "19", "modo_automatico": "1"})
        self.assertEqual(response.status_code, 200)
        pref = PerguntaRespostaPreferenciaUsuario.objects.get(usuario=user)
        self.assertEqual(pref.tempo_entre_questoes_segundos, 19)
        self.assertTrue(pref.modo_automatico_ativo)

    def test_estudar_advances_to_second_question_with_pos_query(self):
        user = self._create_user(username="pr-pos", email="pr-pos@example.com")
        self._seed_two_questions()
        self.client.force_login(user)

        start_resp = self.client.post(
            reverse("perguntas_respostas:iniciar"),
            {"qtd_questoes": "2", "study_mode": "manual", "voice_enabled": "0"},
        )
        self.assertEqual(start_resp.status_code, 302)
        self.assertIn("?pos=0", start_resp.url)

        first_resp = self.client.get(start_resp.url)
        self.assertEqual(first_resp.status_code, 200)
        self.assertContains(first_resp, "Pergunta 1")
        self.assertContains(first_resp, "Questao 1 de 2")

        second_url = start_resp.url.replace("?pos=0", "?pos=1")
        second_resp = self.client.get(second_url)
        self.assertEqual(second_resp.status_code, 200)
        self.assertContains(second_resp, "Pergunta 2")
        self.assertContains(second_resp, "Questao 2 de 2")

    def test_estudar_preserves_auto_on_navigation_urls(self):
        user = self._create_user(username="pr-state", email="pr-state@example.com")
        self._seed_two_questions()
        self.client.force_login(user)

        start_resp = self.client.post(
            reverse("perguntas_respostas:iniciar"),
            {"qtd_questoes": "2", "study_mode": "manual", "voice_enabled": "0"},
        )
        self.assertEqual(start_resp.status_code, 302)

        state_url = f"{start_resp.url}&auto=1"
        response = self.client.get(state_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "?pos=1&amp;auto=1")

    @override_settings(APP_ACCESS_V2_ENABLED=True)
    def test_index_with_v2_respects_plan_permission(self):
        user = self._create_user(username="pr-v2", email="pr-v2@example.com")
        self._seed_access_rule_v2(user, permitido=False, limite_qtd=2, limite_periodo=Plano.Periodo.DIARIO)

        self.client.force_login(user)
        response = self.client.get(reverse("perguntas_respostas:index"))
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Acesso bloqueado")

    @override_settings(APP_ACCESS_V2_ENABLED=True)
    def test_v2_consumes_credit_only_when_starting_session(self):
        user = self._create_user(username="pr-v2-consume", email="pr-v2-consume@example.com")
        self._seed_question()
        self._seed_access_rule_v2(user, permitido=True, limite_qtd=2, limite_periodo=Plano.Periodo.DIARIO)
        self.client.force_login(user)

        index_response = self.client.get(reverse("perguntas_respostas:index"))
        self.assertEqual(index_response.status_code, 200)
        self.assertEqual(UsoAppJanela.objects.filter(usuario=user, app_modulo__slug="perguntas-respostas").count(), 0)

        start_response = self.client.post(
            reverse("perguntas_respostas:iniciar"),
            {"qtd_questoes": "1"},
        )
        self.assertEqual(start_response.status_code, 302)

        uso = UsoAppJanela.objects.get(usuario=user, app_modulo__slug="perguntas-respostas")
        self.assertEqual(uso.contador, 1)

        study_response = self.client.get(start_response.url)
        self.assertEqual(study_response.status_code, 200)
        uso.refresh_from_db()
        self.assertEqual(uso.contador, 1)

    @override_settings(APP_ACCESS_V2_ENABLED=True)
    def test_v2_blocks_on_new_start_after_limit(self):
        user = self._create_user(username="pr-v2-limit", email="pr-v2-limit@example.com")
        self._seed_question()
        self._seed_access_rule_v2(user, permitido=True, limite_qtd=1, limite_periodo=Plano.Periodo.DIARIO)
        self.client.force_login(user)

        first_start = self.client.post(reverse("perguntas_respostas:iniciar"), {"qtd_questoes": "1"})
        self.assertEqual(first_start.status_code, 302)
        study_response = self.client.get(first_start.url)
        self.assertEqual(study_response.status_code, 200)

        second_start = self.client.post(reverse("perguntas_respostas:iniciar"), {"qtd_questoes": "1"})
        self.assertEqual(second_start.status_code, 403)
        self.assertContains(second_start, "Limite de uso atingido")
