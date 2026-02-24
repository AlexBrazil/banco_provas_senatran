from __future__ import annotations

from django.conf import settings
from django.db import models

from .storage import private_apostila_storage


class ApostilaDocumento(models.Model):
    slug = models.SlugField(max_length=120, unique=True)
    titulo = models.CharField(max_length=200)
    arquivo_pdf = models.FileField(
        upload_to="",
        storage=private_apostila_storage,
    )
    ativo = models.BooleanField(default=False)
    total_paginas = models.PositiveIntegerField(default=0)
    idioma = models.CharField(max_length=10, default="pt-BR")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-ativo", "titulo"]
        indexes = [
            models.Index(fields=["ativo"], name="apost_doc_ativo_idx"),
            models.Index(fields=["slug"], name="apost_doc_slug_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["ativo"],
                condition=models.Q(ativo=True),
                name="apost_unq_documento_ativo_true",
            ),
        ]

    def __str__(self) -> str:
        return self.titulo


class ApostilaPagina(models.Model):
    documento = models.ForeignKey(
        ApostilaDocumento,
        on_delete=models.CASCADE,
        related_name="paginas",
    )
    numero_pagina = models.PositiveIntegerField()
    texto = models.TextField(blank=True, default="")
    texto_normalizado = models.TextField(blank=True, default="")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["documento", "numero_pagina"]
        constraints = [
            models.UniqueConstraint(
                fields=["documento", "numero_pagina"],
                name="apost_unq_doc_numero_pagina",
            ),
        ]
        indexes = [
            models.Index(fields=["documento", "numero_pagina"], name="apost_pag_doc_num_idx"),
            models.Index(fields=["documento"], name="apost_pag_doc_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.documento.slug} :: Pagina {self.numero_pagina}"


class ApostilaProgressoLeitura(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="apostila_cnh_progressos",
    )
    documento = models.ForeignKey(
        ApostilaDocumento,
        on_delete=models.CASCADE,
        related_name="progressos",
    )
    ultima_pagina_lida = models.PositiveIntegerField(default=1)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-atualizado_em"]
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "documento"],
                name="apost_unq_usuario_documento_progresso",
            ),
        ]
        indexes = [
            models.Index(fields=["usuario", "documento"], name="apost_prog_user_doc_idx"),
            models.Index(fields=["documento"], name="apost_prog_doc_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.usuario} :: {self.documento.slug} :: {self.ultima_pagina_lida}"
