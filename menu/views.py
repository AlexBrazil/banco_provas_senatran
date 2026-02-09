from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import reverse


MENU_CARDS = [
    {
        "slug": "simulado-provas",
        "titulo": "Simulado de Provas",
        "descricao": "App atual em operacao.",
        "icone": "menu_app/icons/icon_app_1.png",
        "status": "Ativo",
        "rota_nome": "simulado:inicio",
    },
    {
        "slug": "perguntas-respostas",
        "titulo": "Perguntas e Respostas para Estudos",
        "descricao": "Modulo em construcao.",
        "icone": "menu_app/icons/icon_app_2.png",
        "status": "Em construcao",
        "rota_nome": "",
    },
    {
        "slug": "apostila-cnh",
        "titulo": "Apostila da CNH do Brasil",
        "descricao": "Modulo em construcao.",
        "icone": "menu_app/icons/icon_app_3.png",
        "status": "Em construcao",
        "rota_nome": "",
    },
    {
        "slug": "simulacao-prova-detran",
        "titulo": "Simulacao do Ambiente de Provas do DETRAN",
        "descricao": "Modulo em construcao.",
        "icone": "menu_app/icons/icon_app_4.png",
        "status": "Em construcao",
        "rota_nome": "",
    },
    {
        "slug": "manual-aulas-praticas",
        "titulo": "Manual de Aulas Praticas",
        "descricao": "Modulo em construcao.",
        "icone": "menu_app/icons/icon_app_5.png",
        "status": "Em construcao",
        "rota_nome": "",
    },
    {
        "slug": "aprenda-jogando",
        "titulo": "Aprenda Jogando",
        "descricao": "Modulo em construcao.",
        "icone": "menu_app/icons/icon_app_6.png",
        "status": "Em construcao",
        "rota_nome": "",
    },
    {
        "slug": "oraculo",
        "titulo": "Oraculo",
        "descricao": "Modulo em construcao.",
        "icone": "menu_app/icons/icon_app_7.png",
        "status": "Em construcao",
        "rota_nome": "",
    },
    {
        "slug": "aprova-plus",
        "titulo": "Aprova+",
        "descricao": "Modulo em construcao.",
        "icone": "menu_app/icons/icon_app_8.png",
        "status": "Em construcao",
        "rota_nome": "",
    },
]


@login_required
def home(request):
    cards = []
    for index, card in enumerate(MENU_CARDS):
        route_name = card.get("rota_nome", "")
        href = reverse(route_name) if route_name else "#"
        cards.append(
            {
                **card,
                "href": href,
                "ativo": bool(route_name),
                "ordem_base": index,
            }
        )
    cards.sort(key=lambda item: (not item["ativo"], item["ordem_base"]))
    return render(request, "menu/home.html", {"cards": cards})
