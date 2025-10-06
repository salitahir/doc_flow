"""
Docling backend: convert input PDF to Markdown.

Rationale:
- For Step 1, we keep things simple and stable: export to Markdown
  (Docling handles reading order, multi-columns, many tables).
- We then parse Markdown in a separate stage to produce rows.

Later steps can switch to Docling's structured JSON if needed.
"""

from docling.document_converter import DocumentConverter


def docling_md(path: str) -> str:
    """Whole-document markdown (no page numbers)."""
    conv = DocumentConverter()
    doc = conv.convert(path).document
    return doc.export_to_markdown()


def docling_md_pages(path: str):
    """
    Yield (page_no, markdown_text) for each page (1-based).
    Uses Docling's page-level export so we can attach page_no.
    """
    conv = DocumentConverter()
    doc = conv.convert(path).document
    # Most Docling builds expose .pages with page-like objects
    # that support export_to_markdown().
    if hasattr(doc, "pages"):
        for i, page in enumerate(doc.pages, start=1):
            try:
                md = page.export_to_markdown()
            except Exception:
                # Fallback: if a particular page can't export, emit empty string
                md = ""
            yield (i, md)
    else:
        # Fallback to whole-doc if pages are not exposed
        yield (0, doc.export_to_markdown())


def extract_markdown(path: str) -> str:
    """Backward-compatible alias for docling_md."""
    return docling_md(path)
