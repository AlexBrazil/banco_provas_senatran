from __future__ import annotations

import random
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_GET
from banco_questoes.models import Curso, CursoModulo, Questao, Alternativa
from django.db.models import Count, Q


SESSION_KEY = "simulado_state_v1"


def _get_state(request: HttpRequest) -> dict:
    return request.session.get(SESSION_KEY, {})


def _set_state(request: HttpRequest, state: dict) -> None:
    request.session[SESSION_KEY] = state
    request.session.modified = True


def _clear_state(request: HttpRequest) -> None:
    request.session.pop(SESSION_KEY, None)
    request.session.modified = True


@require_http_methods(["GET"])
def simulado_config(request: HttpRequest) -> HttpResponse:
    cursos = Curso.objects.filter(ativo=True).order_by("nome")
    quick_curso_id = (
        Curso.objects.filter(ativo=True, nome__iexact="Primeira Habilitação")
        .values_list("id", flat=True)
        .first()
    )
    return render(
        request,
        "simulado/config.html",
        {"cursos": cursos, "quick_curso_id": quick_curso_id},
    )

@require_http_methods(["POST"])
def simulado_iniciar(request: HttpRequest) -> HttpResponse:
    # Inputs obrigatórios e básicos
    curso_id = (request.POST.get("curso_id") or "").strip()
    modulo_id = (request.POST.get("modulo_id") or "").strip()

    # Quantidade
    try:
        qtd = int(request.POST.get("qtd") or 10)
    except (TypeError, ValueError):
        qtd = 10

    # Modo (NOVO): PROVA | ESTUDO
    modo = (request.POST.get("modo") or "PROVA").strip().upper()
    if modo not in {"PROVA", "ESTUDO"}:
        modo = "PROVA"

    # Filtros (opcionais)
    dificuldade = (request.POST.get("dificuldade") or "").strip().upper()  # "" = misturado
    com_imagem = (request.POST.get("com_imagem") == "1")
    so_placas = (request.POST.get("so_placas") == "1")

    if not curso_id:
        return redirect(reverse("simulado:config"))

    # Limites simples
    if qtd < 1:
        qtd = 1
    if qtd > 50:
        qtd = 50

    # Base queryset
    qs = Questao.objects.filter(curso_id=curso_id)

    if modulo_id:
        qs = qs.filter(modulo_id=modulo_id)

    if dificuldade in {"FACIL", "INTERMEDIARIO", "DIFICIL"}:
        qs = qs.filter(dificuldade=dificuldade)

    if com_imagem:
        qs = qs.exclude(imagem_arquivo="")

    if so_placas:
        qs = qs.exclude(codigo_placa="")

    total = qs.count()
    if total == 0:
        return render(
            request,
            "simulado/erro.html",
            {"msg": "Não existem questões para esse filtro (curso/módulo/filtros)."},
            status=400,
        )

    if qtd > total:
        qtd = total

    # Seleção aleatória eficiente
    ids = list(qs.values_list("id", flat=True))
    chosen = random.sample(ids, k=qtd)

    state = {
        "curso_id": str(curso_id),
        "modulo_id": str(modulo_id) if modulo_id else "",
        "qtd": qtd,
        "index": 0,
        "question_ids": [str(x) for x in chosen],
        "answers": {},  # {question_id: {"alt_id": "...", "is_correct": True/False}}

        # NOVO: modo do simulado
        "mode": modo,  # "PROVA" | "ESTUDO"

        # guarda filtros usados (bom para exibir no resultado e depurar)
        "filters": {
            "dificuldade": dificuldade,   # "", FACIL, INTERMEDIARIO, DIFICIL
            "com_imagem": com_imagem,     # bool
            "so_placas": so_placas,       # bool
        },
    }

    _set_state(request, state)
    return redirect(reverse("simulado:questao"))


@require_http_methods(["GET"])
def simulado_questao(request: HttpRequest) -> HttpResponse:
    state = _get_state(request)
    if not state or not state.get("question_ids"):
        return redirect(reverse("simulado:config"))

    idx = int(state.get("index", 0))
    qids = state["question_ids"]

    if idx >= len(qids):
        return redirect(reverse("simulado:resultado"))

    qid = qids[idx]

    questao = (
        Questao.objects
        .select_related("modulo", "curso")
        .get(id=qid)
    )

    alternativas = list(
        Alternativa.objects.filter(questao=questao).order_by("ordem")
    )
    # Embaralha as alternativas na tela (opcional)
    random.shuffle(alternativas)

    answered = state.get("answers", {}).get(qid)

    return render(
        request,
        "simulado/questao.html",
        {
            "idx": idx,
            "total": len(qids),
            "questao": questao,
            "alternativas": alternativas,
            "answered": answered,
        },
    )


@require_http_methods(["POST"])
def simulado_responder(request: HttpRequest) -> HttpResponse:
    state = _get_state(request)
    if not state or not state.get("question_ids"):
        return redirect(reverse("simulado:config"))

    idx = int(state.get("index", 0))
    qids = state["question_ids"]
    if idx >= len(qids):
        return redirect(reverse("simulado:resultado"))

    qid = qids[idx]
    alt_id = request.POST.get("alternativa_id")
    if not alt_id:
        return redirect(reverse("simulado:questao"))

    # Valida alternativa e calcula correto
    alt = Alternativa.objects.select_related("questao").get(id=alt_id)
    if str(alt.questao_id) != str(qid):
        return render(request, "simulado/erro.html", {"msg": "Alternativa inválida."}, status=400)

    is_correct = bool(alt.is_correta)

    answers = state.get("answers", {})
    answers[qid] = {"alt_id": str(alt_id), "is_correct": is_correct}
    state["answers"] = answers

    # Próxima questão
    state["index"] = idx + 1
    _set_state(request, state)

    if state["index"] >= len(qids):
        return redirect(reverse("simulado:resultado"))

    return redirect(reverse("simulado:questao"))


@require_http_methods(["GET", "POST"])
def simulado_resultado(request: HttpRequest) -> HttpResponse:
    state = _get_state(request)
    if not state or not state.get("question_ids"):
        return redirect(reverse("simulado:config"))

    qids = state["question_ids"]
    answers = state.get("answers", {})

    acertos = sum(1 for qid in qids if answers.get(qid, {}).get("is_correct") is True)
    total = len(qids)

    # Se quiser listar revisões, buscamos as questões respondidas
    questoes = list(
        Questao.objects.filter(id__in=qids).select_related("modulo").order_by("numero_no_modulo")
    )
    questoes_map = {str(q.id): q for q in questoes}

    revisao = []
    for qid in qids:
        q = questoes_map.get(str(qid))
        if not q:
            continue
        info = answers.get(str(qid), {})
        revisao.append(
            {
                "questao": q,
                "respondida": bool(info),
                "acertou": info.get("is_correct"),
            }
        )

    if request.method == "POST":
        # botão "Novo simulado"
        _clear_state(request)
        return redirect(reverse("simulado:config"))

    return render(
        request,
        "simulado/resultado.html",
        {
            "acertos": acertos,
            "total": total,
            "percent": round((acertos / total) * 100, 2) if total else 0,
            "revisao": revisao,
        },
    )

# O que isso faz:
# recebe curso_id
# busca módulos ativos
# retorna JSON limpo e fácil pro front usar.
@require_GET
def api_modulos_por_curso(request: HttpRequest) -> JsonResponse:
    curso_id = (request.GET.get("curso_id") or "").strip()

    if not curso_id:
        return JsonResponse({"ok": False, "error": "curso_id ausente."}, status=400)

    qs = (
        CursoModulo.objects
        .filter(curso_id=curso_id, ativo=True)
        .order_by("ordem")
        .values("id", "ordem", "nome")
    )

    modulos = [
        {"id": str(m["id"]), "ordem": m["ordem"], "nome": m["nome"]}
        for m in qs
    ]

    return JsonResponse({"ok": True, "modulos": modulos})

@require_GET
def api_stats(request: HttpRequest) -> JsonResponse:
    """
    Retorna contagens para o config do simulado.
    Parâmetros (GET):
      - curso_id (obrigatório)
      - modulo_id (opcional)
      - dificuldade (opcional): FACIL | INTERMEDIARIO | DIFICIL | "" (misturado)
      - com_imagem (opcional): 1/0
      - so_placas (opcional): 1/0
    """
    curso_id = (request.GET.get("curso_id") or "").strip()
    if not curso_id:
        return JsonResponse({"ok": False, "error": "curso_id ausente."}, status=400)

    modulo_id = (request.GET.get("modulo_id") or "").strip()
    dificuldade = (request.GET.get("dificuldade") or "").strip().upper()
    com_imagem = (request.GET.get("com_imagem") or "0").strip() == "1"
    so_placas = (request.GET.get("so_placas") or "0").strip() == "1"

    qs = Questao.objects.filter(curso_id=curso_id)

    if modulo_id:
        qs = qs.filter(modulo_id=modulo_id)

    if dificuldade in {"FACIL", "INTERMEDIARIO", "DIFICIL"}:
        qs = qs.filter(dificuldade=dificuldade)

    if com_imagem:
        qs = qs.exclude(imagem_arquivo="")

    if so_placas:
        qs = qs.exclude(codigo_placa="")

    # Total do filtro atual
    total = qs.count()

    # Contagens “de painel” (do mesmo recorte curso/modulo, mas separadas por critério)
    base = Questao.objects.filter(curso_id=curso_id)
    if modulo_id:
        base = base.filter(modulo_id=modulo_id)

    # Com imagem e placas (para o painel)
    with_image = base.exclude(imagem_arquivo="").count()
    only_placas = base.exclude(codigo_placa="").count()

    # Por dificuldade (no recorte base)
    diffs = (
        base.values("dificuldade")
        .annotate(n=Count("id"))
    )
    diff_map = {"FACIL": 0, "INTERMEDIARIO": 0, "DIFICIL": 0, "": 0, None: 0}
    for row in diffs:
        diff_map[row["dificuldade"]] = row["n"]

    return JsonResponse(
        {
            "ok": True,
            "filters": {
                "curso_id": curso_id,
                "modulo_id": modulo_id,
                "dificuldade": dificuldade,
                "com_imagem": com_imagem,
                "so_placas": so_placas,
            },
            "total_disponivel": total,
            "painel": {
                "com_imagem": with_image,
                "placas": only_placas,
                "por_dificuldade": {
                    "FACIL": diff_map.get("FACIL", 0),
                    "INTERMEDIARIO": diff_map.get("INTERMEDIARIO", 0),
                    "DIFICIL": diff_map.get("DIFICIL", 0),
                },
            },
        }
    )
