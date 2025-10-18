"""Docling backend helpers for converting PDFs to Markdown."""

from __future__ import annotations

import logging
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
from docling.document_converter import DocumentConverter, PdfFormatOption


_log = logging.getLogger(__name__)


def _ensure_rapidocr_assets(options: RapidOcrOptions, artifacts_path: Path) -> bool:
    """Return True if RapidOCR can run (models present or downloaded)."""

    try:
        from docling.models.rapid_ocr_model import RapidOcrModel
    except Exception as exc:  # pragma: no cover - defensive guardrail
        _log.warning("RapidOCR backend unavailable: %s", exc)
        return False

    backend = options.backend
    if backend not in ("onnxruntime", "torch"):
        _log.debug("Unsupported RapidOCR backend '%s'; disabling OCR", backend)
        return False

    model_root = artifacts_path / RapidOcrModel._model_repo_folder  # noqa: SLF001
    model_root.mkdir(parents=True, exist_ok=True)

    model_specs = getattr(RapidOcrModel, "_default_models", {}).get(backend, {})
    required_files = [model_root / spec["path"] for spec in model_specs.values()]

    def _have_all_models() -> bool:
        return all(path.exists() for path in required_files)

    if not _have_all_models():
        try:
            RapidOcrModel.download_models(
                backend,
                local_dir=model_root,
                force=False,
                progress=False,
            )
        except Exception as exc:  # pragma: no cover - surfaces at runtime
            _log.warning("Unable to prefetch RapidOCR models: %s", exc)

    if not _have_all_models():
        missing = [str(path.relative_to(artifacts_path)) for path in required_files if not path.exists()]
        _log.warning(
            "RapidOCR models missing after download attempt; OCR will be disabled. Missing: %s",
            ", ".join(missing) or "<unknown>",
        )
        return False

    return True


def _make_pipeline_options(artifacts_path: Path) -> PdfPipelineOptions:
    """Create PdfPipelineOptions with a writable artifacts directory and RapidOCR."""
    artifacts_path = Path(artifacts_path)
    artifacts_path.mkdir(parents=True, exist_ok=True)

    options = RapidOcrOptions()
    have_rapidocr = _ensure_rapidocr_assets(options, artifacts_path)

    return PdfPipelineOptions(
        artifacts_path=artifacts_path,                       # <<< key: writable dir
        do_ocr=have_rapidocr,                               # enable OCR only if models are ready
        ocr_options=options                                  # RapidOCR options (engine inferred by type)
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
