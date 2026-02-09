from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def index(request):
    return render(
        request,
        "simulacao_prova/index.html",
        {"app_title": "Simulacao do Ambiente de Provas do DETRAN"},
    )

