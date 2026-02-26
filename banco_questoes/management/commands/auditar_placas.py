# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from banco_questoes.models import Questao


STATUS_OK = "OK"
STATUS_MISSING = "MISSING_FILE"
STATUS_CASE_MISMATCH = "CASE_MISMATCH"
STATUS_INCONSISTENT = "INCONSISTENT_DATA"

VALID_FORMATS = {"csv", "json", "md"}

CSV_COLUMNS = [
    "questao_id",
    "modulo",
    "numero_no_modulo",
    "codigo_placa",
    "imagem_esperada",
    "imagem_cadastrada",
    "imagem_encontrada",
    "status",
    "observacao",
]


def _parse_formats(raw: str) -> list[str]:
    formats = []
    for part in (raw or "").split(","):
        item = part.strip().lower()
        if not item:
            continue
        if item not in VALID_FORMATS:
            raise CommandError(f"Formato invalido: {item}. Use: csv,json,md")
        if item not in formats:
            formats.append(item)
    if not formats:
        raise CommandError("Nenhum formato valido informado em --format.")
    return formats


def _pick_candidate(candidates: list[str], expected_name: str) -> str:
    if not candidates:
        return ""
    if expected_name in candidates:
        return expected_name

    expected_ext = Path(expected_name).suffix.lower()
    for item in sorted(candidates):
        if Path(item).suffix.lower() == expected_ext:
            return item
    return sorted(candidates)[0]


def _build_file_indexes(placas_dir: Path) -> dict[str, object]:
    names = sorted([entry.name for entry in placas_dir.iterdir() if entry.is_file()])

    lower_to_names: dict[str, list[str]] = defaultdict(list)
    stem_to_names: dict[str, list[str]] = defaultdict(list)
    stem_lower_to_names: dict[str, list[str]] = defaultdict(list)

    for name in names:
        lower_to_names[name.lower()].append(name)
        stem = Path(name).stem
        stem_to_names[stem].append(name)
        stem_lower_to_names[stem.lower()].append(name)

    return {
        "exact_names": set(names),
        "lower_to_names": lower_to_names,
        "stem_to_names": stem_to_names,
        "stem_lower_to_names": stem_lower_to_names,
        "names_count": len(names),
    }


def _resolve_match(
    *,
    expected_name: str,
    indexes: dict[str, object],
    strict_case: bool,
    strict_ext: bool,
) -> tuple[bool, bool, str]:
    if not expected_name:
        return False, False, ""

    exact_names: set[str] = indexes["exact_names"]  # type: ignore[assignment]
    lower_to_names: dict[str, list[str]] = indexes["lower_to_names"]  # type: ignore[assignment]
    stem_to_names: dict[str, list[str]] = indexes["stem_to_names"]  # type: ignore[assignment]
    stem_lower_to_names: dict[str, list[str]] = indexes["stem_lower_to_names"]  # type: ignore[assignment]

    if strict_ext:
        if strict_case:
            if expected_name in exact_names:
                return True, False, expected_name
            case_candidates = lower_to_names.get(expected_name.lower(), [])
            if case_candidates:
                return False, True, _pick_candidate(case_candidates, expected_name)
            return False, False, ""

        ci_candidates = lower_to_names.get(expected_name.lower(), [])
        if ci_candidates:
            return True, False, _pick_candidate(ci_candidates, expected_name)
        return False, False, ""

    expected_stem = Path(expected_name).stem
    if strict_case:
        exact_stem_candidates = stem_to_names.get(expected_stem, [])
        if exact_stem_candidates:
            return True, False, _pick_candidate(exact_stem_candidates, expected_name)

        ci_stem_candidates = stem_lower_to_names.get(expected_stem.lower(), [])
        if ci_stem_candidates:
            return False, True, _pick_candidate(ci_stem_candidates, expected_name)
        return False, False, ""

    ci_stem_candidates = stem_lower_to_names.get(expected_stem.lower(), [])
    if ci_stem_candidates:
        return True, False, _pick_candidate(ci_stem_candidates, expected_name)
    return False, False, ""


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def _write_md(path: Path, *, summary: dict[str, object], rows: list[dict[str, str]]) -> None:
    lines: list[str] = []
    lines.append("# Relatorio de auditoria de placas")
    lines.append("")
    lines.append(f"- Gerado em: {summary['generated_at']}")
    lines.append(f"- Pasta auditada: `{summary['placas_dir']}`")
    lines.append(f"- Regra de caixa: {'estrita' if summary['strict_case'] else 'nao estrita'}")
    lines.append(f"- Regra de extensao: {'estrita' if summary['strict_ext'] else 'flexivel por stem'}")
    lines.append("")
    lines.append("## Resumo")
    lines.append("")
    lines.append("| metrica | valor |")
    lines.append("|---|---:|")
    lines.append(f"| total_questoes_auditadas | {summary['total_auditadas']} |")
    lines.append(f"| total_ok | {summary['total_ok']} |")
    lines.append(f"| total_missing_file | {summary['total_missing_file']} |")
    lines.append(f"| total_case_mismatch | {summary['total_case_mismatch']} |")
    lines.append(f"| total_inconsistent_data | {summary['total_inconsistent_data']} |")
    lines.append(f"| total_problemas | {summary['total_problemas']} |")
    lines.append(f"| nomes_unicos_faltantes | {summary['missing_unique_count']} |")
    lines.append(f"| arquivos_lidos_em_static_placas | {summary['static_files_count']} |")
    lines.append("")

    missing_unique: list[str] = summary["missing_unique_names"]  # type: ignore[assignment]
    if missing_unique:
        lines.append("## Nomes faltantes unicos")
        lines.append("")
        for name in missing_unique:
            lines.append(f"- `{name}`")
        lines.append("")

    case_unique: list[str] = summary["case_mismatch_pairs"]  # type: ignore[assignment]
    if case_unique:
        lines.append("## Divergencias de caixa")
        lines.append("")
        for pair in case_unique:
            lines.append(f"- {pair}")
        lines.append("")

    lines.append("## Problemas por questao")
    lines.append("")
    if not rows:
        lines.append("Nenhum problema encontrado.")
    else:
        lines.append("| questao_id | modulo | numero | codigo_placa | imagem_esperada | imagem_cadastrada | imagem_encontrada | status | observacao |")
        lines.append("|---|---|---:|---|---|---|---|---|---|")
        for row in rows:
            lines.append(
                "| {questao_id} | {modulo} | {numero_no_modulo} | {codigo_placa} | {imagem_esperada} | {imagem_cadastrada} | {imagem_encontrada} | {status} | {observacao} |".format(
                    **row
                )
            )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class Command(BaseCommand):
    help = "Audita a consistencia entre Questao.codigo_placa/imagem_arquivo e arquivos em static/placas."

    def add_arguments(self, parser):
        parser.add_argument("--out-dir", default="doc/reports")
        parser.add_argument("--format", default="csv,json,md")
        parser.add_argument("--strict-ext", action="store_true")
        parser.add_argument(
            "--strict-case",
            action=argparse.BooleanOptionalAction,
            default=True,
            help="Exige igualdade exata de caixa alta/baixa no nome do arquivo (padrao: ligado).",
        )

    def handle(self, *args, **options):
        out_dir = Path(options["out_dir"])
        formats = _parse_formats(options["format"])
        strict_ext = bool(options["strict_ext"])
        strict_case = bool(options["strict_case"])

        placas_dir = Path(settings.BASE_DIR) / "static" / "placas"
        if not placas_dir.exists():
            raise CommandError(f"Pasta nao encontrada: {placas_dir}")
        if not placas_dir.is_dir():
            raise CommandError(f"Caminho nao e diretorio: {placas_dir}")

        indexes = _build_file_indexes(placas_dir)

        all_rows: list[dict[str, str]] = []
        problem_rows: list[dict[str, str]] = []

        questoes = (
            Questao.objects.exclude(codigo_placa="")
            .select_related("modulo")
            .order_by("modulo__ordem", "numero_no_modulo", "id")
        )

        for questao in questoes.iterator():
            codigo_raw = (questao.codigo_placa or "").strip()
            codigo_normalizado = codigo_raw.upper()
            imagem_cadastrada_raw = (questao.imagem_arquivo or "").strip()
            imagem_cadastrada = Path(imagem_cadastrada_raw).name if imagem_cadastrada_raw else ""

            if not codigo_normalizado:
                continue

            observacoes: list[str] = []
            if imagem_cadastrada_raw and imagem_cadastrada != imagem_cadastrada_raw:
                observacoes.append("imagem_arquivo contem caminho; validado apenas nome base")
            if not imagem_cadastrada:
                observacoes.append("imagem_arquivo vazio; fallback para codigo_placa + .png")

            imagem_esperada = imagem_cadastrada or f"{codigo_normalizado}.png"

            if imagem_cadastrada and Path(imagem_cadastrada).stem.upper() != codigo_normalizado:
                observacoes.append("imagem_arquivo nao corresponde ao codigo_placa")

            exists, case_mismatch, imagem_encontrada = _resolve_match(
                expected_name=imagem_esperada,
                indexes=indexes,
                strict_case=strict_case,
                strict_ext=strict_ext,
            )

            if exists:
                status = STATUS_INCONSISTENT if observacoes else STATUS_OK
            elif case_mismatch and strict_case:
                status = STATUS_CASE_MISMATCH
                observacoes.append("arquivo existe com mesmo nome sem diferenciar caixa")
            else:
                status = STATUS_MISSING
                observacoes.append("arquivo nao encontrado em static/placas")

            row = {
                "questao_id": str(questao.id),
                "modulo": questao.modulo.nome,
                "numero_no_modulo": str(questao.numero_no_modulo),
                "codigo_placa": codigo_normalizado,
                "imagem_esperada": imagem_esperada,
                "imagem_cadastrada": imagem_cadastrada,
                "imagem_encontrada": imagem_encontrada,
                "status": status,
                "observacao": "; ".join(observacoes),
            }
            all_rows.append(row)
            if status != STATUS_OK:
                problem_rows.append(row)

        counter = Counter(row["status"] for row in all_rows)
        missing_unique_names = sorted(
            {row["imagem_esperada"] for row in all_rows if row["status"] == STATUS_MISSING}
        )
        case_mismatch_pairs = sorted(
            {
                f"{row['imagem_esperada']} -> {row['imagem_encontrada']}"
                for row in all_rows
                if row["status"] == STATUS_CASE_MISMATCH and row["imagem_encontrada"]
            }
        )

        summary: dict[str, object] = {
            "generated_at": timezone.now().isoformat(),
            "placas_dir": str(placas_dir),
            "strict_case": strict_case,
            "strict_ext": strict_ext,
            "total_auditadas": len(all_rows),
            "total_ok": counter.get(STATUS_OK, 0),
            "total_missing_file": counter.get(STATUS_MISSING, 0),
            "total_case_mismatch": counter.get(STATUS_CASE_MISMATCH, 0),
            "total_inconsistent_data": counter.get(STATUS_INCONSISTENT, 0),
            "total_problemas": len(problem_rows),
            "missing_unique_count": len(missing_unique_names),
            "missing_unique_names": missing_unique_names,
            "case_mismatch_pairs": case_mismatch_pairs,
            "static_files_count": indexes["names_count"],
        }

        out_dir.mkdir(parents=True, exist_ok=True)

        if "csv" in formats:
            _write_csv(out_dir / "placas_faltantes.csv", problem_rows)
        if "json" in formats:
            _write_json(
                out_dir / "placas_faltantes.json",
                {
                    "summary": summary,
                    "rows": problem_rows,
                },
            )
        if "md" in formats:
            _write_md(out_dir / "placas_faltantes.md", summary=summary, rows=problem_rows)

        self.stdout.write(self.style.SUCCESS("Auditoria de placas concluida."))
        self.stdout.write(
            "Auditadas: {total_auditadas} | OK: {total_ok} | Missing: {total_missing_file} | "
            "Case mismatch: {total_case_mismatch} | Inconsistent: {total_inconsistent_data}".format(
                **summary
            )
        )
        self.stdout.write(f"Relatorios em: {out_dir}")
