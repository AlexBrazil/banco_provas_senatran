from __future__ import annotations

import json
import uuid
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from banco_questoes.auditoria import log_event
from banco_questoes.models import Assinatura, EventoAuditoria, Plano

from .abacatepay import AbacatePayError, check_pix_qrcode, create_pix_qrcode, verify_webhook_signature
from .models import Billing, WebhookEvent


FREE_PLAN_NAME = "Free"
UPGRADE_PLAN_NAME = "Free Upgrade"
MANUAL_CHECK_DELAY_SECONDS = 60
CHECK_COOLDOWN_SECONDS = 30


def _get_active_assinatura(user) -> Assinatura | None:
    now = timezone.now()
    return (
        Assinatura.objects
        .filter(usuario=user, status=Assinatura.Status.ATIVO)
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=now))
        .order_by("-inicio", "-criado_em")
        .first()
    )


def _assinatura_is_free(assinatura: Assinatura) -> bool:
    nome = assinatura.nome_plano_snapshot or (assinatura.plano.nome if assinatura.plano else "")
    return nome.strip().lower() == FREE_PLAN_NAME.lower()


def _get_plano_upgrade() -> Plano | None:
    return Plano.objects.filter(nome__iexact=UPGRADE_PLAN_NAME, ativo=True).first()


def _preco_para_centavos(preco: Decimal) -> int:
    try:
        return int((preco * Decimal("100")).quantize(Decimal("1")))
    except (InvalidOperation, TypeError):
        return 0


def _build_checkout_context(
    *,
    plano: Plano,
    billing: Billing | None = None,
    message: str = "",
    error: str = "",
) -> dict:
    now = timezone.now()
    show_manual_check = False
    manual_check_delay = 0
    if billing and billing.status == Billing.Status.PENDING:
        elapsed = (now - billing.criado_em).total_seconds()
        manual_check_delay = max(MANUAL_CHECK_DELAY_SECONDS - int(elapsed), 0)
        show_manual_check = manual_check_delay == 0

    return {
        "plano": plano,
        "billing": billing,
        "message": message,
        "error": error,
        "show_manual_check": show_manual_check,
        "manual_check_delay": manual_check_delay,
        "manual_check_delay_seconds": MANUAL_CHECK_DELAY_SECONDS,
    }


def _registrar_troca_plano(
    *,
    user,
    plano_origem: str,
    plano_destino: str,
    billing: Billing,
) -> None:
    EventoAuditoria.objects.create(
        tipo="plano_trocado_pix",
        usuario=user,
        ip=None,
        device_id="",
        contexto_json={
            "usuario_id": user.id,
            "plano_origem": plano_origem,
            "plano_destino": plano_destino,
            "billing_id": billing.id,
            "billing_ref": billing.billing_ref,
            "valor_centavos": billing.valor_centavos,
            "metodo": "PIX",
        },
    )


def _ativar_plano_upgrade(*, user, plano_upgrade: Plano, billing: Billing) -> None:
    now = timezone.now()
    valid_until = None
    if plano_upgrade.validade_dias:
        valid_until = now + timedelta(days=plano_upgrade.validade_dias)

    with transaction.atomic():
        Assinatura.objects.filter(usuario=user, status=Assinatura.Status.ATIVO).update(
            status=Assinatura.Status.EXPIRADO,
        )
        Assinatura.objects.create(
            usuario=user,
            plano=plano_upgrade,
            nome_plano_snapshot=plano_upgrade.nome,
            limite_qtd_snapshot=plano_upgrade.limite_qtd,
            limite_periodo_snapshot=plano_upgrade.limite_periodo,
            validade_dias_snapshot=plano_upgrade.validade_dias,
            ciclo_cobranca_snapshot=plano_upgrade.ciclo_cobranca,
            preco_snapshot=plano_upgrade.preco,
            status=Assinatura.Status.ATIVO,
            inicio=now,
            valid_until=valid_until,
        )

    _registrar_troca_plano(
        user=user,
        plano_origem=FREE_PLAN_NAME,
        plano_destino=plano_upgrade.nome,
        billing=billing,
    )


def _finalizar_billing_pago(billing: Billing, payload: dict) -> bool:
    if billing.status == Billing.Status.PAID:
        return False
    billing.status = Billing.Status.PAID
    billing.payload_webhook = payload or {}
    billing.save(update_fields=["status", "payload_webhook", "atualizado_em"])
    return True


@login_required
@require_http_methods(["GET", "POST"])
def upgrade_free(request: HttpRequest) -> HttpResponse:
    assinatura = _get_active_assinatura(request.user)
    if not assinatura or not _assinatura_is_free(assinatura):
        return render(
            request,
            "simulado/erro.html",
            {"msg": "Upgrade disponivel apenas para usuarios do plano Free."},
            status=403,
        )

    plano_upgrade = _get_plano_upgrade()
    if not plano_upgrade:
        return render(
            request,
            "simulado/erro.html",
            {"msg": "Plano Free Upgrade indisponivel. Contate o suporte."},
            status=503,
        )

    if request.method == "POST":
        valor_centavos = _preco_para_centavos(plano_upgrade.preco)
        if valor_centavos <= 0:
            return render(
                request,
                "simulado/erro.html",
                {"msg": "Valor invalido para cobranca. Contate o suporte."},
                status=500,
            )

        billing_ref = uuid.uuid4().hex
        try:
            pix_data = create_pix_qrcode(
                amount_centavos=valor_centavos,
                description=f"Upgrade {plano_upgrade.nome}",
                metadata={
                    "billing_ref": str(billing_ref),
                    "user_id": str(request.user.id),
                    "plano_id": str(plano_upgrade.id),
                },
            )
        except AbacatePayError as exc:
            return render(
                request,
                "simulado/erro.html",
                {"msg": f"Falha ao gerar cobranca PIX. {exc}"},
                status=502,
            )

        billing = Billing.objects.create(
            usuario=request.user,
            plano_destino=plano_upgrade,
            billing_ref=billing_ref,
            valor_centavos=valor_centavos,
            status=Billing.Status.PENDING,
            pix_id=str(pix_data.get("id") or ""),
            pix_qrcode_base64=str(pix_data.get("brCodeBase64") or ""),
            pix_br_code=str(pix_data.get("brCode") or ""),
            payload_criacao=pix_data or {},
        )
        log_event(
            request,
            "pix_qrcode_criado",
            user=request.user,
            contexto={"billing_id": billing.id, "billing_ref": billing_ref},
        )

        context = _build_checkout_context(plano=plano_upgrade, billing=billing)
        return render(request, "payments/checkout_free_pix.html", context)

    context = _build_checkout_context(plano=plano_upgrade)
    return render(request, "payments/checkout_free_pix.html", context)


@login_required
@require_http_methods(["POST"])
def upgrade_free_check(request: HttpRequest) -> HttpResponse:
    billing_id = (request.POST.get("billing_id") or "").strip()
    billing = (
        Billing.objects
        .select_related("plano_destino")
        .filter(id=billing_id, usuario=request.user)
        .first()
    )
    if not billing:
        return render(
            request,
            "simulado/erro.html",
            {"msg": "Cobranca nao encontrada."},
            status=404,
        )

    plano_upgrade = billing.plano_destino
    if billing.status != Billing.Status.PENDING:
        context = _build_checkout_context(
            plano=plano_upgrade,
            billing=billing,
            message="Pagamento ja processado.",
        )
        return render(request, "payments/checkout_free_pix.html", context)

    now = timezone.now()
    if billing.criado_em and (now - billing.criado_em).total_seconds() < MANUAL_CHECK_DELAY_SECONDS:
        context = _build_checkout_context(
            plano=plano_upgrade,
            billing=billing,
            error="Aguarde pelo menos 1 minuto antes de revalidar.",
        )
        return render(request, "payments/checkout_free_pix.html", context)

    if billing.last_check_at and (now - billing.last_check_at).total_seconds() < CHECK_COOLDOWN_SECONDS:
        context = _build_checkout_context(
            plano=plano_upgrade,
            billing=billing,
            error="Aguarde alguns segundos antes de tentar novamente.",
        )
        return render(request, "payments/checkout_free_pix.html", context)

    billing.last_check_at = now
    billing.save(update_fields=["last_check_at"])
    log_event(
        request,
        "pix_check_iniciado",
        user=request.user,
        contexto={"billing_id": billing.id, "billing_ref": billing.billing_ref},
    )

    try:
        pix_status = check_pix_qrcode(billing.pix_id)
    except AbacatePayError as exc:
        context = _build_checkout_context(
            plano=plano_upgrade,
            billing=billing,
            error=f"Falha ao revalidar pagamento. {exc}",
        )
        return render(request, "payments/checkout_free_pix.html", context)

    status = str(pix_status.get("status") or "").upper()
    if status == "PAID":
        changed = _finalizar_billing_pago(billing, pix_status)
        if changed:
            _ativar_plano_upgrade(user=request.user, plano_upgrade=plano_upgrade, billing=billing)
        log_event(
            request,
            "pix_check_pago",
            user=request.user,
            contexto={"billing_id": billing.id, "billing_ref": billing.billing_ref},
        )
        context = _build_checkout_context(
            plano=plano_upgrade,
            billing=billing,
            message="Pagamento confirmado. Plano atualizado.",
        )
        return render(request, "payments/checkout_free_pix.html", context)

    if status == "EXPIRED":
        billing.status = Billing.Status.EXPIRED
        billing.save(update_fields=["status", "atualizado_em"])

    log_event(
        request,
        "pix_check_pendente",
        user=request.user,
        contexto={"billing_id": billing.id, "billing_ref": billing.billing_ref, "status": status},
    )
    context = _build_checkout_context(
        plano=plano_upgrade,
        billing=billing,
        error="Pagamento ainda nao confirmado.",
    )
    return render(request, "payments/checkout_free_pix.html", context)


@csrf_exempt
@require_http_methods(["POST"])
def webhook_abacatepay(request: HttpRequest) -> HttpResponse:
    raw_body = request.body or b""
    signature = request.headers.get(settings.ABACATEPAY_WEBHOOK_SIGNATURE_HEADER, "")
    if settings.ABACATEPAY_WEBHOOK_SECRET:
        if not verify_webhook_signature(raw_body, signature):
            return JsonResponse({"ok": False, "error": "invalid_signature"}, status=400)

    try:
        payload = {} if not raw_body else json.loads(raw_body.decode("utf-8"))
    except Exception:
        payload = {}

    event_type = (
        payload.get("type")
        or payload.get("event")
        or payload.get("eventType")
        or payload.get("name")
        or ""
    )
    event_id = str(payload.get("id") or payload.get("eventId") or "")

    webhook_event = WebhookEvent.objects.create(
        event_id=event_id,
        tipo=event_type or "unknown",
        payload=payload or {},
        status_processamento="PENDING",
    )

    if event_type != "billing.paid":
        webhook_event.status_processamento = "IGNORED"
        webhook_event.processado_em = timezone.now()
        webhook_event.save(update_fields=["status_processamento", "processado_em"])
        return JsonResponse({"ok": True, "ignored": True})

    pix_id = ""
    metadata = {}
    if isinstance(payload.get("data"), dict):
        data = payload.get("data")
        metadata = data.get("metadata") or {}
        pix_id = (
            str(data.get("id") or "")
            or str((data.get("pix") or {}).get("id") or "")
            or str((data.get("pixQrCode") or {}).get("id") or "")
        )
    else:
        metadata = payload.get("metadata") or {}
        pix_id = str(payload.get("pix_id") or payload.get("pixId") or "")

    billing_ref = str(metadata.get("billing_ref") or "")
    billing = None
    if billing_ref:
        billing = Billing.objects.filter(billing_ref=billing_ref).select_related("plano_destino", "usuario").first()
    if not billing and pix_id:
        billing = Billing.objects.filter(pix_id=pix_id).select_related("plano_destino", "usuario").first()

    if not billing:
        webhook_event.status_processamento = "NOT_FOUND"
        webhook_event.processado_em = timezone.now()
        webhook_event.save(update_fields=["status_processamento", "processado_em"])
        return JsonResponse({"ok": False, "error": "billing_not_found"}, status=404)

    changed = _finalizar_billing_pago(billing, payload)
    if changed:
        _ativar_plano_upgrade(user=billing.usuario, plano_upgrade=billing.plano_destino, billing=billing)

    webhook_event.status_processamento = "OK"
    webhook_event.processado_em = timezone.now()
    webhook_event.save(update_fields=["status_processamento", "processado_em"])
    return JsonResponse({"ok": True})
