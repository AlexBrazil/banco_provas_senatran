from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

import fitz  # PyMuPDF
from django.db import transaction

from apostila_cnh.models import ApostilaDocumento, ApostilaPagina


def normalizar_texto_busca(texto: str) -> str:
    texto = (texto or "").strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", texto).strip()


@dataclass
class ResultadoIngestao:
    total_paginas: int
    paginas_criadas: int
    paginas_atualizadas: int
    paginas_removidas: int
    paginas_sem_texto: int


@transaction.atomic
def ingerir_documento_pdf(documento: ApostilaDocumento) -> ResultadoIngestao:
    if not documento.arquivo_pdf:
        raise ValueError("Documento sem arquivo PDF associado.")

    pdf_path = documento.arquivo_pdf.path
    paginas_processadas: list[int] = []
    paginas_criadas = 0
    paginas_atualizadas = 0
    paginas_sem_texto = 0

    with fitz.open(pdf_path) as pdf:
        total_paginas = pdf.page_count
        for idx in range(total_paginas):
            numero_pagina = idx + 1
            texto = (pdf.load_page(idx).get_text("text") or "").strip()
            texto_normalizado = normalizar_texto_busca(texto)
            if not texto:
                paginas_sem_texto += 1

            _, created = ApostilaPagina.objects.update_or_create(
                documento=documento,
                numero_pagina=numero_pagina,
                defaults={
                    "texto": texto,
                    "texto_normalizado": texto_normalizado,
                },
            )
            paginas_processadas.append(numero_pagina)
            if created:
                paginas_criadas += 1
            else:
                paginas_atualizadas += 1

    paginas_removidas, _ = (
        ApostilaPagina.objects.filter(documento=documento)
        .exclude(numero_pagina__in=paginas_processadas)
        .delete()
    )

    if documento.total_paginas != total_paginas:
        documento.total_paginas = total_paginas
        documento.save(update_fields=["total_paginas", "atualizado_em"])

    return ResultadoIngestao(
        total_paginas=total_paginas,
        paginas_criadas=paginas_criadas,
        paginas_atualizadas=paginas_atualizadas,
        paginas_removidas=paginas_removidas,
        paginas_sem_texto=paginas_sem_texto,
    )
