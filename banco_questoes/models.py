# -*- coding: utf-8 -*-
from __future__ import annotations

import uuid
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
