from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from typing import Any

from django.contrib import messages
from django.db import transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from banco_questoes.access_control import require_app_access
from banco_questoes.models import Alternativa, Curso, CursoModulo, Questao
from .app_config import get_perguntas_respostas_config
from .models import PerguntaRespostaEstudo, PerguntaRespostaPreferenciaUsuario

SESSION_KEY = "perguntas_respostas_sessoes_v1"


@dataclass
class EstudoContexto:
    curso_id: str
    modulo_id: str
    dificuldade: str
    com_imagem: bool
    com_placa: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "curso_id": self.curso_id,
            "modulo_id": self.modulo_id,
            "dificuldade": self.dificuldade,
            "com_imagem": self.com_imagem,
            "com_placa": self.com_placa,
        }


def _to_positive_int(raw: str, fallback: int) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return fallback
    return value if value > 0 else fallback


def _to_non_negative_int(raw: str, fallback: int = 0) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return fallback
    return value if value >= 0 else fallback


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(min(value, maximum), minimum)


def _parse_bool_flag(raw: str | None, fallback: bool) -> bool:
    if raw is None:
        return fallback
    value = raw.strip()
    if value == "1":
        return True
    if value == "0":
        return False
    return fallback


def _parse_context_from_post(request: HttpRequest) -> EstudoContexto:
    return EstudoContexto(
        curso_id=(request.POST.get("curso_id") or "").strip(),
        modulo_id=(request.POST.get("modulo_id") or "").strip(),
        dificuldade=(request.POST.get("dificuldade") or "").strip(),
        com_imagem=request.POST.get("com_imagem") == "1",
        com_placa=request.POST.get("com_placa") == "1",
    )


def _context_hash(contexto: EstudoContexto) -> str:
    raw = json.dumps(contexto.as_dict(), ensure_ascii=True, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _base_questoes_queryset(contexto: EstudoContexto):
    qs = Questao.objects.select_related("curso", "modulo")

    if contexto.curso_id:
        qs = qs.filter(curso_id=contexto.curso_id)
    if contexto.modulo_id:
        qs = qs.filter(modulo_id=contexto.modulo_id)
    if contexto.dificuldade:
        qs = qs.filter(dificuldade=contexto.dificuldade)
    if contexto.com_imagem:
        qs = qs.exclude(imagem_arquivo="")
    if contexto.com_placa:
        qs = qs.exclude(codigo_placa="")

    return qs.order_by("curso__nome", "modulo__ordem", "numero_no_modulo", "id")


def _select_questoes_for_estudo(user, contexto: EstudoContexto, qtd: int) -> list[uuid.UUID]:
    questoes_ids = list(_base_questoes_queryset(contexto).values_list("id", flat=True))
    if not questoes_ids:
        return []

    contexto_hash = _context_hash(contexto)
    historicos = list(
        PerguntaRespostaEstudo.objects.filter(
            usuario=user,
            contexto_hash=contexto_hash,
            questao_id__in=questoes_ids,
        ).values("questao_id", "ultimo_estudo_em")
    )
    historico_map = {item["questao_id"]: item["ultimo_estudo_em"] for item in historicos}

    ineditas = [qid for qid in questoes_ids if qid not in historico_map]
    selecionadas: list[uuid.UUID] = ineditas[:qtd]
    faltantes = qtd - len(selecionadas)
    if faltantes <= 0:
        return selecionadas

    revisao_lru = sorted(
        [qid for qid in questoes_ids if qid in historico_map],
        key=lambda qid: historico_map[qid],
    )
    if not revisao_lru:
        return selecionadas

    bloco_repeticao: list[uuid.UUID] = []
    while len(bloco_repeticao) < faltantes:
        bloco_repeticao.extend(revisao_lru)
    selecionadas.extend(bloco_repeticao[:faltantes])
    return selecionadas


def _get_preferencia_usuario(user) -> PerguntaRespostaPreferenciaUsuario | None:
    return (
        PerguntaRespostaPreferenciaUsuario.objects
        .filter(usuario=user)
        .first()
    )


def _tempo_usuario_atual(user, cfg: dict[str, int]) -> int:
    pref = _get_preferencia_usuario(user)
    if not pref:
        return cfg["tempo_default"]
    return _clamp(pref.tempo_entre_questoes_segundos, cfg["tempo_min"], cfg["tempo_max"])


def _build_index_context(request: HttpRequest, form_values: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = get_perguntas_respostas_config()
    cursos = Curso.objects.filter(ativo=True).order_by("nome")
    modulos = CursoModulo.objects.select_related("curso").filter(ativo=True).order_by("curso__nome", "ordem")
    form_values = form_values or {}

    return {
        "app_title": "Perguntas e Respostas para Estudos",
        "cfg": cfg,
        "tempo_usuario": _tempo_usuario_atual(request.user, cfg),
        "cursos": cursos,
        "modulos": modulos,
        "dificuldades": Questao.Dificuldade.choices,
        "form_values": form_values,
    }


def _get_bucket(request: HttpRequest) -> dict[str, Any]:
    bucket = request.session.get(SESSION_KEY)
    if isinstance(bucket, dict):
        return bucket
    return {}


def _save_bucket(request: HttpRequest, bucket: dict[str, Any]) -> None:
    request.session[SESSION_KEY] = bucket
    request.session.modified = True


def _save_estudo_sessao(
    request: HttpRequest,
    questoes_ids: list[uuid.UUID],
    contexto: EstudoContexto,
    qtd: int,
    auto_mode: bool,
    voice_enabled: bool,
) -> str:
    sessao_id = uuid.uuid4().hex
    bucket = _get_bucket(request)
    bucket[sessao_id] = {
        "created_at": timezone.now().isoformat(),
        "qtd": qtd,
        "contexto": contexto.as_dict(),
        "contexto_hash": _context_hash(contexto),
        "questoes_ids": [str(item) for item in questoes_ids],
        "default_auto_mode": bool(auto_mode),
        "default_voice_enabled": bool(voice_enabled),
    }
    _save_bucket(request, bucket)
    return sessao_id


def _get_estudo_sessao(request: HttpRequest, sessao_id: str) -> dict[str, Any] | None:
    return _get_bucket(request).get(sessao_id)


def _load_questao_with_resposta_correta(questao_id: str) -> tuple[Questao | None, Alternativa | None]:
    questao = (
        Questao.objects.select_related("curso", "modulo")
        .filter(id=questao_id)
        .first()
    )
    if not questao:
        return None, None

    correta = (
        Alternativa.objects
        .filter(questao=questao, is_correta=True)
        .order_by("ordem")
        .first()
    )
    return questao, correta


def _build_voice_intro(questao: Questao) -> str:
    if questao.codigo_placa:
        return "Esta questao contem uma placa. Olhe a placa em tela."
    if questao.imagem_arquivo:
        return "Esta questao contem uma imagem. Olhe a imagem em tela."
    return ""


def _register_estudo(user, questao: Questao, contexto_hash: str, contexto_json: dict[str, Any]) -> None:
    now = timezone.now()
    with transaction.atomic():
        registro, created = PerguntaRespostaEstudo.objects.select_for_update().get_or_create(
            usuario=user,
            questao=questao,
            contexto_hash=contexto_hash,
            defaults={
                "contexto_json": contexto_json,
                "primeiro_estudo_em": now,
                "ultimo_estudo_em": now,
                "vezes_estudada": 1,
            },
        )
        if created:
            return
        registro.contexto_json = contexto_json
        registro.ultimo_estudo_em = now
        registro.vezes_estudada += 1
        registro.save(update_fields=["contexto_json", "ultimo_estudo_em", "vezes_estudada", "atualizado_em"])


@require_GET
@require_app_access("perguntas-respostas")
def index(request: HttpRequest) -> HttpResponse:
    return render(request, "perguntas_respostas/index.html", _build_index_context(request))


@require_POST
@require_app_access("perguntas-respostas")
def iniciar_estudo(request: HttpRequest) -> HttpResponse:
    cfg = get_perguntas_respostas_config()
    qtd = _to_positive_int(request.POST.get("qtd_questoes"), cfg["qtd_default"])
    qtd = _clamp(qtd, 1, 500)

    contexto = _parse_context_from_post(request)
    auto_mode = request.POST.get("study_mode") == "auto"
    voice_enabled = request.POST.get("voice_enabled") == "1"

    questoes_ids = _select_questoes_for_estudo(request.user, contexto, qtd)
    if not questoes_ids:
        messages.error(request, "Nenhuma questao encontrada para os filtros selecionados.")
        form_values = {
            **contexto.as_dict(),
            "qtd_questoes": qtd,
            "study_mode": "auto" if auto_mode else "manual",
            "voice_enabled": voice_enabled,
        }
        return render(request, "perguntas_respostas/index.html", _build_index_context(request, form_values))

    sessao_id = _save_estudo_sessao(
        request=request,
        questoes_ids=questoes_ids,
        contexto=contexto,
        qtd=qtd,
        auto_mode=auto_mode,
        voice_enabled=voice_enabled,
    )
    return redirect(f"{reverse('perguntas_respostas:estudar', args=[sessao_id])}?pos=0")


@require_GET
@require_app_access("perguntas-respostas")
def estudar(request: HttpRequest, sessao_id: str) -> HttpResponse:
    sessao = _get_estudo_sessao(request, sessao_id)
    if not sessao:
        messages.error(request, "Sessao de estudo nao encontrada. Inicie novamente.")
        return redirect("perguntas_respostas:index")

    questoes_ids = sessao.get("questoes_ids") or []
    if not questoes_ids:
        messages.error(request, "A sessao nao possui questoes.")
        return redirect("perguntas_respostas:index")

    pos = _to_non_negative_int(request.GET.get("pos"), 0)
    if pos < 0:
        pos = 0
    if pos >= len(questoes_ids):
        pos = len(questoes_ids) - 1

    questao_id = questoes_ids[pos]
    questao, correta = _load_questao_with_resposta_correta(questao_id)
    if not questao:
        messages.error(request, "Questao nao encontrada para esta sessao.")
        return redirect("perguntas_respostas:index")

    contexto_json = sessao.get("contexto") or {}
    contexto_hash = (sessao.get("contexto_hash") or "").strip()
    if contexto_hash:
        _register_estudo(request.user, questao, contexto_hash, contexto_json)

    cfg = get_perguntas_respostas_config()
    tempo_from_query = request.GET.get("tempo")
    tempo_atual = _tempo_usuario_atual(request.user, cfg)
    if tempo_from_query is not None:
        tempo_atual = _clamp(_to_positive_int(tempo_from_query, tempo_atual), cfg["tempo_min"], cfg["tempo_max"])

    default_auto_mode = _parse_bool_flag(
        request.GET.get("auto"),
        bool(sessao.get("default_auto_mode", False)),
    )
    default_voice_enabled = _parse_bool_flag(
        request.GET.get("voice"),
        bool(sessao.get("default_voice_enabled", False)),
    )

    next_pos = pos + 1
    prev_pos = pos - 1

    def _build_step_url(target_pos: int) -> str:
        base_url = reverse("perguntas_respostas:estudar", args=[sessao_id])
        return (
            f"{base_url}?pos={target_pos}"
            f"&auto={'1' if default_auto_mode else '0'}"
            f"&voice={'1' if default_voice_enabled else '0'}"
            f"&tempo={tempo_atual}"
        )

    voice_payload = {
        "intro": _build_voice_intro(questao),
        "enunciado": questao.enunciado.strip(),
        "resposta": (correta.texto.strip() if correta else ""),
        "comentario": (questao.comentario or "").strip(),
    }

    context = {
        "app_title": "Perguntas e Respostas para Estudos",
        "sessao_id": sessao_id,
        "questao": questao,
        "resposta_correta": correta,
        "total": len(questoes_ids),
        "posicao": pos,
        "tem_anterior": pos > 0,
        "tem_proxima": pos < len(questoes_ids) - 1,
        "anterior_url": _build_step_url(prev_pos),
        "proxima_url": _build_step_url(next_pos),
        "cfg": cfg,
        "tempo_atual": tempo_atual,
        "default_auto_mode": default_auto_mode,
        "default_voice_enabled": default_voice_enabled,
        "voice_payload": voice_payload,
        "salvar_tempo_url": reverse("perguntas_respostas:salvar_tempo"),
    }
    return render(request, "perguntas_respostas/estudo.html", context)


@require_POST
@require_app_access("perguntas-respostas")
def salvar_tempo_preferencia(request: HttpRequest) -> JsonResponse:
    cfg = get_perguntas_respostas_config()
    tempo = _to_positive_int(request.POST.get("tempo"), cfg["tempo_default"])
    tempo = _clamp(tempo, cfg["tempo_min"], cfg["tempo_max"])
    modo_automatico = request.POST.get("modo_automatico") == "1"

    pref, _ = PerguntaRespostaPreferenciaUsuario.objects.get_or_create(
        usuario=request.user,
        defaults={
            "tempo_entre_questoes_segundos": tempo,
            "modo_automatico_ativo": modo_automatico,
        },
    )
    if pref.tempo_entre_questoes_segundos != tempo or pref.modo_automatico_ativo != modo_automatico:
        pref.tempo_entre_questoes_segundos = tempo
        pref.modo_automatico_ativo = modo_automatico
        pref.save(update_fields=["tempo_entre_questoes_segundos", "modo_automatico_ativo", "atualizado_em"])

    return JsonResponse({"ok": True, "tempo": tempo})
