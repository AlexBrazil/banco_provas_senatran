from django.shortcuts import render

from banco_questoes.access_control import require_app_access

@require_app_access("perguntas-respostas")
def index(request):
    return render(
        request,
        "perguntas_respostas/index.html",
        {"app_title": "Perguntas e Respostas para Estudos"},
    )
