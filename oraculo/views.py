from django.shortcuts import render

from banco_questoes.access_control import require_app_access


@require_app_access("oraculo")
def index(request):
    return render(
        request,
        "oraculo/index.html",
        {"app_title": "Oraculo"},
    )
