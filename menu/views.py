from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import reverse

from .catalog import get_menu_catalog


@login_required
def home(request):
    cards = []
    for index, card in enumerate(get_menu_catalog()):
        route_name = card.get("rota_nome", "")
        clicavel = bool(route_name)
        ativo = str(card.get("status", "")).strip().lower() == "ativo"
        href = reverse(route_name) if clicavel else "#"
        cards.append(
            {
                **card,
                "href": href,
                "ativo": ativo,
                "clicavel": clicavel,
                "ordem_base": index,
            }
        )
    cards.sort(key=lambda item: (not item["ativo"], item["ordem_base"]))
    return render(request, "menu/home.html", {"cards": cards})
