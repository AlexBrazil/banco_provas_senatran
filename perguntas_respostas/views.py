from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def index(request):
    return render(
        request,
        "perguntas_respostas/index.html",
        {"app_title": "Perguntas e Respostas para Estudos"},
    )

