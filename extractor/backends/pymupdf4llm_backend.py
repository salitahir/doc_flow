import fitz  # PyMuPDF

def extract_markdown_pages(path: str):
    """
    Yield (page_no, markdown_text) for each page (1-based) using PyMuPDF directly.
    This is more reliable than page-chunking via pymupdf4llm for some PDFs.
    """
    doc = fitz.open(path)
    try:
        for i in range(doc.page_count):
            page = doc.load_page(i)
            md = page.get_text("markdown") or ""
            yield (i + 1, md)
    finally:
        doc.close()
