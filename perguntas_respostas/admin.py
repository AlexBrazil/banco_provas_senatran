from django.contrib import admin

from .models import PerguntaRespostaEstudo, PerguntaRespostaPreferenciaUsuario


@admin.register(PerguntaRespostaPreferenciaUsuario)
class PerguntaRespostaPreferenciaUsuarioAdmin(admin.ModelAdmin):
    list_display = ("usuario", "tempo_entre_questoes_segundos", "modo_automatico_ativo", "atualizado_em")
    search_fields = ("usuario__username", "usuario__email")
    list_filter = ("modo_automatico_ativo",)


@admin.register(PerguntaRespostaEstudo)
class PerguntaRespostaEstudoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "questao", "contexto_hash", "vezes_estudada", "ultimo_estudo_em")
    search_fields = ("usuario__username", "usuario__email", "contexto_hash")
    list_filter = ("contexto_hash",)
