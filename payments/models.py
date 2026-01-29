from django.conf import settings
from django.db import models

from banco_questoes.models import Plano


class Billing(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendente"
        PAID = "PAID", "Pago"
        EXPIRED = "EXPIRED", "Expirado"
        FAILED = "FAILED", "Falhou"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="billings",
    )
    plano_destino = models.ForeignKey(
        Plano,
        on_delete=models.PROTECT,
        related_name="billings",
    )
    billing_ref = models.CharField(max_length=64, unique=True, db_index=True)
    valor_centavos = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    pix_id = models.CharField(max_length=80, blank=True, default="", db_index=True)
    pix_qrcode_base64 = models.TextField(blank=True, default="")
    pix_br_code = models.TextField(blank=True, default="")

    payload_criacao = models.JSONField(default=dict, blank=True)
    payload_webhook = models.JSONField(default=dict, blank=True)
    last_check_at = models.DateTimeField(null=True, blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["usuario", "status"]),
            models.Index(fields=["pix_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.usuario} :: {self.plano_destino} :: {self.status}"


class WebhookEvent(models.Model):
    event_id = models.CharField(max_length=120, blank=True, default="", db_index=True)
    tipo = models.CharField(max_length=80)
    payload = models.JSONField(default=dict, blank=True)
    recebido_em = models.DateTimeField(auto_now_add=True)
    processado_em = models.DateTimeField(null=True, blank=True)
    status_processamento = models.CharField(max_length=40, default="PENDING")

    class Meta:
        indexes = [
            models.Index(fields=["tipo"]),
            models.Index(fields=["event_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.tipo} @ {self.recebido_em.isoformat()}"
