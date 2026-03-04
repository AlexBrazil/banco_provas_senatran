from __future__ import annotations

import hashlib
from typing import Any

import requests
from django.conf import settings
from django.utils import timezone


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalize_email(user) -> str:
    if not user:
        return ""
    email = (getattr(user, "email", "") or "").strip().lower()
    if email:
        return email
    username = (getattr(user, "username", "") or "").strip().lower()
    if "@" in username:
        return username
    return ""


def build_user_data(*, request=None, user=None) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    email = _normalize_email(user)
    if email:
        payload["em"] = _sha256(email)
    user_id = getattr(user, "id", None)
    if user_id is not None:
        payload["external_id"] = _sha256(str(user_id))
    if request is not None:
        ip = (request.META.get("REMOTE_ADDR") or "").strip()
        if ip:
            payload["client_ip_address"] = ip
        ua = (request.META.get("HTTP_USER_AGENT") or "").strip()
        if ua:
            payload["client_user_agent"] = ua
    return payload


def send_meta_event(
    *,
    event_name: str,
    event_id: str,
    request=None,
    user=None,
    custom_data: dict[str, Any] | None = None,
    event_source_url: str = "",
    action_source: str = "website",
) -> dict[str, Any]:
    if not settings.META_CAPI_ENABLED:
        return {"ok": False, "skipped": True, "reason": "capi_disabled"}

    pixel_id = (settings.META_PIXEL_ID or "").strip()
    token = (settings.META_CAPI_ACCESS_TOKEN or "").strip()
    version = (settings.META_CAPI_API_VERSION or "v20.0").strip()
    if not pixel_id:
        return {"ok": False, "skipped": True, "reason": "pixel_id_missing"}
    if not token:
        return {"ok": False, "skipped": True, "reason": "access_token_missing"}
    if not event_name:
        return {"ok": False, "skipped": True, "reason": "event_name_missing"}
    if not event_id:
        return {"ok": False, "skipped": True, "reason": "event_id_missing"}

    endpoint = f"https://graph.facebook.com/{version}/{pixel_id}/events"
    data_item: dict[str, Any] = {
        "event_name": event_name,
        "event_time": int(timezone.now().timestamp()),
        "event_id": event_id,
        "action_source": action_source,
        "user_data": build_user_data(request=request, user=user),
    }
    if custom_data:
        data_item["custom_data"] = custom_data
    if event_source_url:
        data_item["event_source_url"] = event_source_url

    payload: dict[str, Any] = {"data": [data_item]}
    if settings.META_CAPI_TEST_EVENT_CODE:
        payload["test_event_code"] = settings.META_CAPI_TEST_EVENT_CODE

    try:
        response = requests.post(
            endpoint,
            params={"access_token": token},
            json=payload,
            timeout=10,
        )
    except Exception as exc:
        return {
            "ok": False,
            "skipped": False,
            "reason": "request_exception",
            "error": str(exc),
        }

    if response.status_code >= 400:
        return {
            "ok": False,
            "skipped": False,
            "reason": "http_error",
            "status_code": response.status_code,
            "response_text": response.text[:500],
        }

    return {"ok": True, "skipped": False, "status_code": response.status_code}

