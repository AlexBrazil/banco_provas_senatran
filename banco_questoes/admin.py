from django.contrib import admin
from django.utils.translation import gettext_lazy as _

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


@admin.register(Assinatura)
class AssinaturaAdmin(admin.ModelAdmin):
    list_display = ("usuario", "plano", "status", "valid_until", "preco_snapshot", "limite_qtd_snapshot")
    list_filter = ("status", "plano")
    search_fields = ("usuario__email", "usuario__username", "nome_plano_snapshot")
    list_select_related = ("usuario", "plano")


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
