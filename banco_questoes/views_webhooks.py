import base64
import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


# Logger do módulo (NECESSÁRIO para evitar erro do Pylance)
logger: logging.Logger = logging.getLogger(__name__)


def verify_woovi_signature(request) -> bool:
    """
    Woovi/OpenPix webhook signature:
    - Header: x-webhook-signature
    - Value: Base64( HMAC-SHA256(secret, raw_body) )

    Regras:
    - Se não houver secret configurado, NÃO aceita (retorna False).
    - A validação deve usar o body bruto (request.body) exatamente como chegou.
    """
    secret = getattr(settings, "OPENPIX_WEBHOOK_SECRET", "")
    if not secret:
        return False

    received_sig = request.headers.get("x-webhook-signature", "")
    if not received_sig:
        return False

    raw_body = request.body or b""

    mac = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).digest()

    expected_sig = base64.b64encode(mac).decode("utf-8")

    # comparação segura (timing-attack safe)
    return hmac.compare_digest(received_sig, expected_sig)


@csrf_exempt
@require_http_methods(["POST"])
def openpix_webhook(request):
    # 1) Validar assinatura (SEMPRE antes de parsear JSON)
    if not verify_woovi_signature(request):
        return HttpResponse(status=401)

    # 2) Parse do JSON
    try:
        payload = json.loads((request.body or b"").decode("utf-8"))
    except Exception:
        return HttpResponse(status=400)

    # 3) Log informativo (útil para descobrir o shape real do payload)
    logger.info(
        "Woovi webhook recebido | event=%s",
        payload.get("event")
        or payload.get("type")
        or payload.get("name")
        or "sem_evento",
    )

    # 4) TODO (Versão 2):
    # - extrair correlationID
    # - idempotência
    # - marcar pedido como PAID quando evento for de pagamento confirmado

    # 5) ACK 200 (essencial para Woovi não reenviar)
    return JsonResponse({"ok": True})
