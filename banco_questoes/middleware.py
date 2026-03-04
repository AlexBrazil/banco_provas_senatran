from __future__ import annotations

import uuid

from django.conf import settings

from .meta_capi import send_meta_event


class MetaPageViewCapiMiddleware:
    PAGEVIEW_NAMESPACES = {
        "menu",
        "simulado",
        "payments",
        "perguntas_respostas",
        "apostila_cnh",
        "simulacao_prova",
        "manual_pratico",
        "aprenda_jogando",
        "oraculo",
        "aprova_plus",
    }
    AUTH_PATH_PREFIXES = (
        "/login/",
        "/registrar/",
        "/logout/",
        "/senha/reset/",
    )
    EXCLUDED_PATH_PREFIXES = (
        "/admin/",
        "/simulado/api/",
        "/payments/upgrade/free/status/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def _eligible_request(self, request) -> bool:
        if request.method != "GET":
            return False
        path = (request.path or "").strip()
        if any(path.startswith(prefix) for prefix in self.EXCLUDED_PATH_PREFIXES):
            return False
        resolver = getattr(request, "resolver_match", None)
        namespace = getattr(resolver, "namespace", "") if resolver else ""
        if namespace in self.PAGEVIEW_NAMESPACES:
            return True
        return any(path.startswith(prefix) for prefix in self.AUTH_PATH_PREFIXES)

    def __call__(self, request):
        pageview_event_id = f"pv-{uuid.uuid4().hex}"
        setattr(request, "_meta_pageview_event_id", pageview_event_id)
        response = self.get_response(request)

        should_send = self._eligible_request(request)
        if not should_send:
            return response
        if not settings.META_CAPI_ENABLED:
            return response
        content_type = str(response.headers.get("Content-Type") or "").lower()
        if "text/html" not in content_type:
            return response

        send_meta_event(
            event_name="PageView",
            event_id=pageview_event_id,
            request=request,
            user=getattr(request, "user", None),
            event_source_url=request.build_absolute_uri(),
        )
        return response
