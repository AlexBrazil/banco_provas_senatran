from django.shortcuts import render

from banco_questoes.access_control import require_app_access

@require_app_access("simulacao-prova-detran")
def index(request):
    return render(
        request,
        "simulacao_prova/index.html",
        {"app_title": "Simulacao do Ambiente de Provas do DETRAN"},
    )
