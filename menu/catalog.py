from __future__ import annotations


MENU_CATALOG = [
    {
        "slug": "simulado-digital",
        "titulo": "Simulado de Provas",
        "descricao": "Prepara-se para a prova teórica no DETRAN com as questões oficiais do banco de provas da SENATRAN.",
        "icone": "menu_app/icons/icon_app_1.png",
        "status": "Ativo",
        "rota_nome": "simulado:inicio",
    },
    {
        "slug": "perguntas-respostas",
        "titulo": "Perguntas e Respostas para Estudos",
        "descricao": "Estude de forma direta, sem enrolação e conteúdos desnecessários.",
        "icone": "menu_app/icons/icon_app_2.png",
        "status": "Em construcao",
        "rota_nome": "perguntas_respostas:index",
    },
    {
        "slug": "apostila-cnh",
        "titulo": "Apostila da CNH do Brasil",
        "descricao": "Apostila oficial da SENATRAN em PDF disponível sem ter que entrar com gov.br.",
        "icone": "menu_app/icons/icon_app_3.png",
        "status": "Em construcao",
        "rota_nome": "apostila_cnh:index",
    },
    {
        "slug": "simulacao-prova-detran",
        "titulo": "Simulacao do Ambiente de Provas do DETRAN",
        "descricao": "A prova é realizada no computador e possui uma sequencia de execução. Conheça essa sequencia de forma antecipada.",
        "icone": "menu_app/icons/icon_app_4.png",
        "status": "Em construcao",
        "rota_nome": "simulacao_prova:index",
    },
    {
        "slug": "manual-aulas-praticas",
        "titulo": "Manual de Aulas Praticas",
        "descricao": "Dicas úteis para o momento de suas aulas e prova prática de direção.",
        "icone": "menu_app/icons/icon_app_5.png",
        "status": "Em construcao",
        "rota_nome": "manual_pratico:index",
    },
    {
        "slug": "aprenda-jogando",
        "titulo": "Aprenda Jogando",
        "descricao": "Jogos educacionais para aprender as placas e regras de circulação.",
        "icone": "menu_app/icons/icon_app_6.png",
        "status": "Em construcao",
        "rota_nome": "aprenda_jogando:index",
    },
    {
        "slug": "oraculo",
        "titulo": "Oraculo",
        "descricao": "Agente de IA (Inteligência Artificial) que responde perguintas sobre a legislação de trânsito.",
        "icone": "menu_app/icons/icon_app_7.png",
        "status": "Em construcao",
        "rota_nome": "oraculo:index",
    },
    {
        "slug": "aprova-plus",
        "titulo": "Aprova+",
        "descricao": "Seu maior vilão na hora da prova é seu estado emocional e nervosismo. Te damos dicas úteis que te ajudarão a superar tais barreiras.",
        "icone": "menu_app/icons/icon_app_8.png",
        "status": "Em construcao",
        "rota_nome": "aprova_plus:index",
    },
]


def get_menu_catalog() -> list[dict]:
    return [dict(item) for item in MENU_CATALOG]
