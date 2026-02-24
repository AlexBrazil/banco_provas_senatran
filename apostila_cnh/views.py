from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterator

from django.http import FileResponse
from django.http import HttpResponse
from django.http import JsonResponse
from django.http import StreamingHttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_http_methods

from banco_questoes.access_control import require_app_access

from .models import ApostilaDocumento, ApostilaPagina, ApostilaProgressoLeitura
from .services.ingestao_pdf import normalizar_texto_busca


APP_SLUG = "apostila-cnh"
RANGE_HEADER_RE = re.compile(r"bytes=(\d*)-(\d*)$")


def _get_documento_ativo() -> ApostilaDocumento | None:
    return (
        ApostilaDocumento.objects.filter(ativo=True)
        .order_by("-atualizado_em")
        .first()
    )


def _iter_file_segment(file_path: Path, start: int, length: int, chunk_size: int = 64 * 1024) -> Iterator[bytes]:
    with file_path.open("rb") as fh:
        fh.seek(start)
        remaining = length
        while remaining > 0:
            data = fh.read(min(chunk_size, remaining))
            if not data:
                break
            remaining -= len(data)
            yield data


def _build_partial_content_response(
    *,
    file_path: Path,
    file_size: int,
    range_header: str,
    method: str,
    filename: str,
):
    match = RANGE_HEADER_RE.match(range_header.strip())
    if not match:
        return HttpResponse(status=416, headers={"Content-Range": f"bytes */{file_size}"})

    start_str, end_str = match.groups()
    if not start_str and not end_str:
        return HttpResponse(status=416, headers={"Content-Range": f"bytes */{file_size}"})

    if not start_str:
        # Suffix range: bytes=-N
        suffix_len = int(end_str)
        if suffix_len <= 0:
            return HttpResponse(status=416, headers={"Content-Range": f"bytes */{file_size}"})
        start = max(file_size - suffix_len, 0)
        end = file_size - 1
    else:
        start = int(start_str)
        end = int(end_str) if end_str else file_size - 1

    if start >= file_size or start < 0:
        return HttpResponse(status=416, headers={"Content-Range": f"bytes */{file_size}"})

    end = min(end, file_size - 1)
    if end < start:
        return HttpResponse(status=416, headers={"Content-Range": f"bytes */{file_size}"})

    length = end - start + 1
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(length),
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Content-Disposition": f'inline; filename="{filename}"',
    }
    if method == "HEAD":
        return HttpResponse(status=206, content_type="application/pdf", headers=headers)

    response = StreamingHttpResponse(
        _iter_file_segment(file_path=file_path, start=start, length=length),
        status=206,
        content_type="application/pdf",
    )
    for key, value in headers.items():
        response[key] = value
    return response


@require_app_access(APP_SLUG, consume=True)
def index(request):
    documento_ativo = _get_documento_ativo()
    return render(
        request,
        "apostila_cnh/index.html",
        {
            "app_title": "Apostila da CNH do Brasil",
            "tem_documento_ativo": bool(documento_ativo),
            "documento_ativo_titulo": documento_ativo.titulo if documento_ativo else "",
            "api_documento_ativo_url": reverse("apostila_cnh:api_documento_ativo"),
            "api_documento_ativo_pdf_url": reverse("apostila_cnh:api_documento_ativo_pdf"),
            "api_progresso_url": reverse("apostila_cnh:api_progresso"),
            "api_busca_url": reverse("apostila_cnh:api_busca"),
            "viewer_config": {
                "api_documento_ativo_url": reverse("apostila_cnh:api_documento_ativo"),
                "api_documento_ativo_pdf_url": reverse("apostila_cnh:api_documento_ativo_pdf"),
                "api_progresso_url": reverse("apostila_cnh:api_progresso"),
                "api_busca_url": reverse("apostila_cnh:api_busca"),
            },
        },
    )


@require_GET
@require_app_access(APP_SLUG, consume=False)
def api_documento_ativo(request):
    documento = _get_documento_ativo()
    if not documento:
        return JsonResponse(
            {
                "ok": False,
                "error": "Nenhum documento ativo encontrado.",
            },
            status=404,
        )

    return JsonResponse(
        {
            "ok": True,
            "documento": {
                "id": documento.id,
                "slug": documento.slug,
                "titulo": documento.titulo,
                "total_paginas": documento.total_paginas,
                "idioma": documento.idioma,
                "arquivo_nome": documento.arquivo_pdf.name.rsplit("/", 1)[-1],
                "pdf_url": reverse("apostila_cnh:api_documento_ativo_pdf"),
            },
        }
    )


@require_http_methods(["GET", "HEAD"])
@require_app_access(APP_SLUG, consume=False)
def api_documento_ativo_pdf(request):
    documento = _get_documento_ativo()
    if not documento:
        return JsonResponse({"ok": False, "error": "Nenhum documento ativo encontrado."}, status=404)
    if not documento.arquivo_pdf:
        return JsonResponse({"ok": False, "error": "Documento ativo sem arquivo PDF."}, status=404)

    file_path = Path(documento.arquivo_pdf.path)
    if not file_path.exists():
        return JsonResponse({"ok": False, "error": "Arquivo PDF do documento ativo nao encontrado."}, status=404)

    file_size = file_path.stat().st_size
    filename = file_path.name
    range_header = request.headers.get("Range", "").strip()

    if range_header:
        return _build_partial_content_response(
            file_path=file_path,
            file_size=file_size,
            range_header=range_header,
            method=request.method,
            filename=filename,
        )

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(file_size),
        "Content-Disposition": f'inline; filename="{filename}"',
    }
    if request.method == "HEAD":
        return HttpResponse(status=200, content_type="application/pdf", headers=headers)

    response = FileResponse(file_path.open("rb"), content_type="application/pdf")
    for key, value in headers.items():
        response[key] = value
    return response


@require_http_methods(["GET", "POST"])
@require_app_access(APP_SLUG, consume=False)
def api_progresso(request):
    documento = _get_documento_ativo()
    if not documento:
        return JsonResponse({"ok": False, "error": "Nenhum documento ativo encontrado."}, status=404)

    total_paginas = documento.total_paginas or 0
    if request.method == "GET":
        progresso = (
            ApostilaProgressoLeitura.objects
            .filter(usuario=request.user, documento=documento)
            .only("ultima_pagina_lida")
            .first()
        )
        pagina = progresso.ultima_pagina_lida if progresso else 1
        if total_paginas > 0:
            pagina = min(max(pagina, 1), total_paginas)
        else:
            pagina = max(pagina, 1)

        return JsonResponse(
            {
                "ok": True,
                "progresso": {
                    "ultima_pagina_lida": pagina,
                    "total_paginas_documento": total_paginas,
                },
            }
        )

    payload = {}
    if request.content_type and "application/json" in request.content_type:
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except (TypeError, ValueError):
            return JsonResponse({"ok": False, "error": "JSON invalido."}, status=400)
    else:
        payload = request.POST

    pagina_raw = payload.get("pagina")
    if pagina_raw in (None, ""):
        return JsonResponse({"ok": False, "error": "Campo 'pagina' e obrigatorio."}, status=400)

    try:
        pagina = int(pagina_raw)
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "Campo 'pagina' deve ser inteiro."}, status=400)

    if pagina < 1:
        return JsonResponse({"ok": False, "error": "Campo 'pagina' deve ser >= 1."}, status=400)
    if total_paginas > 0 and pagina > total_paginas:
        return JsonResponse(
            {
                "ok": False,
                "error": f"Campo 'pagina' deve ser <= {total_paginas}.",
            },
            status=400,
        )

    progresso, _ = ApostilaProgressoLeitura.objects.update_or_create(
        usuario=request.user,
        documento=documento,
        defaults={"ultima_pagina_lida": pagina},
    )

    return JsonResponse(
        {
            "ok": True,
            "progresso": {
                "ultima_pagina_lida": progresso.ultima_pagina_lida,
                "total_paginas_documento": total_paginas,
            },
        },
    )


@require_GET
@require_app_access(APP_SLUG, consume=False)
def api_busca(request):
    documento = _get_documento_ativo()
    if not documento:
        return JsonResponse({"ok": False, "error": "Nenhum documento ativo encontrado."}, status=404)

    termo_raw = (request.GET.get("q") or "").strip()
    if not termo_raw:
        return JsonResponse({"ok": False, "error": "Parametro 'q' e obrigatorio."}, status=400)

    termo_normalizado = normalizar_texto_busca(termo_raw)
    if not termo_normalizado:
        return JsonResponse({"ok": False, "error": "Termo de busca invalido."}, status=400)

    paginas = list(
        ApostilaPagina.objects
        .filter(documento=documento, texto_normalizado__icontains=termo_normalizado)
        .order_by("numero_pagina")
        .only("numero_pagina", "texto", "texto_normalizado")[:30]
    )

    termo_lower = termo_raw.lower()
    resultados = []
    for pagina in paginas:
        texto = pagina.texto or ""
        texto_norm = pagina.texto_normalizado or ""
        base_snippet = texto

        idx = texto.lower().find(termo_lower)
        if idx >= 0:
            start = max(idx - 45, 0)
            end = min(idx + len(termo_raw) + 85, len(texto))
            base_snippet = texto[start:end]
        else:
            idx_norm = texto_norm.find(termo_normalizado)
            if idx_norm >= 0:
                start = max(idx_norm - 45, 0)
                end = min(idx_norm + len(termo_normalizado) + 85, len(texto_norm))
                base_snippet = texto_norm[start:end]
            else:
                base_snippet = (texto or texto_norm)[:130]

        trecho = re.sub(r"\s+", " ", base_snippet).strip()
        if len(trecho) > 160:
            trecho = trecho[:157].rstrip() + "..."

        resultados.append(
            {
                "pagina": pagina.numero_pagina,
                "trecho": trecho or "(sem trecho disponivel)",
            }
        )

    return JsonResponse(
        {
            "ok": True,
            "q": termo_raw,
            "total_resultados": len(resultados),
            "resultados": resultados,
        },
    )
