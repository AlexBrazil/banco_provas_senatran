from __future__ import annotations

from typing import Any

from django.http import HttpRequest

from .models import EventoAuditoria


DEVICE_COOKIE_NAME = "device_id"


def get_client_ip(request: HttpRequest) -> str:
    return (request.META.get("REMOTE_ADDR") or "").strip()


def get_device_id(request: HttpRequest) -> str:
    return (request.COOKIES.get(DEVICE_COOKIE_NAME) or "").strip()


def log_event(
    request: HttpRequest,
    tipo: str,
    *,
    user=None,
    contexto: dict[str, Any] | None = None,
    ip: str | None = None,
    device_id: str | None = None,
) -> None:
    EventoAuditoria.objects.create(
        tipo=tipo,
        usuario=user,
        ip=(ip or get_client_ip(request)) or None,
        device_id=(device_id or get_device_id(request)),
        contexto_json=contexto or {},
    )
