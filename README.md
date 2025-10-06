# Green Guard — Extraction MVP (Step 1)

This step builds a robust **PDF → Markdown → Sentences → .xlsx** pipeline using **Docling** with detailed logs.

## Quick start
```bash
pip install -r extractor/requirements.txt
python extractor/cli.py --in path/to/your.pdf --out outputs/your.xlsx --log-level INFO
```

## What it does

1. Converts PDF to Markdown via Docling
2. Parses Markdown into sentences/lines while preserving:
   - Headings (with level)
   - Bulleted lines
   - Table rows (kept as single lines; marked is_table=1)
3. Exports to .xlsx with metadata columns

## Next steps

Only once this initial set up is done and stable I would next like to add optional backends (Agentic-Doc / PyMuPDF4LLM) and a Streamlit MVP.
