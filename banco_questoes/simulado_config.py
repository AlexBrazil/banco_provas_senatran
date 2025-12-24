from __future__ import annotations

import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

from django.conf import settings


DEFAULT_CONFIG: Dict[str, Any] = {
    "version": "1.0",
    "defaults": {
        "curso": {"nome": "Primeira Habilitação"},
        "modo": "PROVA",
        "dificuldade": "",
        "com_imagem": False,
        "so_placas": False,
        "qtd": 10,
    },
    "inicio_rapido": {
        "habilitado": True,
        "label": "Início rápido",
        "hint": "Primeira Habilitação · Modo Prova · Misturado · 10 questões",
        "tooltip": "Curso padrão não encontrado",
        "override_filtros": {},
    },
    "ui": {
        "messages": {
            "selecione_curso": "Selecione um curso para ver as estatísticas.",
            "carregando_stats": "Carregando estatísticas...",
            "pronto": "Pronto para iniciar.",
            "sem_questoes": "Não há questões para os filtros selecionados.",
            "erro_generico": "Falha ao carregar dados.",
        }
    },
    "limits": {
        "qtd_min": 1,
        "qtd_max": 50,
        "modes": ["PROVA", "ESTUDO"],
    },
}

CONFIG_FILENAME = "config_simulado.json"


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


@lru_cache(maxsize=1)
def get_simulado_config() -> Dict[str, Any]:
    """
    Carrega o JSON de config do simulado, mesclando com defaults.
    Cache simples em memória; reiniciar o processo recarrega o arquivo.
    """
    cfg = deepcopy(DEFAULT_CONFIG)
    path = Path(getattr(settings, "SIMULADO_CONFIG_PATH", settings.BASE_DIR / CONFIG_FILENAME))

    try:
        with path.open("r", encoding="utf-8") as fh:
            loaded = json.load(fh)
        if isinstance(loaded, dict):
            cfg = _deep_merge(cfg, loaded)
    except FileNotFoundError:
        # Usa apenas os defaults
        pass
    except Exception:
        # Em caso de erro de parsing, também retorna defaults
        pass

    return cfg


def clear_simulado_config_cache() -> None:
    get_simulado_config.cache_clear()
