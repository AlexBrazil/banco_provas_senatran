from django.contrib import admin

from .models import Alternativa, Curso, CursoModulo, Documento, Questao


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
