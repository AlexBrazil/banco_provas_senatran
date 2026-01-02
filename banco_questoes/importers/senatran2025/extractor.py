from __future__ import annotations
from dataclasses import dataclass
import fitz  # PyMuPDF


@dataclass
class PageText:
    page_number: int  # 1-based
    text: str


def extract_pages(pdf_path: str) -> list[PageText]:
    doc = fitz.open(pdf_path)
    pages: list[PageText] = []
    for i in range(doc.page_count):
        page = doc.load_page(i)
        text = page.get_text("text") or ""
        pages.append(PageText(page_number=i + 1, text=text))
    doc.close()
    return pages
