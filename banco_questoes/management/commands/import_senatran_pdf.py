# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Count

from banco_questoes.models import (
    Curso,
    CursoModulo,
    Documento,
    Questao,
    Alternativa,
)

from banco_questoes.importers.senatran2025.extractor import extract_pages
from banco_questoes.importers.senatran2025.normalizer import clean_text, split_lines
from banco_questoes.importers.senatran2025.parser import (
    parse_questions_across_pages,
    normalize_difficulty,
)

# ============================================================
# Helpers
# ============================================================

def parse_page_range(s: str) -> tuple[int, int]:
    s = (s or "").strip()
    if not s:
        raise ValueError("Faixa de páginas vazia.")
    if "-" not in s:
        n = int(s)
        return n, n
    a, b = s.split("-", 1)
    return int(a.strip()), int(b.strip())


def make_import_hash(modulo_id: str, numero_no_modulo: int, enunciado: str, correta: str) -> str:
    base = f"{modulo_id}|{numero_no_modulo}|{enunciado.strip()}|{correta.strip()}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


@transaction.atomic
def upsert_question_by_natural_key(
    *,
    curso: Curso,
    modulo: CursoModulo,
    documento: Documento,
    numero_no_modulo: int,
    dificuldade_code: Optional[str],
    enunciado: str,
    comentario: str,
    codigo_placa: str,
    imagem_arquivo: str,
    pagina_inicio: int,
    pagina_fim: int,
    raw_block: str,
    correta: str,
    incorretas: list[str],
):
    import_hash = make_import_hash(str(modulo.id), numero_no_modulo, enunciado, correta)

    questao, created = Questao.objects.update_or_create(
        documento=documento,
        modulo=modulo,
        numero_no_modulo=numero_no_modulo,
        defaults={
            "curso": curso,
            "dificuldade": dificuldade_code,
            "enunciado": enunciado,
            "comentario": comentario,
            "codigo_placa": codigo_placa,
            "imagem_arquivo": imagem_arquivo,
            "pagina_inicio": pagina_inicio,
            "pagina_fim": pagina_fim,
            "raw_block": raw_block,
            "import_hash": import_hash,
        },
    )

    Alternativa.objects.filter(questao=questao).delete()

    Alternativa.objects.create(
        questao=questao,
        ordem=1,
        texto=correta,
        is_correta=True,
    )

    ordem = 2
    for txt in incorretas:
        Alternativa.objects.create(
            questao=questao,
            ordem=ordem,
            texto=txt,
            is_correta=False,
        )
        ordem += 1

    return questao, created


# ============================================================
# Stats
# ============================================================

@dataclass
class ImportStats:
    pages_processed: int = 0
    questions_parsed: int = 0
    created: int = 0
    updated: int = 0
    errors: int = 0


# ============================================================
# Command
# ============================================================

class Command(BaseCommand):
    help = "Importa o PDF SENATRAN (Banco Nacional de Questões) para o banco."

    def add_arguments(self, parser):
        parser.add_argument("pdf_path", type=str)
        parser.add_argument("--curso", required=True)
        parser.add_argument("--documento", required=True)
        parser.add_argument("--ano", type=int)
        parser.add_argument("--pages", type=str)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--strict-modulo", action="store_true")
        parser.add_argument("--max-errors", type=int, default=20)

    def handle(self, *args, **options):
        pdf_path = options["pdf_path"]
        curso_nome = options["curso"]
        documento_titulo = options["documento"]
        ano = options.get("ano")
        pages_opt = options.get("pages")
        dry_run = options.get("dry_run", False)
        strict_modulo = options.get("strict_modulo", False)
        max_errors = options.get("max_errors", 20)

        # Curso
        try:
            curso = Curso.objects.get(nome=curso_nome, ativo=True)
        except Curso.DoesNotExist:
            raise CommandError(f'Curso não encontrado: "{curso_nome}"')

        # Documento
        documento, _ = Documento.objects.get_or_create(
            titulo=documento_titulo,
            defaults={"ano": ano},
        )
        if ano and documento.ano != ano:
            documento.ano = ano
            documento.save(update_fields=["ano"])

        # Módulos
        modulos = list(
            CursoModulo.objects.filter(curso=curso, ativo=True).order_by("ordem")
        )

        def resolve_modulo(page: int) -> Optional[CursoModulo]:
            for m in modulos:
                if m.pagina_inicio and m.pagina_fim and m.pagina_inicio <= page <= m.pagina_fim:
                    return m
            return None

        pages = extract_pages(pdf_path)

        if pages_opt:
            p1, p2 = parse_page_range(pages_opt)
            pages = [p for p in pages if p1 <= p.page_number <= p2]

        pages_lines = []
        for p in pages:
            lines = split_lines(clean_text(p.text))
            pages_lines.append((p.page_number, lines))

        stats = ImportStats(pages_processed=len(pages_lines))

        parsed_questions = parse_questions_across_pages(pages_lines)
        stats.questions_parsed = len(parsed_questions)

        errors = []
        by_modulo = {}

        ctx = transaction.atomic() if not dry_run else _nullcontext()

        with ctx:
            for pq in parsed_questions:
                modulo = resolve_modulo(pq.page_start)

                if not modulo:
                    msg = f"Página {pq.page_start} fora de qualquer módulo"
                    if strict_modulo:
                        raise CommandError(msg)
                    errors.append(msg)
                    stats.errors += 1
                    continue

                by_modulo[modulo.nome] = by_modulo.get(modulo.nome, 0) + 1

                if dry_run:
                    continue

                dificuldade = normalize_difficulty(pq.dificuldade_raw)
                codigo_placa = (pq.codigo_placa or "").upper()
                imagem = f"{codigo_placa}.png" if codigo_placa else ""

                _, created = upsert_question_by_natural_key(
                    curso=curso,
                    modulo=modulo,
                    documento=documento,
                    numero_no_modulo=pq.numero_no_modulo,
                    dificuldade_code=dificuldade,
                    enunciado=pq.enunciado.strip(),
                    comentario=(pq.comentario or "").strip(),
                    codigo_placa=codigo_placa,
                    imagem_arquivo=imagem,
                    pagina_inicio=pq.page_start,
                    pagina_fim=pq.page_end,
                    raw_block=pq.raw_block,
                    correta=pq.alternativa_correta.strip(),
                    incorretas=[i.strip() for i in pq.incorretas],
                )

                stats.created += int(created)
                stats.updated += int(not created)

        # Relatório
        self.stdout.write(self.style.SUCCESS("IMPORTAÇÃO FINALIZADA"))
        self.stdout.write(f"Páginas: {stats.pages_processed}")
        self.stdout.write(f"Questões: {stats.questions_parsed}")
        self.stdout.write(f"Dry-run: {'SIM' if dry_run else 'NÃO'}")
        self.stdout.write(f"Erros: {stats.errors}")

        for nome, qtd in by_modulo.items():
            self.stdout.write(f"- {nome}: {qtd}")


class _nullcontext:
    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, tb):
        return False
