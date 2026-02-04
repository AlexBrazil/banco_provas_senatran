from __future__ import annotations

import base64
import hashlib
import hmac
from typing import Any

import requests
from django.conf import settings


class AbacatePayError(RuntimeError):
    pass


def _auth_headers() -> dict[str, str]:
    token = (settings.ABACATEPAY_API_TOKEN or "").strip()
    if not token:
        raise AbacatePayError("Token AbacatePay nao configurado.")
    return {
        "accept": "application/json",
        "authorization": f"Bearer {token}",
        "content-type": "application/json",
    }


def create_pix_qrcode(
    *,
    amount_centavos: int,
    description: str,
    metadata: dict[str, Any] | None = None,
    expires_in: int = 3600,
) -> dict:
    payload = {
        "amount": amount_centavos,
        "expiresIn": expires_in,
        "description": description[:140],
        "metadata": metadata or {},
    }
    url = f"{settings.ABACATEPAY_API_URL}/v1/pixQrCode/create"
    resp = requests.post(url, headers=_auth_headers(), json=payload, timeout=20)
    if resp.status_code >= 400:
        raise AbacatePayError(f"HTTP {resp.status_code} - {resp.text}")
    try:
        data = resp.json()
    except ValueError:
        raise AbacatePayError(f"Resposta invalida (nao-JSON). HTTP {resp.status_code} - {resp.text}")
    if data.get("error"):
        raise AbacatePayError(f"{data.get('error')} - {data}")
    return data.get("data") or {}


def check_pix_qrcode(pix_id: str) -> dict:
    if not pix_id:
        raise AbacatePayError("pix_id ausente.")
    url = f"{settings.ABACATEPAY_API_URL}/v1/pixQrCode/check"
    resp = requests.get(url, headers=_auth_headers(), params={"id": pix_id}, timeout=20)
    if resp.status_code >= 400:
        raise AbacatePayError(f"HTTP {resp.status_code} - {resp.text}")
    try:
        data = resp.json()
    except ValueError:
        raise AbacatePayError(f"Resposta invalida (nao-JSON). HTTP {resp.status_code} - {resp.text}")
    if data.get("error"):
        raise AbacatePayError(f"{data.get('error')} - {data}")
    return data.get("data") or {}


def _iter_webhook_keys() -> list[bytes]:
    keys = []
    for key in (
        settings.ABACATEPAY_WEBHOOK_PUBLIC_HMAC_KEY,
        settings.ABACATEPAY_WEBHOOK_SECRET,
    ):
        key = (key or "").strip()
        if key:
            keys.append(key.encode("utf-8"))
    return keys


def _normalize_signature(signature: str) -> str:
    signature = (signature or "").strip()
    if not signature:
        return ""
    if "=" in signature:
        prefix, value = signature.split("=", 1)
        if prefix.lower() in {"sha256", "v1", "hmac", "sig", "signature"}:
            return value.strip()
    return signature


def verify_webhook_signature(raw_body: bytes, signature: str) -> bool:
    keys = _iter_webhook_keys()
    if not keys:
        return True
    normalized = _normalize_signature(signature)
    if not normalized:
        return False
    for key in keys:
        digest = hmac.new(key, raw_body, hashlib.sha256).digest()
        digest_hex = digest.hex()
        digest_b64 = base64.b64encode(digest).decode("ascii")
        digest_b64_url = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
        if (
            hmac.compare_digest(digest_hex, normalized)
            or hmac.compare_digest(digest_b64, normalized)
            or hmac.compare_digest(digest_b64_url, normalized)
        ):
            return True
    return False
