from __future__ import annotations
from dataclasses import dataclass, field
import re

# =========================
# REGEX BASEADAS NO PDF REAL
# =========================

# Exemplo real:
# G (Fácil) 1. Ao ver a placa...
QUESTION_START_RE = re.compile(
    r"^[A-Z]\s*\((Fácil|Intermediário|Difícil)\)\s*(\d+)\.\s*(.*)$",
    re.IGNORECASE,
)

PLATE_RE = re.compile(r"^Código da placa:\s*([A-Z0-9\-]+)\s*$", re.IGNORECASE)

CORRECT_RE = re.compile(r"^Alternativa correta:\s*(.*)$", re.IGNORECASE)
COMMENT_RE = re.compile(r"^Comentário:\s*(.*)$", re.IGNORECASE)
WRONG_HEADER_RE = re.compile(r"^Respostas incorretas:\s*$", re.IGNORECASE)

# Marcadores reais do PDF
CORRECT_MARKERS_RE = re.compile(r"[✓‼\x13]\s*$")
WRONG_ITEM_RE = re.compile(r"^[↨✗xX\x17]\s*(.*)$")

# =========================
# DTO
# =========================

@dataclass
class ParsedQuestion:
    page_start: int
    page_end: int

    numero_no_modulo: int
    dificuldade_raw: str

    enunciado: str = ""
    codigo_placa: str = ""
    alternativa_correta: str = ""
    comentario: str = ""
    incorretas: list[str] = field(default_factory=list)

    raw_block: str = ""


# =========================
# NORMALIZAÇÕES
# =========================

def normalize_difficulty(diff: str) -> str:
    d = diff.lower()
    if "fácil" in d or "facil" in d:
        return "FACIL"
    if "inter" in d:
        return "INTERMEDIARIO"
    return "DIFICIL"


def strip_correct_markers(text: str) -> str:
    return CORRECT_MARKERS_RE.sub("", text).strip()


# =========================
# PARSER (máquina de estados)
# =========================

def parse_questions_across_pages(
    pages_lines: list[tuple[int, list[str]]]
) -> list[ParsedQuestion]:

    questions: list[ParsedQuestion] = []
    current: ParsedQuestion | None = None

    state = "WAIT_START"  # WAIT_START | IN_STATEMENT | IN_CORRECT | IN_COMMENT | IN_WRONGS

    def flush():
        nonlocal current
        if current:
            current.raw_block = current.raw_block.strip()
            questions.append(current)
            current = None

    for page_number, lines in pages_lines:
        for ln in lines:
            # =========================
            # INÍCIO DE QUESTÃO
            # =========================
            m = QUESTION_START_RE.match(ln)
            if m:
                flush()

                dificuldade, numero, resto = m.groups()
                current = ParsedQuestion(
                    page_start=page_number,
                    page_end=page_number,
                    numero_no_modulo=int(numero),
                    dificuldade_raw=dificuldade,
                    enunciado=resto.strip(),
                    raw_block=ln + "\n",
                )
                state = "IN_STATEMENT"
                continue

            if current is None:
                continue

            # Atualiza página final
            current.page_end = page_number
            current.raw_block += ln + "\n"

            # =========================
            # CAMPOS DETECTÁVEIS
            # =========================
            pm = PLATE_RE.match(ln)
            if pm:
                current.codigo_placa = pm.group(1).upper()
                continue

            cm = CORRECT_RE.match(ln)
            if cm:
                state = "IN_CORRECT"
                current.alternativa_correta = strip_correct_markers(cm.group(1))
                continue

            com = COMMENT_RE.match(ln)
            if com:
                state = "IN_COMMENT"
                current.comentario = com.group(1).strip()
                continue

            if WRONG_HEADER_RE.match(ln):
                state = "IN_WRONGS"
                continue

            wm = WRONG_ITEM_RE.match(ln)
            if wm and state == "IN_WRONGS":
                current.incorretas.append(wm.group(1).strip())
                continue

            # =========================
            # CONTINUIDADES MULTI-LINHA
            # =========================
            if state == "IN_STATEMENT":
                current.enunciado += " " + ln

            elif state == "IN_CORRECT":
                current.alternativa_correta += " " + strip_correct_markers(ln)

            elif state == "IN_COMMENT":
                current.comentario += " " + ln

            elif state == "IN_WRONGS":
                if current.incorretas:
                    current.incorretas[-1] += " " + ln

    flush()
    return questions
