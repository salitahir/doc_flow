"""
Docling backend: convert input PDF to Markdown.

Rationale:
- For Step 1, we keep things simple and stable: export to Markdown
  (Docling handles reading order, multi-columns, many tables).
- We then parse Markdown in a separate stage to produce rows.

Later steps can switch to Docling's structured JSON if needed.
"""

from docling.document_converter import DocumentConverter


def extract_markdown(path: str) -> str:
    """
    Convert a file path (PDF) to Markdown using Docling.
    Returns: single Markdown string.
    """
    converter = DocumentConverter()
    doc = converter.convert(path).document
    md_text = doc.export_to_markdown()
    # Note: We keep raw Markdown; parsing happens downstream.
    return md_text
