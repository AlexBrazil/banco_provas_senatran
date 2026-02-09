from django.shortcuts import render

from banco_questoes.access_control import require_app_access

@require_app_access("manual-aulas-praticas")
def index(request):
    return render(
        request,
        "manual_pratico/index.html",
        {"app_title": "Manual de Aulas Praticas"},
    )
