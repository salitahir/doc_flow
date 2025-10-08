#!/usr/bin/env python3
import argparse
import logging
import os
from datetime import datetime
from tqdm import tqdm

from docflow.backends.docling_backend import docling_md
from docflow.sentence_postprocess import parse_markdown_to_rows
from docflow.export import to_xlsx

LOGGER = logging.getLogger("docflow.cli")

def setup_logging(level: str) -> None:
    numeric = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

def main():
    parser = argparse.ArgumentParser(description="DocFlow — PDF to structured text")
    parser.add_argument("--in", dest="input_path", required=True, help="Path to PDF")
    parser.add_argument("--out", dest="out_path", required=True, help="Path to .xlsx")
    parser.add_argument("--backend", choices=["docling", "pymupdf4llm", "agenticdoc"], default="docling")
    parser.add_argument("--use-pdf-outline", action="store_true", help="Override h1/h2/h3 from PDF outline if available.")
    parser.add_argument("--log-level", dest="log_level", default="INFO")
    args = parser.parse_args()

    setup_logging(args.log_level)
    start_ts = datetime.now()

    input_path = args.input_path
    out_path = args.out_path
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    if args.backend == "pymupdf4llm":
        from docflow.backends.pymupdf4llm_backend import extract_markdown_pages
        rows = []
        for page_no, md_text in tqdm(list(extract_markdown_pages(input_path)), desc="Parsing pages", unit="page"):
            for r in parse_markdown_to_rows(md_text, source_file=os.path.basename(input_path), page_no=page_no):
                rows.append(r)
    elif args.backend == "agenticdoc":
        from docflow.backends.agenticdoc_backend import extract_rows
        rows = extract_rows(input_path)
    else:
        md_text = docling_md(input_path)
        rows = list(parse_markdown_to_rows(md_text, source_file=os.path.basename(input_path)))

    if args.use_pdf_outline and rows:
        try:
            from docflow.utils.outline import get_outline_ranges, label_for_page

            outline = get_outline_ranges(input_path)
            if outline:
                for row in rows:
                    page_no = row.get("page_no") or 0
                    if page_no > 0:
                        h1, h2, h3 = label_for_page(outline, page_no)
                        if h1 and not row.get("h1"):
                            row["h1"] = h1
                        if h2 and not row.get("h2"):
                            row["h2"] = h2
                        if h3 and not row.get("h3"):
                            row["h3"] = h3
                        if h1 or h2 or h3:
                            row["section_path"] = " > ".join(filter(None, [row.get("h1", ""), row.get("h2", ""), row.get("h3", "")]))
        except Exception as exc:
            LOGGER.warning("Failed to apply PDF outline: %s", exc)

    to_xlsx(rows, out_path)
    elapsed = (datetime.now() - start_ts).total_seconds()
    print(f"DocFlow: wrote {len(rows)} rows to {out_path} in {elapsed:.2f}s")

if __name__ == "__main__":
    main()
