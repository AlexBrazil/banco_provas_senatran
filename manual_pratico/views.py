from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def index(request):
    return render(
        request,
        "manual_pratico/index.html",
        {"app_title": "Manual de Aulas Praticas"},
    )

