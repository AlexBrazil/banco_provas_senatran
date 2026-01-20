from __future__ import annotations

import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods
from django.db.models import Q

from .forms import EmailAuthenticationForm, RegistroForm
from .models import Assinatura, EventoAuditoria, Plano


DEVICE_COOKIE_NAME = "device_id"
DEVICE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365 * 2
REGISTER_COOLDOWN_SECONDS = 2 * 60 * 60


class EmailLoginView(auth_views.LoginView):
    template_name = "registration/login.html"
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.session.set_expiry(settings.SESSION_COOKIE_AGE)
        return response


class EmailLogoutView(auth_views.LogoutView):
    next_page = "login"


def _get_client_ip(request: HttpRequest) -> str:
    return (request.META.get("REMOTE_ADDR") or "").strip()


def _get_device_id(request: HttpRequest) -> tuple[str, bool]:
    device_id = (request.COOKIES.get(DEVICE_COOKIE_NAME) or "").strip()
    if device_id:
        return device_id, False
    return uuid.uuid4().hex, True


def _set_device_cookie(response: HttpResponse, device_id: str) -> None:
    response.set_cookie(
        DEVICE_COOKIE_NAME,
        device_id,
        max_age=DEVICE_COOKIE_MAX_AGE,
        httponly=True,
        samesite="Lax",
    )


def _safe_next_url(request: HttpRequest) -> str:
    raw = (request.POST.get("next") or request.GET.get("next") or "").strip()
    if raw and url_has_allowed_host_and_scheme(raw, allowed_hosts={request.get_host()}):
        return raw
    return reverse("simulado:inicio")


def _cooldown_remaining(ip: str, device_id: str) -> timedelta | None:
    if not ip and not device_id:
        return None

    cutoff = timezone.now() - timedelta(seconds=REGISTER_COOLDOWN_SECONDS)
    filters = Q()
    if ip:
        filters |= Q(ip=ip)
    if device_id:
        filters |= Q(device_id=device_id)

    last_event = (
        EventoAuditoria.objects
        .filter(tipo="auth_register", timestamp__gte=cutoff)
        .filter(filters)
        .order_by("-timestamp")
        .first()
    )
    if not last_event:
        return None
    elapsed = timezone.now() - last_event.timestamp
    remaining = timedelta(seconds=REGISTER_COOLDOWN_SECONDS) - elapsed
    if remaining.total_seconds() <= 0:
        return None
    return remaining


def _format_remaining(remaining: timedelta) -> str:
    total_minutes = int(remaining.total_seconds() // 60) + 1
    hours, minutes = divmod(total_minutes, 60)
    if hours <= 0:
        return f"{minutes} minutos"
    if minutes == 0:
        return f"{hours} horas"
    return f"{hours}h {minutes}min"


def _create_free_assinatura(user, plano: Plano) -> Assinatura:
    now = timezone.now()
    valid_until = None
    if plano.validade_dias:
        valid_until = now + timedelta(days=plano.validade_dias)
    return Assinatura.objects.create(
        usuario=user,
        plano=plano,
        nome_plano_snapshot=plano.nome,
        limite_qtd_snapshot=plano.limite_qtd,
        limite_periodo_snapshot=plano.limite_periodo,
        validade_dias_snapshot=plano.validade_dias,
        ciclo_cobranca_snapshot=plano.ciclo_cobranca,
        preco_snapshot=plano.preco,
        status=Assinatura.Status.ATIVO,
        inicio=now,
        valid_until=valid_until,
    )


@require_http_methods(["GET", "POST"])
def registrar(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect(_safe_next_url(request))

    device_id, new_device = _get_device_id(request)
    ip = _get_client_ip(request)
    next_url = (request.POST.get("next") or request.GET.get("next") or "").strip()

    if request.method == "POST":
        remaining = _cooldown_remaining(ip, device_id)
        if remaining:
            EventoAuditoria.objects.create(
                tipo="auth_register_blocked",
                usuario=None,
                ip=ip or None,
                device_id=device_id,
                contexto_json={"motivo": "cooldown", "restante": _format_remaining(remaining)},
            )
            form = RegistroForm()
            msg = f"Aguarde { _format_remaining(remaining) } para cadastrar outra conta."
            response = render(
                request,
                "registration/register.html",
                {"form": form, "cooldown_message": msg, "next": next_url},
            )
            if new_device:
                _set_device_cookie(response, device_id)
            return response

        form = RegistroForm(request.POST)
        if form.is_valid():
            plano_free = Plano.objects.filter(nome__iexact="Free", ativo=True).first()
            if not plano_free:
                form.add_error(None, "Plano Free nao encontrado. Contate o suporte.")
            else:
                user = form.save()
                assinatura = _create_free_assinatura(user, plano_free)
                login(request, user)
                request.session.set_expiry(settings.SESSION_COOKIE_AGE)
                EventoAuditoria.objects.create(
                    tipo="auth_register",
                    usuario=user,
                    ip=ip or None,
                    device_id=device_id,
                    contexto_json={"plano": assinatura.nome_plano_snapshot},
                )
                response = redirect(_safe_next_url(request))
                if new_device:
                    _set_device_cookie(response, device_id)
                return response
    else:
        form = RegistroForm()

    response = render(request, "registration/register.html", {"form": form, "next": next_url})
    if new_device:
        _set_device_cookie(response, device_id)
    return response
