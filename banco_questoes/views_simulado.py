from __future__ import annotations

import random
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from banco_questoes.models import Curso, CursoModulo, Questao, Alternativa


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

    curso_id = request.GET.get("curso")
    modulos = []
    if curso_id:
        modulos = CursoModulo.objects.filter(curso_id=curso_id, ativo=True).order_by("ordem")

    return render(
        request,
        "simulado/config.html",
        {
            "cursos": cursos,
            "curso_id": curso_id,
            "modulos": modulos,
        },
    )


@require_http_methods(["POST"])
def simulado_iniciar(request: HttpRequest) -> HttpResponse:
    # Inputs
    curso_id = request.POST.get("curso_id")
    modulo_id = request.POST.get("modulo_id") or ""
    qtd = int(request.POST.get("qtd") or 10)

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

    total = qs.count()
    if total == 0:
        # nada para simular
        return render(
            request,
            "simulado/erro.html",
            {"msg": "Não existem questões para esse filtro (curso/módulo)."},
            status=400,
        )

    if qtd > total:
        qtd = total

    # Seleção aleatória (para 1500 questões funciona bem)
    # Pegamos IDs e fazemos sample no Python (evita ORDER BY ? pesado)
    ids = list(qs.values_list("id", flat=True))
    chosen = random.sample(ids, k=qtd)

    state = {
        "curso_id": str(curso_id),
        "modulo_id": str(modulo_id) if modulo_id else "",
        "qtd": qtd,
        "index": 0,
        "question_ids": [str(x) for x in chosen],
        "answers": {},  # {question_id: {"alt_id": "...", "is_correct": True/False}}
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
