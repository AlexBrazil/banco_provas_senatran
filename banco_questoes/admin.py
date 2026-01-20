from datetime import timedelta

from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .auditoria import log_event

from .models import (
    Alternativa,
    Assinatura,
    Curso,
    CursoModulo,
    Documento,
    EventoAuditoria,
    Plano,
    Questao,
    SimuladoUso,
)


class PlanoFilter(admin.SimpleListFilter):
    title = _("plano")
    parameter_name = "plano"

    def lookups(self, request, model_admin):
        return [(str(p.id), p.nome) for p in Plano.objects.order_by("nome")]

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset
        return queryset.filter(usuario__assinaturas__plano_id=value).distinct()


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ("nome", "slug", "ativo", "criado_em")
    search_fields = ("nome", "slug")
    list_filter = ("ativo",)


@admin.register(CursoModulo)
class CursoModuloAdmin(admin.ModelAdmin):
    list_display = ("curso", "ordem", "nome", "categoria", "ativo")
    list_filter = ("categoria", "ativo", "curso")
    search_fields = ("nome", "curso__nome")
    ordering = ("curso__nome", "ordem")


@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "ano", "arquivo_nome", "arquivo_hash", "criado_em")
    search_fields = ("titulo", "arquivo_nome", "arquivo_hash")
    list_filter = ("ano",)


@admin.register(Questao)
class QuestaoAdmin(admin.ModelAdmin):
    list_display = ("modulo", "numero_no_modulo", "dificuldade", "codigo_placa")
    list_filter = ("dificuldade", "modulo", "curso")
    search_fields = ("enunciado", "codigo_placa", "modulo__nome", "curso__nome")


@admin.register(Alternativa)
class AlternativaAdmin(admin.ModelAdmin):
    list_display = ("questao", "ordem", "is_correta")
    list_filter = ("is_correta",)
    search_fields = ("texto", "questao__enunciado")


@admin.register(Plano)
class PlanoAdmin(admin.ModelAdmin):
    list_display = ("nome", "limite_qtd", "limite_periodo", "validade_dias", "ciclo_cobranca", "preco", "ativo")
    list_filter = ("ativo", "limite_periodo", "ciclo_cobranca")
    search_fields = ("nome",)

    def save_model(self, request, obj, form, change):
        old_preco = None
        if change:
            old_preco = Plano.objects.filter(pk=obj.pk).values_list("preco", flat=True).first()
        super().save_model(request, obj, form, change)
        if change and old_preco is not None and old_preco != obj.preco:
            log_event(
                request,
                "plano_preco_atualizado",
                user=request.user,
                contexto={"plano": obj.nome, "preco_anterior": str(old_preco), "preco_novo": str(obj.preco)},
            )


@admin.register(Assinatura)
class AssinaturaAdmin(admin.ModelAdmin):
    list_display = ("usuario", "plano", "status", "valid_until", "preco_snapshot", "limite_qtd_snapshot")
    list_filter = ("status", "plano")
    search_fields = ("usuario__email", "usuario__username", "nome_plano_snapshot")
    list_select_related = ("usuario", "plano")

    def save_model(self, request, obj, form, change):
        old_preco = old_valid = None
        if change:
            old = Assinatura.objects.filter(pk=obj.pk).first()
            if old:
                old_preco = old.preco_snapshot
                old_valid = old.valid_until
        else:
            if obj.plano:
                obj.nome_plano_snapshot = obj.plano.nome
                obj.limite_qtd_snapshot = obj.plano.limite_qtd
                obj.limite_periodo_snapshot = obj.plano.limite_periodo
                obj.validade_dias_snapshot = obj.plano.validade_dias
                obj.ciclo_cobranca_snapshot = obj.plano.ciclo_cobranca
                obj.preco_snapshot = obj.plano.preco
        if obj.plano:
            inicio = timezone.now()
            obj.inicio = inicio
            if obj.plano.validade_dias:
                obj.valid_until = inicio + timedelta(days=obj.plano.validade_dias)
            else:
                obj.valid_until = None
        super().save_model(request, obj, form, change)
        if change and (old_preco != obj.preco_snapshot or old_valid != obj.valid_until):
            log_event(
                request,
                "assinatura_renovada",
                user=request.user,
                contexto={
                    "usuario_id": obj.usuario_id,
                    "plano": obj.nome_plano_snapshot,
                    "preco_anterior": str(old_preco),
                    "preco_novo": str(obj.preco_snapshot),
                    "valid_until_anterior": old_valid.isoformat() if old_valid else "",
                    "valid_until_novo": obj.valid_until.isoformat() if obj.valid_until else "",
                },
            )


@admin.register(SimuladoUso)
class SimuladoUsoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "janela_inicio", "janela_fim", "contador")
    list_filter = ("janela_fim",)
    search_fields = ("usuario__email", "usuario__username")
    list_select_related = ("usuario",)


@admin.register(EventoAuditoria)
class EventoAuditoriaAdmin(admin.ModelAdmin):
    list_display = ("tipo", "usuario", "timestamp", "ip", "device_id")
    list_filter = ("tipo", "timestamp", "ip", PlanoFilter)
    search_fields = ("usuario__email", "usuario__username", "tipo", "device_id")
    list_select_related = ("usuario",)
    date_hierarchy = "timestamp"
