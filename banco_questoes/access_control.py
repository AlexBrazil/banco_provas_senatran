from __future__ import annotations

from datetime import timedelta
from functools import wraps
from typing import Any, Callable

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from .auditoria import log_event
from .models import AppModulo, Assinatura, PlanoPermissaoApp, UsoAppJanela


def get_assinatura_ativa(user) -> Assinatura | None:
    if not getattr(user, "is_authenticated", False):
        return None

    now = timezone.now()
    return (
        Assinatura.objects.filter(usuario=user, status=Assinatura.Status.ATIVO)
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=now))
        .order_by("-inicio", "-criado_em")
        .first()
    )


def get_regra_app(assinatura: Assinatura | None, app_slug: str) -> PlanoPermissaoApp | None:
    if not assinatura or not assinatura.plano_id:
        return None
    return (
        PlanoPermissaoApp.objects.select_related("plano", "app_modulo")
        .filter(
            plano_id=assinatura.plano_id,
            app_modulo__slug=app_slug,
            app_modulo__ativo=True,
        )
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


def _get_janela_atual(
    inicio: timezone.datetime,
    period_seconds: int,
) -> tuple[timezone.datetime, timezone.datetime]:
    now = timezone.now()
    elapsed = max((now - inicio).total_seconds(), 0)
    index = int(elapsed // period_seconds)
    janela_inicio = inicio + timedelta(seconds=index * period_seconds)
    janela_fim = janela_inicio + timedelta(seconds=period_seconds)
    return janela_inicio, janela_fim


def _nome_plano(assinatura: Assinatura | None) -> str:
    if not assinatura:
        return ""
    if assinatura.nome_plano_snapshot:
        return assinatura.nome_plano_snapshot
    if assinatura.plano:
        return assinatura.plano.nome
    return ""


def check_and_increment_app_use(user, app_slug: str) -> tuple[bool, str | None, dict[str, Any]]:
    contexto: dict[str, Any] = {"app_slug": app_slug}
    assinatura = get_assinatura_ativa(user)
    if not assinatura:
        contexto["motivo"] = "assinatura_inativa"
        return False, "Assinatura inativa ou expirada.", contexto

    contexto["plano"] = _nome_plano(assinatura)
    regra = get_regra_app(assinatura, app_slug)
    if not regra:
        if AppModulo.objects.filter(slug=app_slug, ativo=True).exists():
            contexto["motivo"] = "regra_ausente"
            return False, "Regra de acesso nao configurada para seu plano.", contexto
        contexto["motivo"] = "app_ausente"
        return False, "Modulo nao configurado.", contexto

    if not regra.permitido:
        contexto["motivo"] = "plano_sem_permissao"
        return False, "Este modulo nao esta liberado no seu plano.", contexto

    limite = regra.limite_qtd
    periodo = regra.limite_periodo
    contexto.update({"limite_qtd": limite, "limite_periodo": periodo})

    if limite is None:
        contexto["motivo"] = "liberado_ilimitado"
        return True, None, contexto

    if limite <= 0:
        contexto["motivo"] = "limite_invalido"
        return False, "Limite indisponivel para este modulo.", contexto

    period_seconds = _get_period_seconds(periodo)
    if not period_seconds:
        contexto["motivo"] = "periodo_invalido"
        return False, "Regra de limite sem periodo configurado para este modulo.", contexto

    inicio = assinatura.inicio or timezone.now()
    if assinatura.inicio is None:
        assinatura.inicio = inicio
        assinatura.save(update_fields=["inicio", "atualizado_em"])

    janela_inicio, janela_fim = _get_janela_atual(inicio, period_seconds)

    with transaction.atomic():
        uso, _ = (
            UsoAppJanela.objects.select_for_update().get_or_create(
                usuario=user,
                app_modulo=regra.app_modulo,
                janela_inicio=janela_inicio,
                janela_fim=janela_fim,
                defaults={"contador": 0},
            )
        )
        if uso.contador >= limite:
            contexto.update(
                {
                    "motivo": "limite_atingido",
                    "janela_inicio": janela_inicio.isoformat(),
                    "janela_fim": janela_fim.isoformat(),
                    "contador": uso.contador,
                }
            )
            return False, "Limite de uso atingido para este modulo no periodo atual.", contexto

        uso.contador += 1
        uso.save(update_fields=["contador", "atualizado_em"])

    contexto.update(
        {
            "motivo": "liberado_com_limite",
            "janela_inicio": janela_inicio.isoformat(),
            "janela_fim": janela_fim.isoformat(),
            "contador": uso.contador,
            "restantes": max(limite - uso.contador, 0),
        }
    )
    return True, None, contexto


def build_app_access_status(user) -> dict[str, Any]:
    apps = list(AppModulo.objects.filter(ativo=True).order_by("ordem_menu", "nome"))
    assinatura = get_assinatura_ativa(user)
    regras_por_app_id: dict[int, PlanoPermissaoApp] = {}

    if assinatura and assinatura.plano_id:
        regras_por_app_id = {
            regra.app_modulo_id: regra
            for regra in PlanoPermissaoApp.objects.filter(
                plano_id=assinatura.plano_id,
                app_modulo__in=apps,
            ).select_related("app_modulo")
        }

    status_apps = []
    for app in apps:
        regra = regras_por_app_id.get(app.id)
        liberado = bool(regra and regra.permitido and assinatura)
        status_apps.append(
            {
                "slug": app.slug,
                "nome": app.nome,
                "ordem_menu": app.ordem_menu,
                "icone_path": app.icone_path,
                "rota_nome": app.rota_nome,
                "ativo": app.ativo,
                "liberado": liberado,
                "em_construcao": app.em_construcao,
                "bloqueado_plano": bool(assinatura and regra and not regra.permitido),
                "regra_ausente": bool(assinatura and not regra),
            }
        )

    return {
        "assinatura_ativa": bool(assinatura),
        "plano": _nome_plano(assinatura),
        "apps": status_apps,
        "por_slug": {item["slug"]: item for item in status_apps},
    }


def require_app_access(app_slug: str) -> Callable:
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def _wrapped(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path(), login_url=settings.LOGIN_URL)

            if not getattr(settings, "APP_ACCESS_V2_ENABLED", False):
                return view_func(request, *args, **kwargs)

            allowed, reason, contexto = check_and_increment_app_use(request.user, app_slug)
            if allowed:
                log_event(request, "app_access_granted", user=request.user, contexto=contexto)
                return view_func(request, *args, **kwargs)

            assinatura = get_assinatura_ativa(request.user)
            plano_nome = _nome_plano(assinatura)
            show_upgrade_cta = plano_nome.strip().lower() == "free"
            upgrade_url = reverse("payments:upgrade_free") if show_upgrade_cta else ""
            log_event(
                request,
                "app_access_blocked",
                user=request.user,
                contexto={**contexto, "reason": reason or ""},
            )
            return render(
                request,
                "menu/access_blocked.html",
                {
                    "app_slug": app_slug,
                    "reason": reason or "Acesso bloqueado para este modulo.",
                    "plano_nome": plano_nome,
                    "show_upgrade_cta": show_upgrade_cta,
                    "upgrade_url": upgrade_url,
                },
                status=403,
            )

        return _wrapped

    return decorator
