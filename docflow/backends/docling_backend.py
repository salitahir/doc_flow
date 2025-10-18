"""Docling backend helpers for converting PDFs to Markdown."""

from __future__ import annotations

import logging
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    RapidOcrOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption


_log = logging.getLogger(__name__)


def _ensure_rapidocr_assets(options: RapidOcrOptions, artifacts_path: Path) -> None:
    """Make sure the RapidOCR backend has the model files it expects."""

    try:
        from docling.models.rapid_ocr_model import RapidOcrModel
    except Exception as exc:  # pragma: no cover - defensive guardrail
        # ImportError is the expected failure mode if RapidOCR is unavailable.
        # Defer to Docling's pipeline which will raise a clearer error.
        _log.debug("Skipping RapidOCR asset prefetch: %s", exc)
        return

    backend = options.backend
    # Docling currently only ships URLs for the default RapidOCR ONNX/Torch bundles.
    if backend not in ("onnxruntime", "torch"):
        return

    try:
        RapidOcrModel.download_models(
            backend,
            local_dir=artifacts_path / RapidOcrModel._model_repo_folder,  # noqa: SLF001
            force=False,
            progress=False,
        )
    except Exception as exc:  # pragma: no cover - surfaces at runtime
        _log.warning("Unable to prefetch RapidOCR models: %s", exc)


def _make_pipeline_options(artifacts_path: Path) -> PdfPipelineOptions:
    """Create PdfPipelineOptions with a writable artifacts directory and RapidOCR."""
    artifacts_path = Path(artifacts_path)
    artifacts_path.mkdir(parents=True, exist_ok=True)

    options = RapidOcrOptions()
    _ensure_rapidocr_assets(options, artifacts_path)

    return PdfPipelineOptions(
        artifacts_path=artifacts_path,                       # <<< key: writable dir
        do_ocr=True,                                        # enable OCR
        ocr_options=options                                  # RapidOCR options (engine inferred by type)
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
