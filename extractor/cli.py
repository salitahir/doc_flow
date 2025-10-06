#!/usr/bin/env python3
"""
CLI for Green Guard Extraction MVP (Step 1).

Pipeline:
    PDF -> (Docling) Markdown -> parse to structured rows -> export .xlsx

Features:
- Clear, pedagogical logging explaining each step
- Robust error handling
- Simple, consistent output schema

Usage:
    python extractor/cli.py --in input.pdf --out outputs/output.xlsx --log-level INFO
"""

import argparse
import logging
import os
from datetime import datetime
from tqdm import tqdm

from backends.docling_backend import extract_markdown
from sentence_postprocess import parse_markdown_to_rows
from export import to_xlsx

LOGGER = logging.getLogger("green_guard.extractor")


def setup_logging(level: str) -> None:
    numeric = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    LOGGER.info("Initialized logging at level=%s", level.upper())


def main():
    parser = argparse.ArgumentParser(description="Green Guard — Extraction MVP")
    parser.add_argument("--in", dest="input_path", required=True, help="Path to PDF")
    parser.add_argument("--out", dest="out_path", required=True, help="Path to .xlsx")
    parser.add_argument(
        "--log-level",
        dest="log_level",
        default="INFO",
        help="DEBUG, INFO, WARNING, ERROR, CRITICAL (default=INFO)",
    )
    args = parser.parse_args()

    setup_logging(args.log_level)
    start_ts = datetime.now()

    input_path = args.input_path
    out_path = args.out_path

    if not os.path.exists(input_path):
        LOGGER.error("Input file not found: %s", input_path)
        raise SystemExit(1)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    LOGGER.info("Extraction started")
    LOGGER.info("Step 1/3: Converting PDF to Markdown via Docling")

    md_text = extract_markdown(input_path)
    LOGGER.info("Docling conversion complete. Markdown length: %d chars", len(md_text))

    LOGGER.info("Step 2/3: Parsing Markdown into structured rows")
    rows_iter = parse_markdown_to_rows(md_text, source_file=os.path.basename(input_path))

    # Materialize to list with progress bar for visibility
    rows = []
    for r in tqdm(rows_iter, desc="Parsing", unit="row"):
        rows.append(r)

    LOGGER.info("Parsed %d rows (lines/sentences)", len(rows))

    LOGGER.info("Step 3/3: Writing to Excel: %s", out_path)
    to_xlsx(rows, out_path)
    elapsed = (datetime.now() - start_ts).total_seconds()
    LOGGER.info("Done. Wrote %d rows to %s (%.2fs)", len(rows), out_path, elapsed)


if __name__ == "__main__":
    main()
