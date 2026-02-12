from __future__ import annotations

from django.conf import settings
from django.db import models


class PerguntaRespostaPreferenciaUsuario(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perguntas_respostas_preferencia",
    )
    tempo_entre_questoes_segundos = models.PositiveSmallIntegerField(default=12)
    modo_automatico_ativo = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Preferencia Perguntas e Respostas"
        verbose_name_plural = "Preferencias Perguntas e Respostas"

    def __str__(self) -> str:
        return f"{self.usuario} :: {self.tempo_entre_questoes_segundos}s"


class PerguntaRespostaEstudo(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perguntas_respostas_estudos",
    )
    questao = models.ForeignKey(
        "banco_questoes.Questao",
        on_delete=models.CASCADE,
        related_name="perguntas_respostas_estudos",
    )
    contexto_hash = models.CharField(max_length=64, db_index=True)
    contexto_json = models.JSONField(default=dict, blank=True)
    primeiro_estudo_em = models.DateTimeField()
    ultimo_estudo_em = models.DateTimeField()
    vezes_estudada = models.PositiveIntegerField(default=1)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Historico Perguntas e Respostas"
        verbose_name_plural = "Historico Perguntas e Respostas"
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "questao", "contexto_hash"],
                name="uniq_pr_estudo_usuario_questao_contexto",
            ),
        ]
        indexes = [
            models.Index(
                fields=["usuario", "contexto_hash", "ultimo_estudo_em"],
                name="pr_estudo_user_ctx_last_idx",
            ),
            models.Index(
                fields=["usuario", "questao"],
                name="pr_estudo_user_questao_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.usuario} :: {self.questao_id} :: {self.contexto_hash}"
