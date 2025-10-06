import fitz  # PyMuPDF
from typing import Iterator, Tuple

def extract_markdown_pages(path: str) -> Iterator[Tuple[int, str]]:
    """
    Yield (page_no, markdown_text) for each page (1-based) using PyMuPDF directly.
    Any per-page failure is caught and returned as empty text so the pipeline continues.
    """
    doc = fitz.open(path)
    try:
        n = doc.page_count
        if n == 0:
            raise RuntimeError("No pages found in PDF.")
        for i in range(n):
            md = ""
            try:
                page = doc.load_page(i)
                # 'markdown' is supported by PyMuPDF 1.23+. Falls back to text if needed.
                try:
                    md = page.get_text("markdown") or ""
                except Exception:
                    md = page.get_text() or ""
            except Exception:
                md = ""  # keep going
            yield (i + 1, md)
    finally:
        doc.close()
