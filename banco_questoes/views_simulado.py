from __future__ import annotations

import json
import random
from datetime import timedelta

from functools import wraps

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_http_methods, require_GET

from banco_questoes.auditoria import log_event
from banco_questoes.models import (
    Alternativa,
    AppModulo,
    Assinatura,
    Curso,
    CursoModulo,
    Questao,
    SimuladoUso,
    UsoAppJanela,
)
from banco_questoes.simulado_config import get_simulado_config


SESSION_KEY = "simulado_state_v1"
SIMULADO_APP_SLUG = "simulado-digital"


def login_required_audit(view_func):
    @wraps(view_func)
    def _wrapped(request: HttpRequest, *args, **kwargs):
        if request.user.is_authenticated:
            return view_func(request, *args, **kwargs)
        log_event(
            request,
            "auth_required",
            contexto={"path": request.path, "next": request.get_full_path()},
        )
        return redirect_to_login(request.get_full_path(), login_url=settings.LOGIN_URL)

    return _wrapped


def _get_state(request: HttpRequest) -> dict:
    return request.session.get(SESSION_KEY, {})


def _set_state(request: HttpRequest, state: dict) -> None:
    request.session[SESSION_KEY] = state
    request.session.modified = True


def _clear_state(request: HttpRequest) -> None:
    request.session.pop(SESSION_KEY, None)
    request.session.modified = True


def _resolve_quick_curso_id(curso_cfg: dict | None) -> str | None:
    if not curso_cfg:
        return None

    base_qs = Curso.objects.filter(ativo=True)

    cid = curso_cfg.get("id")
    if cid:
        found = base_qs.filter(id=cid).values_list("id", flat=True).first()
        if found:
            return found

    slug = curso_cfg.get("slug")
    if slug:
        found = base_qs.filter(slug__iexact=slug).values_list("id", flat=True).first()
        if found:
            return found

    nome = curso_cfg.get("nome")
    if nome:
        found = base_qs.filter(nome__iexact=nome).values_list("id", flat=True).first()
        if found:
            return found

    return None


def _merge_filtros(defaults_cfg: dict, override_cfg: dict | None) -> dict:
    override_cfg = override_cfg or {}
    return {
        "modo": override_cfg.get("modo") or defaults_cfg.get("modo") or "PROVA",
        "dificuldade": override_cfg.get("dificuldade") or defaults_cfg.get("dificuldade") or "",
        "com_imagem": bool(override_cfg.get("com_imagem", defaults_cfg.get("com_imagem", False))),
        "so_placas": bool(override_cfg.get("so_placas", defaults_cfg.get("so_placas", False))),
        "qtd": int(override_cfg.get("qtd", defaults_cfg.get("qtd", 10)) or 10),
    }


def _build_frontend_config(cfg: dict) -> tuple[dict, dict, str | None]:
    cfg = cfg or {}
    defaults_cfg = cfg.get("defaults", {}) or {}
    inicio_cfg = cfg.get("inicio_rapido", {}) or {}
    limits_cfg = cfg.get("limits", {}) or {}

    quick_curso_id = _resolve_quick_curso_id(defaults_cfg.get("curso"))
    quick_filters = _merge_filtros(defaults_cfg, inicio_cfg.get("override_filtros"))

    frontend_config = {
        "defaults": {
            "modo": defaults_cfg.get("modo", "PROVA"),
            "dificuldade": defaults_cfg.get("dificuldade", ""),
            "com_imagem": bool(defaults_cfg.get("com_imagem", False)),
            "so_placas": bool(defaults_cfg.get("so_placas", False)),
            "qtd": defaults_cfg.get("qtd", 10),
        },
        "inicio_rapido": {
            "habilitado": bool(inicio_cfg.get("habilitado", True)),
            "label": inicio_cfg.get("label", "Início rápido"),
            "hint": inicio_cfg.get("hint", ""),
            "tooltip": inicio_cfg.get("tooltip", "Curso padrão não encontrado"),
            "override_filtros": quick_filters,
        },
        "ui": {"messages": (cfg.get("ui", {}) or {}).get("messages", {})},
        "limits": {
            "qtd_min": limits_cfg.get("qtd_min", 1),
            "qtd_max": limits_cfg.get("qtd_max", 50),
            "modes": limits_cfg.get("modes", ["PROVA", "ESTUDO"]),
        },
        "quick_curso_id": str(quick_curso_id or ""),
    }

    return frontend_config, quick_filters, quick_curso_id


def _now_iso() -> str:
    return timezone.now().isoformat()


def _parse_ts(value: str | None):
    if not value:
        return None
    dt = parse_datetime(value)
    if dt and timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _get_active_assinatura(user) -> Assinatura | None:
    now = timezone.now()
    return (
        Assinatura.objects
        .filter(usuario=user, status=Assinatura.Status.ATIVO)
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=now))
        .order_by("-inicio", "-criado_em")
        .first()
    )


def _get_period_seconds(periodo: str | None) -> int | None:
    if not periodo:
        return None
    return {
        "DIARIO": 24 * 60 * 60,
        "SEMANAL": 7 * 24 * 60 * 60,
        "MENSAL": 30 * 24 * 60 * 60,
        "ANUAL": 365 * 24 * 60 * 60,
    }.get(periodo)


def _get_janela_atual(inicio: timezone.datetime, period_seconds: int) -> tuple[timezone.datetime, timezone.datetime]:
    now = timezone.now()
    elapsed = max((now - inicio).total_seconds(), 0)
    index = int(elapsed // period_seconds)
    janela_inicio = inicio + timedelta(seconds=index * period_seconds)
    janela_fim = janela_inicio + timedelta(seconds=period_seconds)
    return janela_inicio, janela_fim


def _dual_write_simulado_uso(
    request: HttpRequest,
    *,
    user,
    janela_inicio: timezone.datetime,
    janela_fim: timezone.datetime,
) -> None:
    if not getattr(settings, "APP_ACCESS_DUAL_WRITE", False):
        return

    app_modulo = AppModulo.objects.filter(slug=SIMULADO_APP_SLUG, ativo=True).first()
    if not app_modulo:
        log_event(
            request,
            "app_rule_missing",
            user=user,
            contexto={"app_slug": SIMULADO_APP_SLUG, "reason": "app_modulo_not_found"},
        )
        return

    try:
        uso_app, _ = (
            UsoAppJanela.objects
            .select_for_update()
            .get_or_create(
                usuario=user,
                app_modulo=app_modulo,
                janela_inicio=janela_inicio,
                janela_fim=janela_fim,
                defaults={"contador": 0},
            )
        )
        uso_app.contador += 1
        uso_app.save(update_fields=["contador", "atualizado_em"])
    except Exception as exc:
        log_event(
            request,
            "app_usage_increment_failed",
            user=user,
            contexto={
                "app_slug": SIMULADO_APP_SLUG,
                "reason": "dual_write_exception",
                "error": str(exc),
            },
        )


def _check_and_increment_uso(request: HttpRequest, user, assinatura: Assinatura) -> tuple[bool, str | None]:
    limite = assinatura.limite_qtd_snapshot
    if limite is None:
        return True, None
    if limite <= 0:
        return False, "Limite de simulados indisponivel para este plano."

    period_seconds = _get_period_seconds(assinatura.limite_periodo_snapshot)
    if not period_seconds:
        return False, "Plano sem periodo de limite configurado."

    inicio = assinatura.inicio or timezone.now()
    if assinatura.inicio is None:
        assinatura.inicio = inicio
        assinatura.save(update_fields=["inicio"])

    janela_inicio, janela_fim = _get_janela_atual(inicio, period_seconds)

    with transaction.atomic():
        uso, _ = (
            SimuladoUso.objects
            .select_for_update()
            .get_or_create(
                usuario=user,
                janela_inicio=janela_inicio,
                janela_fim=janela_fim,
                defaults={"contador": 0},
            )
        )
        if uso.contador >= limite:
            return False, "Limite de simulados atingido para o periodo atual."
        uso.contador += 1
        uso.save(update_fields=["contador"])
        _dual_write_simulado_uso(
            request,
            user=user,
            janela_inicio=janela_inicio,
            janela_fim=janela_fim,
        )

    return True, None


def _build_plano_status(user, assinatura: Assinatura | None = None) -> dict | None:
    if not user.is_authenticated:
        return None

    assinatura = assinatura or _get_active_assinatura(user)
    if not assinatura:
        return {"ativo": False}

    limite = assinatura.limite_qtd_snapshot
    periodo = assinatura.limite_periodo_snapshot
    ilimitado = limite is None
    usos = 0
    restantes = None
    janela_inicio = None
    janela_fim = None
    periodo_label = assinatura.get_limite_periodo_snapshot_display() if periodo else ""

    if not ilimitado and periodo:
        period_seconds = _get_period_seconds(periodo)
        if period_seconds:
            inicio = assinatura.inicio
            if inicio:
                janela_inicio, janela_fim = _get_janela_atual(inicio, period_seconds)
                uso = (
                    SimuladoUso.objects
                    .filter(usuario=user, janela_inicio=janela_inicio, janela_fim=janela_fim)
                    .first()
                )
                usos = uso.contador if uso else 0
                restantes = max(limite - usos, 0)
            else:
                usos = 0
                restantes = limite

    nome_plano = assinatura.nome_plano_snapshot or (assinatura.plano.nome if assinatura.plano else "Plano")
    is_free = nome_plano.strip().lower() == "free"
    return {
        "ativo": True,
        "nome": nome_plano,
        "is_free": is_free,
        "limite_qtd": limite,
        "limite_periodo": periodo,
        "limite_periodo_label": periodo_label,
        "ilimitado": ilimitado,
        "usos": usos,
        "restantes": restantes,
        "janela_inicio": janela_inicio,
        "janela_fim": janela_fim,
        "valid_until": assinatura.valid_until,
    }


def _build_error_context(
    request: HttpRequest,
    *,
    msg: str,
    assinatura: Assinatura | None = None,
    allow_upgrade: bool = False,
) -> dict:
    plano_status = _build_plano_status(request.user, assinatura)
    show_upgrade_cta = bool(
        allow_upgrade and plano_status and plano_status.get("ativo") and plano_status.get("is_free")
    )
    upgrade_url = reverse("payments:upgrade_free") if show_upgrade_cta else ""
    return {
        "msg": msg,
        "plano_status": plano_status,
        "show_upgrade_cta": show_upgrade_cta,
        "upgrade_url": upgrade_url,
    }


@login_required_audit
@require_http_methods(["GET"])
def simulado_inicio(request: HttpRequest) -> HttpResponse:
    cfg = get_simulado_config()
    frontend_config, quick_filters, quick_curso_id = _build_frontend_config(cfg)
    plano_status = _build_plano_status(request.user)

    # limpa sessao anterior para evitar retomar simulados ao entrar na tela inicial
    _clear_state(request)

    return render(
        request,
        "simulado/inicio.html",
        {
            "inicio_rapido": frontend_config["inicio_rapido"],
            "quick_filters": quick_filters,
            "quick_curso_id": quick_curso_id,
            "simulado_limits": frontend_config["limits"],
            "simulado_defaults": frontend_config["defaults"],
            "plano_status": plano_status,
        },
    )


@login_required_audit
@require_http_methods(["GET"])
def simulado_config(request: HttpRequest) -> HttpResponse:
    cfg = get_simulado_config()
    defaults_cfg = cfg.get("defaults", {}) or {}
    inicio_cfg = cfg.get("inicio_rapido", {}) or {}
    limits_cfg = cfg.get("limits", {}) or {}

    cursos = Curso.objects.filter(ativo=True).order_by("nome")
    quick_curso_id = _resolve_quick_curso_id(defaults_cfg.get("curso"))
    quick_filters = _merge_filtros(defaults_cfg, inicio_cfg.get("override_filtros"))

    frontend_config = {
        "defaults": {
            "modo": defaults_cfg.get("modo", "PROVA"),
            "dificuldade": defaults_cfg.get("dificuldade", ""),
            "com_imagem": bool(defaults_cfg.get("com_imagem", False)),
            "so_placas": bool(defaults_cfg.get("so_placas", False)),
            "qtd": defaults_cfg.get("qtd", 10),
        },
        "inicio_rapido": {
            "habilitado": bool(inicio_cfg.get("habilitado", True)),
            "label": inicio_cfg.get("label", "Iní­cio rápido"),
            "hint": inicio_cfg.get("hint", ""),
            "tooltip": inicio_cfg.get("tooltip", "Curso padrão não encontrado"),
            "override_filtros": quick_filters,
        },
        "ui": {"messages": (cfg.get("ui", {}) or {}).get("messages", {})},
        "limits": {
            "qtd_min": limits_cfg.get("qtd_min", 1),
            "qtd_max": limits_cfg.get("qtd_max", 50),
            "modes": limits_cfg.get("modes", ["PROVA", "ESTUDO"]),
        },
        "quick_curso_id": str(quick_curso_id or ""),
    }
    plano_status = _build_plano_status(request.user)
    plano_bloqueado = bool(plano_status and plano_status.get("restantes") == 0)
    return render(
        request,
        "simulado/config.html",
        {
            "cursos": cursos,
            "quick_curso_id": quick_curso_id,
            "simulado_defaults": frontend_config["defaults"],
            "simulado_limits": frontend_config["limits"],
            "inicio_rapido": frontend_config["inicio_rapido"],
            "simulado_config_json": json.dumps(frontend_config, ensure_ascii=False),
            "quick_filters": quick_filters,
            "plano_status": plano_status,
            "plano_bloqueado": plano_bloqueado,
        },
    )

@login_required_audit
@require_http_methods(["POST"])
def simulado_iniciar(request: HttpRequest) -> HttpResponse:
    assinatura = _get_active_assinatura(request.user)
    if not assinatura:
        log_event(
            request,
            "assinatura_inativa",
            user=request.user,
            contexto={"path": request.path},
        )
        return render(
            request,
            "simulado/erro.html",
            _build_error_context(request, msg="Assinatura inativa ou expirada."),
            status=403,
        )

    cfg = get_simulado_config()
    limits_cfg = cfg.get("limits", {}) or {}

    # --------
    # Limites (qtd)
    # --------
    try:
        qtd_min = int(limits_cfg.get("qtd_min", 1) or 1)
    except (TypeError, ValueError):
        qtd_min = 1

    try:
        qtd_max = int(limits_cfg.get("qtd_max", 50) or 50)
    except (TypeError, ValueError):
        qtd_max = 50

    if qtd_min < 1:
        qtd_min = 1
    if qtd_max < qtd_min:
        qtd_max = qtd_min

    # --------
    # Modos permitidos
    # --------
    raw_modes = limits_cfg.get("modes", ["PROVA", "ESTUDO"])
    if not isinstance(raw_modes, (list, tuple, set)):
        raw_modes = [raw_modes]

    allowed_modes = {str(m).upper() for m in raw_modes if m}
    if not allowed_modes:
        allowed_modes = {"PROVA", "ESTUDO"}

    # --------
    # Inputs obrigatÃ³rios e bÃ¡sicos
    # --------
    curso_id = (request.POST.get("curso_id") or "").strip()
    modulo_id = (request.POST.get("modulo_id") or "").strip()

    if not curso_id:
        return redirect(reverse("simulado:inicio"))

    # Quantidade
    try:
        qtd = int(request.POST.get("qtd") or 10)
    except (TypeError, ValueError):
        qtd = 10

    # Modo: PROVA | ESTUDO
    modo = (request.POST.get("modo") or "PROVA").strip().upper()
    if modo not in allowed_modes:
        modo = "PROVA"

    # Filtros (opcionais)
    dificuldade = (request.POST.get("dificuldade") or "").strip().upper()  # "" = misturado
    com_imagem = (request.POST.get("com_imagem") == "1")
    so_placas = (request.POST.get("so_placas") == "1")

    # Aplica limites
    if qtd < qtd_min:
        qtd = qtd_min
    if qtd > qtd_max:
        qtd = qtd_max

    # --------
    # Base queryset
    # --------
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
            _build_error_context(
                request,
                msg="NÃ£o existem questÃµes para esse filtro (curso/módulo/filtros).",
                assinatura=assinatura,
            ),
            status=400,
        )

    if qtd > total:
        qtd = total

    allowed, error_msg = _check_and_increment_uso(request, request.user, assinatura)
    if not allowed:
        log_event(
            request,
            "limite_excedido",
            user=request.user,
            contexto={"plano": assinatura.nome_plano_snapshot, "limite": assinatura.limite_qtd_snapshot},
        )
        return render(
            request,
            "simulado/erro.html",
            _build_error_context(request, msg=error_msg, assinatura=assinatura, allow_upgrade=True),
            status=403,
        )

    # SeleÃ§Ã£o aleatÃ³ria eficiente
    ids = list(qs.values_list("id", flat=True))
    chosen = random.sample(ids, k=qtd)

    state = {
        "curso_id": str(curso_id),
        "modulo_id": str(modulo_id) if modulo_id else "",
        "qtd": qtd,
        "index": 0,
        "question_ids": [str(x) for x in chosen],
        "answers": {},  # {question_id: {"alt_id": "...", "is_correct": True/False}}

        # Modo do simulado
        "mode": modo,  # "PROVA" | "ESTUDO"

        # Guarda filtros usados (bom para exibir no resultado e depurar)
        "filters": {
            "dificuldade": dificuldade,  # "", FACIL, INTERMEDIARIO, DIFICIL
            "com_imagem": com_imagem,    # bool
            "so_placas": so_placas,      # bool
        },

        # Auditoria simples de tempo
        "started_at": _now_iso(),
        "finished_at": "",
    }

    _set_state(request, state)
    log_event(
        request,
        "simulado_iniciado",
        user=request.user,
        contexto={
            "curso_id": str(curso_id),
            "modulo_id": str(modulo_id) if modulo_id else "",
            "qtd": qtd,
            "modo": modo,
        },
    )
    return redirect(reverse("simulado:questao"))


@login_required_audit
@require_http_methods(["GET"])
def simulado_questao(request: HttpRequest) -> HttpResponse:
    assinatura = _get_active_assinatura(request.user)
    if not assinatura:
        log_event(
            request,
            "assinatura_inativa",
            user=request.user,
            contexto={"path": request.path},
        )
        return render(
            request,
            "simulado/erro.html",
            _build_error_context(request, msg="Assinatura inativa ou expirada."),
            status=403,
        )

    cfg = get_simulado_config()
    imagens_cfg = cfg.get("imagens", {}) if isinstance(cfg, dict) else {}

    state = _get_state(request)
    if not state or not state.get("question_ids"):
        return redirect(reverse("simulado:inicio"))

    idx = int(state.get("index", 0))
    qids = state["question_ids"]

    if idx >= len(qids):
        return redirect(reverse("simulado:resultado"))

    qid = qids[idx]

    answers = state.get("answers", {})
    acertos = sum(1 for v in answers.values() if v.get("is_correct"))
    erros = sum(1 for v in answers.values() if v.get("is_correct") is False)

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
            "acertos": acertos,
            "erros": erros,
            "mode": state.get("mode") or "PROVA",
            "questao": questao,
            "alternativas": alternativas,
            "answered": answered,
            "imagens_cfg_json": json.dumps(imagens_cfg, ensure_ascii=False),
        },
    )


@login_required_audit
@require_http_methods(["POST"])
def simulado_responder(request: HttpRequest) -> HttpResponse:
    assinatura = _get_active_assinatura(request.user)
    if not assinatura:
        log_event(
            request,
            "assinatura_inativa",
            user=request.user,
            contexto={"path": request.path},
        )
        return render(
            request,
            "simulado/erro.html",
            _build_error_context(request, msg="Assinatura inativa ou expirada."),
            status=403,
        )

    state = _get_state(request)
    if not state or not state.get("question_ids"):
        return redirect(reverse("simulado:inicio"))

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
        return render(
            request,
            "simulado/erro.html",
            _build_error_context(request, msg="Alternativa invÃ¡lida."),
            status=400,
        )

    is_correct = bool(alt.is_correta)

    answers = state.get("answers", {})
    answers[qid] = {"alt_id": str(alt_id), "is_correct": is_correct}
    state["answers"] = answers

    # PrÃ³xima questÃ£o (avan?a o Ã­ndice; feedback do modo ESTUDO ? renderizado antes de seguir)
    state["index"] = idx + 1
    if state["index"] >= len(qids) and not state.get("finished_at"):
        state["finished_at"] = _now_iso()
    _set_state(request, state)

    if state.get("mode") == "ESTUDO":
        cfg = get_simulado_config()
        imagens_cfg = cfg.get("imagens", {}) if isinstance(cfg, dict) else {}

        questao = alt.questao
        alternativas = list(
            Alternativa.objects.filter(questao=questao).order_by("ordem")
        )
        correta = next((a for a in alternativas if a.is_correta), None)
        answers_map = state.get("answers", {}) or {}
        total_respostas = len(qids) or 1  # usa total planejado para evitar % inflado no inÃ­cio
        total_answered = len(answers_map) or 1  # usado sÃ³ para contar erros/acertos
        acertos_so_far = sum(1 for data in answers_map.values() if data.get("is_correct"))
        erros_so_far = sum(1 for data in answers_map.values() if data.get("is_correct") is False)
        percent_acerto = round((acertos_so_far / total_respostas) * 100, 2)
        next_url = (
            reverse("simulado:resultado")
            if state["index"] >= len(qids)
            else reverse("simulado:questao")
        )
        return render(
            request,
            "simulado/questao.html",
            {
                "idx": idx,
                "total": len(qids),
                "acertos": acertos_so_far,
                "erros": erros_so_far,
                "mode": state.get("mode") or "PROVA",
                "questao": questao,
                "alternativas": alternativas,
                "answered": answers.get(qid),
                "imagens_cfg_json": json.dumps(imagens_cfg, ensure_ascii=False),
                "feedback": {
                    "is_correct": is_correct,
                    "comentario": questao.comentario,
                    "correta": correta,
                    "selecionada": alt,
                    "next_url": next_url,
                    "is_last": state["index"] >= len(qids),
                    "percent_acerto": percent_acerto,
                },
            },
        )

    if state["index"] >= len(qids):
        return redirect(reverse("simulado:resultado"))

    return redirect(reverse("simulado:questao"))


@login_required_audit
@require_http_methods(["GET", "POST"])
def simulado_resultado(request: HttpRequest) -> HttpResponse:
    assinatura = _get_active_assinatura(request.user)
    if not assinatura:
        log_event(
            request,
            "assinatura_inativa",
            user=request.user,
            contexto={"path": request.path},
        )
        return render(
            request,
            "simulado/erro.html",
            _build_error_context(request, msg="Assinatura inativa ou expirada."),
            status=403,
        )

    state = _get_state(request)
    if not state or not state.get("question_ids"):
        return redirect(reverse("simulado:inicio"))

    qids = state["question_ids"]
    answers = state.get("answers", {})
    mode = state.get("mode") or "PROVA"
    filters = state.get("filters", {}) or {}

    acertos = sum(1 for qid in qids if answers.get(qid, {}).get("is_correct") is True)
    total = len(qids)

    # Se quiser listar revisÃµes, buscamos as questÃµes respondidas
    questoes = list(
        Questao.objects.filter(id__in=qids).select_related("modulo", "curso").order_by("numero_no_modulo")
    )
    questoes_map = {str(q.id): q for q in questoes}

    alternativas = list(
        Alternativa.objects.filter(questao_id__in=qids).order_by("ordem")
    )
    alts_map: dict[str, list[Alternativa]] = {}
    for alt in alternativas:
        key = str(alt.questao_id)
        alts_map.setdefault(key, []).append(alt)

    respondidas = sum(1 for qid in qids if answers.get(str(qid)))
    erros = max(respondidas - acertos, 0)
    nao_respondidas = max(total - respondidas, 0)

    started_at = _parse_ts(state.get("started_at"))
    finished_at = _parse_ts(state.get("finished_at"))
    if not finished_at:
        finished_at = timezone.now()
        state["finished_at"] = finished_at.isoformat()
        _set_state(request, state)

    tempo_total_segundos = None
    tempo_total_human = None
    if started_at and finished_at:
        delta = finished_at - started_at
        tempo_total_segundos = max(int(delta.total_seconds()), 0)
        mins, secs = divmod(tempo_total_segundos, 60)
        tempo_total_human = f"{mins}m {secs:02d}s" if mins else f"{secs}s"

    revisao = []
    for qid in qids:
        q = questoes_map.get(str(qid))
        if not q:
            continue
        info = answers.get(str(qid), {})
        alts = alts_map.get(str(qid), [])
        selecionada = next((a for a in alts if str(a.id) == str(info.get("alt_id"))), None)
        correta = next((a for a in alts if a.is_correta), None)
        revisao.append(
            {
                "questao": q,
                "respondida": bool(info),
                "acertou": info.get("is_correct"),
                "selecionada": selecionada,
                "correta": correta,
            }
        )

    if request.method == "POST":
        # botÃ£o "Novo simulado"
        _clear_state(request)
        return redirect(reverse("simulado:inicio"))

    return render(
        request,
        "simulado/resultado.html",
        {
            "acertos": acertos,
            "total": total,
            "percent": round((acertos / total) * 100, 2) if total else 0,
            "revisao": revisao,
            "respondidas": respondidas,
            "erros": erros,
            "nao_respondidas": nao_respondidas,
            "modo": mode,
            "filters": filters,
            "curso": questoes[0].curso if questoes else None,
            "modulo": next((q.modulo for q in questoes if str(q.modulo_id) == str(state.get("modulo_id"))), None) if state.get("modulo_id") else None,
            "tempo_total_segundos": tempo_total_segundos,
            "tempo_total_human": tempo_total_human,
        },
    )

# O que isso faz:
# recebe curso_id
# busca mÃ³dulos ativos
# retorna JSON limpo e fÃ¡cil pro front usar.
@login_required_audit
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

@login_required_audit
@require_GET
def api_stats(request: HttpRequest) -> JsonResponse:
    """
    Retorna contagens para o config do simulado.
    ParÃ¢metros (GET):
      - curso_id (obrigatÃ³rio)
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

    # Contagens â€œde painelâ€ (do mesmo recorte curso/modulo, mas separadas por critÃ©rio)
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

