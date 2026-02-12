from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from django.conf import settings


DEFAULT_CONFIG: dict[str, int] = {
    "tempo_min": 5,
    "tempo_max": 60,
    "tempo_default": 12,
    "qtd_default": 30,
}


def _to_int(value, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _normalize_config(raw: dict) -> dict[str, int]:
    tempo_min = max(_to_int(raw.get("tempo_min"), DEFAULT_CONFIG["tempo_min"]), 1)
    tempo_max = max(_to_int(raw.get("tempo_max"), DEFAULT_CONFIG["tempo_max"]), tempo_min)
    tempo_default = _to_int(raw.get("tempo_default"), DEFAULT_CONFIG["tempo_default"])
    qtd_default = max(_to_int(raw.get("qtd_default"), DEFAULT_CONFIG["qtd_default"]), 1)

    tempo_default = max(min(tempo_default, tempo_max), tempo_min)
    return {
        "tempo_min": tempo_min,
        "tempo_max": tempo_max,
        "tempo_default": tempo_default,
        "qtd_default": qtd_default,
    }


@lru_cache(maxsize=1)
def get_perguntas_respostas_config() -> dict[str, int]:
    cfg_path = Path(settings.BASE_DIR) / "config_perguntas_respostas.json"
    if not cfg_path.exists():
        return dict(DEFAULT_CONFIG)

    try:
        raw = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULT_CONFIG)

    if not isinstance(raw, dict):
        return dict(DEFAULT_CONFIG)
    return _normalize_config(raw)
