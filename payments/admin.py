from django.contrib import admin

from .models import Billing, WebhookEvent


@admin.register(Billing)
class BillingAdmin(admin.ModelAdmin):
    list_display = ("usuario", "plano_destino", "status", "valor_centavos", "criado_em")
    list_filter = ("status", "plano_destino")
    search_fields = ("usuario__email", "usuario__username", "billing_ref", "pix_id")
    readonly_fields = ("criado_em", "atualizado_em")


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ("tipo", "event_id", "status_processamento", "recebido_em")
    list_filter = ("tipo", "status_processamento")
    search_fields = ("event_id", "tipo")
    readonly_fields = ("recebido_em", "processado_em")
