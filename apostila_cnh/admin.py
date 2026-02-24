from django.contrib import admin

from .models import ApostilaDocumento, ApostilaPagina, ApostilaProgressoLeitura


@admin.register(ApostilaDocumento)
class ApostilaDocumentoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "slug", "ativo", "total_paginas", "idioma", "atualizado_em")
    list_filter = ("ativo", "idioma")
    search_fields = ("titulo", "slug")
    ordering = ("-ativo", "titulo")


@admin.register(ApostilaPagina)
class ApostilaPaginaAdmin(admin.ModelAdmin):
    list_display = ("documento", "numero_pagina", "atualizado_em")
    list_filter = ("documento",)
    search_fields = ("documento__titulo", "documento__slug", "texto")
    list_select_related = ("documento",)
    ordering = ("documento", "numero_pagina")


@admin.register(ApostilaProgressoLeitura)
class ApostilaProgressoLeituraAdmin(admin.ModelAdmin):
    list_display = ("usuario", "documento", "ultima_pagina_lida", "atualizado_em")
    list_filter = ("documento",)
    search_fields = ("usuario__username", "usuario__email", "documento__titulo", "documento__slug")
    list_select_related = ("usuario", "documento")
    ordering = ("-atualizado_em",)
