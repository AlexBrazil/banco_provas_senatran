from __future__ import annotations


MENU_CATALOG = [
    {
        "slug": "simulado-digital",
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
        "rota_nome": "perguntas_respostas:index",
    },
    {
        "slug": "apostila-cnh",
        "titulo": "Apostila da CNH do Brasil",
        "descricao": "Modulo em construcao.",
        "icone": "menu_app/icons/icon_app_3.png",
        "status": "Em construcao",
        "rota_nome": "apostila_cnh:index",
    },
    {
        "slug": "simulacao-prova-detran",
        "titulo": "Simulacao do Ambiente de Provas do DETRAN",
        "descricao": "Modulo em construcao.",
        "icone": "menu_app/icons/icon_app_4.png",
        "status": "Em construcao",
        "rota_nome": "simulacao_prova:index",
    },
    {
        "slug": "manual-aulas-praticas",
        "titulo": "Manual de Aulas Praticas",
        "descricao": "Modulo em construcao.",
        "icone": "menu_app/icons/icon_app_5.png",
        "status": "Em construcao",
        "rota_nome": "manual_pratico:index",
    },
    {
        "slug": "aprenda-jogando",
        "titulo": "Aprenda Jogando",
        "descricao": "Modulo em construcao.",
        "icone": "menu_app/icons/icon_app_6.png",
        "status": "Em construcao",
        "rota_nome": "aprenda_jogando:index",
    },
    {
        "slug": "oraculo",
        "titulo": "Oraculo",
        "descricao": "Modulo em construcao.",
        "icone": "menu_app/icons/icon_app_7.png",
        "status": "Em construcao",
        "rota_nome": "oraculo:index",
    },
    {
        "slug": "aprova-plus",
        "titulo": "Aprova+",
        "descricao": "Modulo em construcao.",
        "icone": "menu_app/icons/icon_app_8.png",
        "status": "Em construcao",
        "rota_nome": "aprova_plus:index",
    },
]


def get_menu_catalog() -> list[dict]:
    return [dict(item) for item in MENU_CATALOG]
