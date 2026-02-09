# -*- coding: utf-8 -*-
from __future__ import annotations

import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q


class Curso(models.Model):
    """Ex.: 'Primeira Habilitação', 'Cargas Indivisíveis', etc."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)

    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome


class CursoModulo(models.Model):
    """
    Módulos são cadastráveis por curso.
    Ex.: 'Placas, Cores e Caminhos', 'Na Direção da Segurança', etc.
    """
    class Categoria(models.TextChoices):
        CONTEUDO = "CONTEUDO", "Conteúdo"
        SIMULADO = "SIMULADO", "Simulado / Teste"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    curso = models.ForeignKey(
        Curso,
        on_delete=models.CASCADE,
        related_name="modulos",
    )

    ordem = models.PositiveSmallIntegerField(help_text="Ordem de exibição no curso (1..N).")
    nome = models.CharField(max_length=160)
    categoria = models.CharField(
        max_length=20,
        choices=Categoria.choices,
        default=Categoria.CONTEUDO,
        db_index=True,
    )

    # Opcional: mapeamento de páginas para import (ajuda MUITO)
    pagina_inicio = models.PositiveSmallIntegerField(null=True, blank=True)
    pagina_fim = models.PositiveSmallIntegerField(null=True, blank=True)

    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["curso__nome", "ordem"]
        constraints = [
            models.UniqueConstraint(
                fields=["curso", "ordem"],
                name="uniq_modulo_ordem_por_curso",
            ),
            models.UniqueConstraint(
                fields=["curso", "nome"],
                name="uniq_modulo_nome_por_curso",
            ),
        ]
        indexes = [
            models.Index(fields=["curso", "categoria", "ordem"]),
        ]

    def __str__(self) -> str:
        return f"{self.curso.nome} :: M{self.ordem} - {self.nome}"


class Documento(models.Model):
    """Ex.: 'Banco Nacional de Questões - SENATRAN 2025'."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    titulo = models.CharField(max_length=200)
    ano = models.PositiveSmallIntegerField(null=True, blank=True)

    arquivo_nome = models.CharField(max_length=255, blank=True, default="")
    arquivo_hash = models.CharField(max_length=64, blank=True, default="", db_index=True)

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-ano", "titulo"]
        constraints = [
            models.UniqueConstraint(
                fields=["arquivo_hash"],
                condition=~Q(arquivo_hash=""),
                name="uniq_documento_por_hash_quando_preenchido",
            )
        ]

    def __str__(self) -> str:
        return f"{self.titulo} ({self.ano})" if self.ano else self.titulo


class Questao(models.Model):
    class Dificuldade(models.TextChoices):
        FACIL = "FACIL", "Fácil"
        INTERMEDIARIO = "INTERMEDIARIO", "Intermediário"
        DIFICIL = "DIFICIL", "Difícil"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    curso = models.ForeignKey(Curso, on_delete=models.PROTECT, related_name="questoes")
    modulo = models.ForeignKey(CursoModulo, on_delete=models.PROTECT, related_name="questoes")

    documento = models.ForeignKey(Documento, on_delete=models.PROTECT, related_name="questoes")

    # numeração reinicia POR MÓDULO
    numero_no_modulo = models.PositiveSmallIntegerField()

    dificuldade = models.CharField(max_length=20, choices=Dificuldade.choices, null=True, blank=True)

    enunciado = models.TextField()
    comentario = models.TextField(blank=True, default="")

    # 1) código_placa: ex. "R-14" (quando existir)
    codigo_placa = models.CharField(max_length=20, blank=True, default="", db_index=True)

    # 2) imagem: nome do arquivo (ex. "R-14.png" ou vazio)
    imagem_arquivo = models.CharField(max_length=255, blank=True, default="")

    # Auditoria/depuração do import
    pagina_inicio = models.PositiveSmallIntegerField(null=True, blank=True)
    pagina_fim = models.PositiveSmallIntegerField(null=True, blank=True)
    raw_block = models.TextField(blank=True, default="")

    import_hash = models.CharField(max_length=64, blank=True, default="", db_index=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["curso__nome", "modulo__ordem", "numero_no_modulo"]
        indexes = [
            models.Index(fields=["curso", "modulo", "numero_no_modulo"]),
            models.Index(fields=["codigo_placa"]),
            models.Index(fields=["dificuldade"]),
        ]
        constraints = [
            # garante que a questão é consistente: módulo pertence ao mesmo curso
            # (Django não faz isso sozinho; você valida no importador/admin)
            models.UniqueConstraint(
                fields=["documento", "modulo", "numero_no_modulo"],
                name="uniq_questao_por_documento_modulo_numero",
            ),
            models.UniqueConstraint(
                fields=["import_hash"],
                condition=~Q(import_hash=""),
                name="uniq_questao_import_hash_quando_preenchido",
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.modulo.nome} #{self.numero_no_modulo}] {self.enunciado[:60]}"

    @property
    def tem_imagem(self) -> bool:
        return bool(self.imagem_arquivo)


class Alternativa(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    questao = models.ForeignKey(Questao, on_delete=models.CASCADE, related_name="alternativas")
    texto = models.TextField()
    is_correta = models.BooleanField(default=False)
    ordem = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["questao", "ordem"]
        constraints = [
            models.UniqueConstraint(fields=["questao", "ordem"], name="uniq_ordem_por_questao"),
            models.UniqueConstraint(
                fields=["questao"],
                condition=Q(is_correta=True),
                name="uniq_uma_correta_por_questao",
            ),
        ]
        indexes = [
            models.Index(fields=["questao", "is_correta"]),
        ]

    def __str__(self) -> str:
        prefixo = "[correta]" if self.is_correta else "[incorreta]"
        return f"{prefixo} {self.texto[:60]}"


class Plano(models.Model):
    class Periodo(models.TextChoices):
        DIARIO = "DIARIO", "Diario"
        SEMANAL = "SEMANAL", "Semanal"
        MENSAL = "MENSAL", "Mensal"
        ANUAL = "ANUAL", "Anual"

    class CicloCobranca(models.TextChoices):
        MENSAL = "MENSAL", "Mensal"
        ANUAL = "ANUAL", "Anual"
        NAO_RECORRENTE = "NAO_RECORRENTE", "Nao recorrente"

    nome = models.CharField(max_length=120, unique=True)
    limite_qtd = models.PositiveIntegerField(null=True, blank=True)
    limite_periodo = models.CharField(max_length=20, choices=Periodo.choices, null=True, blank=True)
    validade_dias = models.PositiveIntegerField(null=True, blank=True)
    ciclo_cobranca = models.CharField(
        max_length=20,
        choices=CicloCobranca.choices,
        default=CicloCobranca.NAO_RECORRENTE,
    )
    preco = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome


class AppModulo(models.Model):
    slug = models.SlugField(max_length=120, unique=True)
    nome = models.CharField(max_length=120)
    ativo = models.BooleanField(default=True)
    ordem_menu = models.PositiveSmallIntegerField(default=0)
    icone_path = models.CharField(max_length=255, blank=True, default="")
    rota_nome = models.CharField(max_length=120, blank=True, default="")
    em_construcao = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["ordem_menu", "nome"]
        indexes = [
            models.Index(fields=["ativo", "ordem_menu"], name="bq_appmod_ativo_ordem_idx"),
        ]

    def __str__(self) -> str:
        return self.nome


class PlanoPermissaoApp(models.Model):
    plano = models.ForeignKey(
        Plano,
        on_delete=models.CASCADE,
        related_name="permissoes_apps",
    )
    app_modulo = models.ForeignKey(
        AppModulo,
        on_delete=models.CASCADE,
        related_name="permissoes_planos",
    )
    permitido = models.BooleanField(default=False)
    limite_qtd = models.PositiveIntegerField(null=True, blank=True)
    limite_periodo = models.CharField(
        max_length=20,
        choices=Plano.Periodo.choices,
        null=True,
        blank=True,
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["plano__nome", "app_modulo__ordem_menu", "app_modulo__nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["plano", "app_modulo"],
                name="uniq_plano_permissao_app",
            ),
        ]
        indexes = [
            models.Index(fields=["plano", "permitido"], name="bq_planoapp_plano_perm_idx"),
            models.Index(fields=["app_modulo"], name="bq_planoapp_app_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.plano.nome} :: {self.app_modulo.nome}"


class Assinatura(models.Model):
    class Status(models.TextChoices):
        ATIVO = "ATIVO", "Ativo"
        EXPIRADO = "EXPIRADO", "Expirado"
        PAUSADO = "PAUSADO", "Pausado"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assinaturas",
    )
    plano = models.ForeignKey(
        Plano,
        on_delete=models.SET_NULL,
        related_name="assinaturas",
        null=True,
        blank=True,
    )

    nome_plano_snapshot = models.CharField(max_length=120, default="", blank=True)
    limite_qtd_snapshot = models.PositiveIntegerField(null=True, blank=True)
    limite_periodo_snapshot = models.CharField(
        max_length=20,
        choices=Plano.Periodo.choices,
        null=True,
        blank=True,
    )
    validade_dias_snapshot = models.PositiveIntegerField(null=True, blank=True)
    ciclo_cobranca_snapshot = models.CharField(
        max_length=20,
        choices=Plano.CicloCobranca.choices,
        default=Plano.CicloCobranca.NAO_RECORRENTE,
    )
    preco_snapshot = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ATIVO)
    inicio = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]
        indexes = [
            models.Index(fields=["usuario", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.usuario} :: {self.nome_plano_snapshot or self.plano_id}"


class SimuladoUso(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="simulado_uso",
    )
    janela_inicio = models.DateTimeField()
    janela_fim = models.DateTimeField()
    contador = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "janela_inicio", "janela_fim"],
                name="uniq_uso_por_usuario_janela",
            ),
        ]
        indexes = [
            models.Index(fields=["usuario", "janela_fim"]),
        ]

    def __str__(self) -> str:
        return f"{self.usuario} :: {self.janela_inicio.date()}-{self.janela_fim.date()}"


class UsoAppJanela(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="uso_apps_janela",
    )
    app_modulo = models.ForeignKey(
        AppModulo,
        on_delete=models.CASCADE,
        related_name="usos_janela",
    )
    janela_inicio = models.DateTimeField()
    janela_fim = models.DateTimeField()
    contador = models.PositiveIntegerField(default=0)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "app_modulo", "janela_inicio", "janela_fim"],
                name="uniq_usoapp_usuario_janela",
            ),
        ]
        indexes = [
            models.Index(fields=["usuario", "app_modulo", "janela_fim"], name="bq_usoapp_user_app_fim_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.usuario} :: {self.app_modulo.slug} :: {self.janela_inicio.date()}-{self.janela_fim.date()}"


class EventoAuditoria(models.Model):
    tipo = models.CharField(max_length=60)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_auditoria",
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    device_id = models.CharField(max_length=64, blank=True, default="")
    contexto_json = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["tipo"]),
            models.Index(fields=["timestamp"]),
            models.Index(fields=["ip"]),
        ]

    def __str__(self) -> str:
        return f"{self.tipo} @ {self.timestamp.isoformat()}"
