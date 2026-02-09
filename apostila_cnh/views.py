from django.shortcuts import render

from banco_questoes.access_control import require_app_access

@require_app_access("apostila-cnh")
def index(request):
    return render(
        request,
        "apostila_cnh/index.html",
        {"app_title": "Apostila da CNH do Brasil"},
    )
