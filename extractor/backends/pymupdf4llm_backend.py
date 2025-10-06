import fitz
import pymupdf4llm

def extract_markdown_pages(path: str):
    """
    Yield (page_no, markdown_text) for each page (1-based).
    Uses page_chunks=True so we don't process the whole doc as one string.
    """
    data = pymupdf4llm.to_markdown(path, page_chunks=True)
    # data is a list; each item is a dict for a page
    # common keys include "text" (markdown) and some metadata
    for idx, page in enumerate(data, start=1):
        md = page.get("text", "") or ""
        yield (idx, md)
