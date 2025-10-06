#!/usr/bin/env python3
import argparse
import logging
import os
from datetime import datetime
from tqdm import tqdm

from backends.docling_backend import docling_md  # your existing function
from export import to_xlsx
from sentence_postprocess import parse_markdown_to_rows
from utils.outline import get_outline_ranges, label_for_page  # keep optional

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
    parser = argparse.ArgumentParser(description="Green Guard — Extraction (stable default)")
    parser.add_argument("--in", dest="input_path", required=True, help="Path to PDF")
    parser.add_argument("--out", dest="out_path", required=True, help="Path to .xlsx")
    parser.add_argument("--backend", choices=["docling", "pymupdf4llm"], default="docling",
                        help="Extraction backend (default=docling)")
    parser.add_argument("--use-pdf-outline", action="store_true",
                        help="If set (and page_no is available), override h1/h2/h3 from PDF bookmarks.")
    parser.add_argument("--heuristic-headings", action="store_true",
                        help="Enable optional numbering/caps heuristics for heading detection.")
    parser.add_argument("--log-level", dest="log_level", default="INFO",
                        help="DEBUG, INFO, WARNING, ERROR, CRITICAL")
    args = parser.parse_args()

    setup_logging(args.log_level)
    start_ts = datetime.now()

    input_path = args.input_path
    out_path = args.out_path

    if not os.path.exists(input_path):
        LOGGER.error("Input file not found: %s", input_path)
        raise SystemExit(1)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    LOGGER.info("Extraction started | backend=%s | heuristics=%s", args.backend, args.heuristic_headings)

    rows = []
    if args.backend == "pymupdf4llm":
        from backends.pymupdf4llm_backend import extract_markdown_pages
        md_pages = list(extract_markdown_pages(input_path))
        LOGGER.info("Conversion complete via PyMuPDF. Pages: %d", len(md_pages))

        # Safety net: warn if any pages are empty
        empty_pages = [p for p, md in md_pages if not (md and md.strip())]
        if empty_pages:
            LOGGER.warning("No markdown extracted for %d page(s): %s", len(empty_pages), empty_pages[:10])

        LOGGER.info("Step 2/3: Parsing page chunks into rows")
        for page_no, md_text in tqdm(md_pages, desc="Parsing pages", unit="page"):
            for r in parse_markdown_to_rows(md_text,
                                            source_file=os.path.basename(input_path),
                                            page_no=page_no,
                                            use_heuristics=args.heuristic_headings):
                rows.append(r)
    else:
        LOGGER.info("Step 1/3: Converting PDF to Markdown via Docling")
        md_text = docling_md(input_path)
        LOGGER.info("Docling conversion complete. Markdown length: %d chars", len(md_text))

        LOGGER.info("Step 2/3: Parsing Markdown into rows")
        for r in tqdm(parse_markdown_to_rows(md_text,
                                             source_file=os.path.basename(input_path),
                                             use_heuristics=args.heuristic_headings),
                      desc="Parsing", unit="row"):
            rows.append(r)

    # Optional outline enrichment (works best with page_no)
    if args.use_pdf_outline:
        LOGGER.info("Enriching rows with PDF outline data")
        ranges = get_outline_ranges(input_path)
        if ranges:
            for r in rows:
                pg = r.get("page_no", 0)
                if pg > 0:
                    oh1, oh2, oh3 = label_for_page(ranges, pg)
                    if oh1 or oh2 or oh3:
                        r["h1"] = oh1 or r.get("h1", "")
                        r["h2"] = oh2 or r.get("h2", "")
                        r["h3"] = oh3 or r.get("h3", "")
                        r["section_path"] = " > ".join([x for x in [r["h1"], r["h2"], r["h3"]] if x])
        else:
            LOGGER.info("No outline found; skipping enrichment")

    # Quality summary
    LOGGER.info("Step 3/3: Quality summary before export")
    total = len(rows)
    n_empty = sum(1 for r in rows if not r.get("text"))
    n_head = sum(1 for r in rows if r.get("section_type") == "heading")
    n_table = sum(1 for r in rows if r.get("section_type") == "table")
    n_bull  = sum(1 for r in rows if r.get("section_type") == "bullet")
    LOGGER.info("Rows=%d | empty_text=%d | headings=%d | tables=%d | bullets=%d", total, n_empty, n_head, n_table, n_bull)
    if n_empty > max(5, int(0.05 * total)):
        LOGGER.warning("High empty-text ratio detected; consider using --backend docling")
    if n_head < 10 and args.backend != "docling":
        LOGGER.warning("Few headings detected; consider using --backend docling")

    LOGGER.info("Writing to Excel: %s", out_path)
    to_xlsx(rows, out_path)
    elapsed = (datetime.now() - start_ts).total_seconds()
    LOGGER.info("Done. Wrote %d rows to %s (%.2fs)", total, out_path, elapsed)

if __name__ == "__main__":
    main()
