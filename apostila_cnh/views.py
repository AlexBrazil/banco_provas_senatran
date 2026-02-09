from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def index(request):
    return render(
        request,
        "apostila_cnh/index.html",
        {"app_title": "Apostila da CNH do Brasil"},
    )

