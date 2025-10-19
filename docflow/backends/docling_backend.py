"""Docling backend helpers for converting PDFs to Markdown (robust prefetch)."""

from __future__ import annotations

import os                     # ← ADD THIS LINE
from pathlib import Path
import logging
import shutil

from huggingface_hub import hf_hub_download, HfApi

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    RapidOcrOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption

_log = logging.getLogger(__name__)

HF_REPO = "ds4sd/docling-models"


# ----------------------------- OCR PREFETCH -----------------------------

def _prefetch_rapidocr_models(artifacts_path: Path) -> None:
    """
    Ensure RapidOCR ONNX models exist under:
      <artifacts_path>/RapidOcr/onnx/PP-OCRv4/{det,rec,cls}/...
    """
    apath = Path(artifacts_path)
    apath.mkdir(parents=True, exist_ok=True)

    try:
        from docling.models.rapid_ocr_model import RapidOcrModel  # type: ignore
    except Exception as exc:
        _log.info("RapidOcrModel import failed; skipping OCR prefetch: %s", exc)
        return

    repo_folder = getattr(RapidOcrModel, "_model_repo_folder", "RapidOcr")
    local_dir = apath / repo_folder
    local_dir.mkdir(parents=True, exist_ok=True)

    expected_det = local_dir / "onnx" / "PP-OCRv4" / "det" / "ch_PP-OCRv4_det_infer.onnx"
    if expected_det.exists():
        return

    for backend_name in ("onnxruntime", "onnx"):
        try:
            RapidOcrModel.download_models(
                backend=backend_name,
                local_dir=local_dir,
                force=False,
                progress=False,
            )
            if expected_det.exists():
                return
        except Exception as exc:
            _log.info("RapidOCR download via backend=%s failed: %s", backend_name, exc)

    raise FileNotFoundError(f"RapidOCR ONNX models not found. Expected: {expected_det}")


# --------------------------- LAYOUT PREFETCH ----------------------------

def _download_first_ok(repo_id: str, candidates: list[str], apath: Path) -> dict[str, str]:
    """
    Try each candidate base path in HF. Return {'weights','config','preproc'} on first success.
    We catch broad exceptions to support multiple huggingface_hub versions.
    """
    last_err: Exception | None = None
    for base in candidates:
        try:
            w = hf_hub_download(repo_id=repo_id, filename=f"{base}/model.safetensors",
                                local_dir=apath, local_dir_use_symlinks=False)
            c = hf_hub_download(repo_id=repo_id, filename=f"{base}/config.json",
                                local_dir=apath, local_dir_use_symlinks=False)
            p = hf_hub_download(repo_id=repo_id, filename=f"{base}/preprocessor_config.json",
                                local_dir=apath, local_dir_use_symlinks=False)
            return {"weights": w, "config": c, "preproc": p}
        except Exception as e:
            last_err = e
            continue
    if last_err:
        raise last_err
    raise RuntimeError("No candidate paths attempted.")


def _prefetch_layout_model(artifacts_path: Path) -> None:
    """
    Ensure layout model files exist exactly at:
        <artifacts_path>/model.safetensors
        <artifacts_path>/config.json
        <artifacts_path>/preprocessor_config.json

    We fetch Docling's RT-DETRv2 layout model and save it in-place so
    LayoutPredictor (AutoModelForObjectDetection) can load it.
    """
    apath = Path(artifacts_path)                     # ← define apath
    apath.mkdir(parents=True, exist_ok=True)

    target_weights = apath / "model.safetensors"
    target_cfg = apath / "config.json"
    target_pre = apath / "preprocessor_config.json"

    if target_weights.exists() and target_cfg.exists() and target_pre.exists():
        return

    try:
        # object-detection model class
        from transformers import RTDetrV2ForObjectDetection, AutoImageProcessor, AutoProcessor
    except Exception as exc:
        raise RuntimeError(
            "Transformers not installed. Add `transformers>=4.41,<5` to requirements."
        ) from exc

    # Use Docling's RT-DETRv2 layout model (correct type for AutoModelForObjectDetection)
    model_id = os.environ.get("DOCLING_LAYOUT_MODEL_ID", "ds4sd/docling-layout-heron")

    # 1) Download & save model (writes model.safetensors + config.json)
    model = RTDetrV2ForObjectDetection.from_pretrained(model_id, trust_remote_code=False)
    model.save_pretrained(str(apath), safe_serialization=True)
    del model

    # 2) Download & save processor config
    try:
        proc = AutoImageProcessor.from_pretrained(model_id, trust_remote_code=False)
    except Exception:
        proc = AutoProcessor.from_pretrained(model_id, trust_remote_code=False)
    proc.save_pretrained(str(apath))

    # Some repos use processor_config.json; rename to preprocessor_config.json
    alt = apath / "processor_config.json"
    if not target_pre.exists() and alt.exists():
        alt.rename(target_pre)

    # Final sanity check
    missing = [p.name for p in (target_weights, target_cfg, target_pre) if not p.exists()]
    if missing:
        raise FileNotFoundError(
            f"Layout model prefetch did not create files: {', '.join(missing)} in {apath}"
        )
# ---------------------------- DOC LING PIPE ----------------------------

def _prefetch_table_models(artifacts_path: Path) -> None:
    """
    Ensure Docling's table-structure assets exist under:
        <artifacts_path>/accurate/tm_config.json
    We scan ds4sd/docling-models for a directory containing tm_config.json,
    then mirror that directory into <artifacts_path>/accurate/.
    """
    apath = Path(artifacts_path)
    table_dir = apath / "accurate"
    (table_dir).mkdir(parents=True, exist_ok=True)

    target_cfg = table_dir / "tm_config.json"
    if target_cfg.exists():
        return  # already present

    # Find a 'tm_config.json' in the HF repo
    api = HfApi()
    files = api.list_repo_files(repo_id=HF_REPO)

    # Prefer table-related paths
    tm_candidates = [p for p in files if p.endswith("tm_config.json")]
    if not tm_candidates:
        raise FileNotFoundError(
            "Docling table-structure assets not found in HF repo: no 'tm_config.json'."
        )

    # Score candidates: prefer ones that look table-ish and are shallower
    KEYWORDS = ("table", "tableformer", "table_structure", "tsr", "accurate")
    def score(path: str) -> tuple[int, int]:
        name = path.lower()
        kw_hit = 0 if any(k in name for k in KEYWORDS) else 1
        depth = path.count("/")
        return (kw_hit, depth)

    tm_candidates.sort(key=score)
    tm_path = tm_candidates[0]               # e.g. 'model_artifacts/table/.../tm_config.json'
    base = "/".join(tm_path.split("/")[:-1]) # the folder containing tm_config.json

    # Download everything under that base dir and mirror into <artifacts>/accurate/
    for p in files:
        if p == base or p.startswith(base + "/"):
            local = hf_hub_download(
                repo_id=HF_REPO,
                filename=p,
                local_dir=apath,                 # fetch to a temp cache under artifacts
                local_dir_use_symlinks=False,
            )
            rel = p[len(base):].lstrip("/")      # path relative to base
            dest = table_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(local, dest)

    if not target_cfg.exists():
        raise FileNotFoundError(
            f"Table-structure prefetch did not create {target_cfg}. "
            f"Tried base '{base}' from {HF_REPO}."
        )

def _make_pipeline_options(artifacts_path: Path) -> PdfPipelineOptions:
    apath = Path(artifacts_path)
    apath.mkdir(parents=True, exist_ok=True)

    # NEW: table-structure assets (needed for TableStructureModel)
    _prefetch_table_models(apath)

    # Existing: layout (object detection) + OCR assets
    _prefetch_layout_model(apath)
    _prefetch_rapidocr_models(apath)

    rocr = RapidOcrOptions()
    return PdfPipelineOptions(
        artifacts_path=apath,
        do_ocr=True,
        ocr_options=rocr,
    )

def _make_converter(artifacts_path: Path) -> DocumentConverter:
    pipeline_opts = _make_pipeline_options(artifacts_path)
    return DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_opts)}
    )


def docling_md(path: str, artifacts_path=None) -> str:
    apath = Path(artifacts_path) if artifacts_path is not None else Path.cwd() / ".artifacts"
    conv = _make_converter(apath)
    doc = conv.convert(path).document
    return doc.export_to_markdown()


def docling_md_pages(path: str, artifacts_path=None):
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
        yield (0, doc.export_to_markdown())


def extract_markdown(path: str, artifacts_path=None) -> str:
    return docling_md(path, artifacts_path=artifacts_path)