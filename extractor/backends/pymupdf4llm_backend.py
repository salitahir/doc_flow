import fitz
import pymupdf4llm


def extract_markdown_pages(path: str):
    """
    Yield tuples: (page_no, markdown_string) for each page (1-based).
    """
    doc = fitz.open(path)
    try:
        for i in range(doc.page_count):
            # to_markdown on a single page
            md = pymupdf4llm.to_markdown(path, page_numbers=[i])
            yield (i + 1, md)
    finally:
        doc.close()
