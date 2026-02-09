from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def index(request):
    return render(
        request,
        "aprenda_jogando/index.html",
        {"app_title": "Aprenda Jogando"},
    )

