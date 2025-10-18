"""
Docling backend: convert input PDF to Markdown.

Rationale:
- Export to Markdown (Docling handles reading order, multi-columns, many tables).
- Parsing Markdown to rows is done in a separate stage.

This version ensures all Docling/RapidOCR artifacts are stored in a writable
directory (artifacts_path), which is required on Streamlit Cloud.
"""

from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    RapidOcrOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption


def _make_pipeline_options(artifacts_path: Path) -> PdfPipelineOptions:
    """Create PdfPipelineOptions with a writable artifacts directory and RapidOCR."""
    artifacts_path = Path(artifacts_path)
    artifacts_path.mkdir(parents=True, exist_ok=True)

    return PdfPipelineOptions(
        artifacts_path=artifacts_path,                       # <<< key: writable dir
        do_ocr=True,                                        # enable OCR
        ocr_options=RapidOcrOptions()                        # RapidOCR options (engine inferred by type)
    )


def _make_converter(artifacts_path: Path) -> DocumentConverter:
    """Build a DocumentConverter that uses our pipeline options for PDFs."""
    pipeline_opts = _make_pipeline_options(artifacts_path)
    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_opts)
        }
    )


def docling_md(path: str, artifacts_path=None) -> str:
    """Whole-document markdown (no page numbers)."""
    apath = Path(artifacts_path) if artifacts_path is not None else Path.cwd() / ".artifacts"
    conv = _make_converter(apath)
    doc = conv.convert(path).document
    return doc.export_to_markdown()


def docling_md_pages(path: str, artifacts_path=None):
    """
    Yield (page_no, markdown_text) for each page (1-based).
    Uses Docling's page-level export so we can attach page_no.
    """
    apath = Path(artifacts_path) if artifacts_path is not None else Path.cwd() / ".artifacts"
    conv = _make_converter(apath)
    doc = conv.convert(path).document

    if hasattr(doc, "pages"):
        for i, page in enumerate(doc.pages, start=1):
            try:
                md = page.export_to_markdown()
            except Exception:
                md = ""
            yield (i, md)
    else:
        # Fallback to whole-doc if pages are not exposed
        yield (0, doc.export_to_markdown())


def extract_markdown(path: str, artifacts_path=None) -> str:
    """Backward-compatible alias for docling_md."""
    return docling_md(path, artifacts_path=artifacts_path)