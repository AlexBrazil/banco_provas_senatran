from __future__ import annotations
import re

FOOTER_PATTERNS = [
    r"CNH do Brasil\s*-\s*Ministério dos Transportes\s*-\s*Secretaria Nacional de Trânsito",
]

def clean_text(raw: str) -> str:
    text = raw.replace("\r\n", "\n").replace("\r", "\n")

    # remove rodapés repetidos
    for pat in FOOTER_PATTERNS:
        text = re.sub(pat, "", text, flags=re.IGNORECASE)

    # remove múltiplas linhas vazias
    text = re.sub(r"\n{3,}", "\n\n", text)

    # strip geral
    return text.strip()


def split_lines(text: str) -> list[str]:
    lines = [ln.strip() for ln in text.split("\n")]
    # remove linhas vazias "soltas"
    return [ln for ln in lines if ln]
