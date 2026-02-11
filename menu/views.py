from __future__ import annotations

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import NoReverseMatch, reverse

from banco_questoes.access_control import build_app_access_status, build_plan_modal_status
from .catalog import get_menu_catalog


def _build_cards_from_catalog() -> list[dict]:
    cards = []
    for index, card in enumerate(get_menu_catalog()):
        route_name = card.get("rota_nome", "")
        clicavel = bool(route_name)
        ativo = str(card.get("status", "")).strip().lower() == "ativo"
        try:
            href = reverse(route_name) if clicavel else "#"
        except NoReverseMatch:
            href = "#"
            clicavel = False
        cards.append(
            {
                **card,
                "href": href,
                "ativo": ativo,
                "liberado": ativo,
                "clicavel": clicavel,
                "em_construcao": not ativo,
                "ordem_base": index,
                "badge_class": "menu-badge--active" if ativo else "",
            }
        )
    cards.sort(key=lambda item: (not item["ativo"], item["ordem_base"]))
    return cards


def _build_cards_from_access(user) -> list[dict]:
    access_status = build_app_access_status(user)
    if not access_status.get("apps"):
        return _build_cards_from_catalog()

    catalog_by_slug = {item["slug"]: item for item in get_menu_catalog()}
    cards = []
    for index, app in enumerate(access_status["apps"]):
        route_name = app.get("rota_nome", "")
        bloqueado = not app.get("liberado")
        clicavel = bool(route_name) and not bloqueado
        try:
            href = reverse(route_name) if clicavel else "#"
        except NoReverseMatch:
            href = "#"
            clicavel = False

        if app.get("liberado") and app.get("em_construcao"):
            status_label = "Em construcao"
            badge_class = ""
        elif app.get("liberado"):
            status_label = "Liberado"
            badge_class = "menu-badge--active"
        else:
            status_label = "Bloqueado pelo plano"
            badge_class = "menu-badge--blocked"

        catalog_item = catalog_by_slug.get(app["slug"], {})
        cards.append(
            {
                "slug": app["slug"],
                "titulo": app["nome"],
                "descricao": catalog_item.get("descricao", ""),
                "icone": app.get("icone_path") or catalog_item.get("icone", ""),
                "status": status_label,
                "href": href,
                "ativo": bool(app.get("liberado") and not app.get("em_construcao")),
                "liberado": bool(app.get("liberado")),
                "clicavel": clicavel,
                "em_construcao": bool(app.get("em_construcao")),
                "ordem_base": int(app.get("ordem_menu", index + 1)),
                "badge_class": badge_class,
            }
        )

    cards.sort(key=lambda item: (not item["liberado"], item["em_construcao"], item["ordem_base"]))
    return cards


@login_required
def home(request):
    if settings.APP_ACCESS_V2_ENABLED:
        cards = _build_cards_from_access(request.user)
    else:
        cards = _build_cards_from_catalog()
    plano_modal_status = build_plan_modal_status(request.user)
    return render(request, "menu/home.html", {"cards": cards, "plano_modal_status": plano_modal_status})
