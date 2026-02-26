# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import uuid
from collections import defaultdict
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from banco_questoes.models import Questao


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


def _expected_image_name(questao: Questao) -> str:
    codigo = (questao.codigo_placa or "").strip().upper()
    imagem_raw = (questao.imagem_arquivo or "").strip()
    imagem_base = Path(imagem_raw).name if imagem_raw else ""
    if imagem_base:
        return imagem_base
    if codigo:
        return f"{codigo}.png"
    return ""


def _collect_case_pairs(placas_dir: Path) -> tuple[list[tuple[str, str]], list[str], dict[str, object]]:
    names = sorted([entry.name for entry in placas_dir.iterdir() if entry.is_file()])
    lower_to_names: dict[str, list[str]] = defaultdict(list)
    for name in names:
        lower_to_names[name.lower()].append(name)

    pairs_found: set[tuple[str, str]] = set()
    questoes = (
        Questao.objects.exclude(codigo_placa="")
        .select_related("modulo")
        .order_by("modulo__ordem", "numero_no_modulo", "id")
    )
    for questao in questoes.iterator():
        expected = _expected_image_name(questao)
        if not expected:
            continue

        candidates = lower_to_names.get(expected.lower(), [])
        if not candidates:
            continue
        if expected in candidates:
            continue

        found = _pick_candidate(candidates, expected)
        if not found:
            continue
        if found.lower() != expected.lower():
            # Diferenca nao e apenas caixa; nao altera automaticamente.
            continue
        pairs_found.add((found, expected))

    src_to_dst: dict[str, set[str]] = defaultdict(set)
    dst_to_src: dict[str, set[str]] = defaultdict(set)
    for src, dst in pairs_found:
        src_to_dst[src].add(dst)
        dst_to_src[dst].add(src)

    conflicts: list[str] = []
    conflict_sources = {src for src, dsts in src_to_dst.items() if len(dsts) > 1}
    conflict_targets = {dst for dst, srcs in dst_to_src.items() if len(srcs) > 1}

    for src in sorted(conflict_sources):
        conflicts.append(f"conflito: origem '{src}' mapeia para varios destinos {sorted(src_to_dst[src])}")
    for dst in sorted(conflict_targets):
        conflicts.append(f"conflito: destino '{dst}' recebe varias origens {sorted(dst_to_src[dst])}")

    actions = sorted(
        (src, dst)
        for src, dst in pairs_found
        if src not in conflict_sources and dst not in conflict_targets
    )

    meta = {
        "static_files_count": len(names),
        "pairs_detected": len(pairs_found),
        "actions_count": len(actions),
        "conflicts_count": len(conflicts),
    }
    return actions, conflicts, meta


def _apply_case_rename(
    placas_dir: Path,
    *,
    src_name: str,
    dst_name: str,
    dry_run: bool,
) -> tuple[bool, str]:
    src = placas_dir / src_name
    dst = placas_dir / dst_name

    if not src.exists():
        return False, f"origem nao encontrada: {src_name}"
    if src_name == dst_name:
        return True, "sem alteracao"
    if src_name.lower() != dst_name.lower():
        return False, "renomeio nao e apenas case; pulado"

    tmp = placas_dir / f"__tmp_casefix__{uuid.uuid4().hex}{src.suffix}"
    if dry_run:
        return True, f"dry-run: {src_name} -> {tmp.name} -> {dst_name}"

    try:
        src.rename(tmp)
        tmp.rename(dst)
    except OSError as exc:
        # Tenta reverter caso o segundo passo falhe.
        if tmp.exists() and not src.exists():
            try:
                tmp.rename(src)
            except OSError:
                pass
        return False, f"erro ao renomear '{src_name}' para '{dst_name}': {exc}"

    return True, f"renomeado: {src_name} -> {dst_name}"


class Command(BaseCommand):
    help = "Corrige divergencias de caixa alta/baixa dos arquivos em static/placas com base no banco."

    def add_arguments(self, parser):
        parser.add_argument("--out-dir", default="doc/reports")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--placas-dir",
            default="",
            help="Sobrescreve a pasta de placas. Padrao: <BASE_DIR>/static/placas",
        )
        parser.add_argument(
            "--write-report",
            action=argparse.BooleanOptionalAction,
            default=True,
            help="Gera doc/reports/placas_case_fix.json com resumo da execucao.",
        )

    def handle(self, *args, **options):
        placas_dir_opt = (options.get("placas_dir") or "").strip()
        out_dir = Path(options["out_dir"])
        dry_run = bool(options["dry_run"])
        write_report = bool(options["write_report"])

        placas_dir = Path(placas_dir_opt) if placas_dir_opt else (Path(settings.BASE_DIR) / "static" / "placas")
        if not placas_dir.exists():
            raise CommandError(f"Pasta nao encontrada: {placas_dir}")
        if not placas_dir.is_dir():
            raise CommandError(f"Caminho nao e diretorio: {placas_dir}")

        actions, conflicts, meta = _collect_case_pairs(placas_dir)

        successes: list[str] = []
        failures: list[str] = []
        for src, dst in actions:
            ok, msg = _apply_case_rename(
                placas_dir,
                src_name=src,
                dst_name=dst,
                dry_run=dry_run,
            )
            if ok:
                successes.append(msg)
            else:
                failures.append(msg)

        summary: dict[str, object] = {
            "placas_dir": str(placas_dir),
            "dry_run": dry_run,
            "pairs_detected": meta["pairs_detected"],
            "actions_attempted": len(actions),
            "actions_success": len(successes),
            "actions_failed": len(failures),
            "conflicts_count": len(conflicts),
            "conflicts": conflicts,
            "failures": failures,
            "successes": successes,
        }

        if write_report:
            out_dir.mkdir(parents=True, exist_ok=True)
            report_path = out_dir / "placas_case_fix.json"
            report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("Correcao de case concluida."))
        self.stdout.write(
            "Detectados: {pairs_detected} | Tentativas: {actions_attempted} | "
            "Sucesso: {actions_success} | Falhas: {actions_failed} | Conflitos: {conflicts_count}".format(
                **summary
            )
        )
        if write_report:
            self.stdout.write(f"Relatorio de correcao: {out_dir / 'placas_case_fix.json'}")
