# Green Guard — Document Parser

Green Guard is a focused document-to-structured-data pipeline designed to extract sentences, metadata, and tabular markers from PDF reports. The project powers downstream sustainability and compliance workflows by delivering clean, analyzable spreadsheets from messy source documents.

## 🚀 What makes it useful
- **Reliable PDF ingestion.** Uses [Docling](https://github.com/DS4SD/docling) to convert PDFs into Markdown with stable layout fidelity.
- **Sentence-first parsing.** Breaks Markdown into sentence-level rows while preserving headings, bullet structure, and table context flags.
- **Spreadsheet-ready output.** Exports processed text into `.xlsx` files with metadata columns tailored for labeling and review.
- **Transparent processing.** Verbose logging highlights every transformation step to make debugging and auditing easy.

## 🧭 How the pipeline works
1. **PDF ➜ Markdown.** Docling renders each page, preserving heading hierarchy and list markers.
2. **Markdown ➜ Structured rows.** Custom parsing cleans artifacts, segments text, and tags row context (heading level, bullet state, table membership).
3. **Rows ➜ Excel workbook.** The exporter writes cleaned rows and metadata into separate worksheet columns for quick filtering.

## 📂 Project layout
```
extractor/
  backends/             # Interfaces to additional parsing engines (Docling today, more soon)
  cli.py                # Entry point for running the pipeline from the command line
  export.py             # Excel writer utilities
  sentence_postprocess.py  # Sentence segmentation and cleanup routines
  text_clean.py         # Markdown-specific normalization helpers
  utils/                # Shared helpers (logging, I/O, constants)
app/                    # Placeholder for future UI / Streamlit prototype
```

## 🏁 Quick start
```bash
pip install -r extractor/requirements.txt
python extractor/cli.py --in path/to/your.pdf --out outputs/your.xlsx --log-level INFO
```

This command converts your PDF into an Excel workbook with columns such as `text`, `heading_level`, `is_bullet`, and `is_table` for downstream analysis.

## 🛣️ Roadmap
- Optional backend support (Agentic-Doc, PyMuPDF4LLM) for specialized PDFs.
- Streamlit-based reviewer dashboard for rapid validation.
- Smart chunking and annotation-ready exports for ML labeling workflows.

## 🤝 Contributing
Issues and pull requests are welcome! If you spot a parsing edge case or have a feature request, open an issue describing the document type and desired output. For significant contributions, please coordinate on GitHub Discussions first to align on approach.

---
Green Guard is maintained by the Green Guard team to accelerate compliant, traceable document understanding.
