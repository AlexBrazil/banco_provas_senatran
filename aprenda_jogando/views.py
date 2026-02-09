from django.shortcuts import render

from banco_questoes.access_control import require_app_access

@require_app_access("aprenda-jogando")
def index(request):
    return render(
        request,
        "aprenda_jogando/index.html",
        {"app_title": "Aprenda Jogando"},
    )
