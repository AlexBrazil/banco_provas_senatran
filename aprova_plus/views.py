from django.shortcuts import render

from banco_questoes.access_control import require_app_access

@require_app_access("aprova-plus")
def index(request):
    return render(
        request,
        "aprova_plus/index.html",
        {"app_title": "Aprova+"},
    )
