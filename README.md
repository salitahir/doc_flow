# 📄 DocFlow
Domain-agnostic PDF → structured text extractor. Supports Docling, PyMuPDF (page-wise), and Agentic Document Extraction (Landing AI).
- Output schema includes: Source, Page_No, Line_No, Section Type, Heading Level, Is Table, H1, H2, H3, Section, Current Section, Text.
- Streamlit demo included (upload PDF → choose backend → preview → download CSV/XLSX).
- MIT licensed. Built by Ali Tahir.

## Quickstart
```bash
python -m pip install -r requirements.txt
python -m streamlit run app/streamlit_app.py
# or CLI:
python -m docflow.cli --in sample.pdf --out outputs/sample.xlsx
```

## Backends
- **Docling (default):** best reading order, headings/bullets/tables to Markdown
- **PyMuPDF:** fast CPU, page-by-page progress
- **Agentic-Doc:** robust for complex layouts (requires VISION_AGENT_API_KEY)

## Project Overview
DocFlow is a hybrid document-to-structured-data pipeline designed to help researchers, analysts, and builders extract clean, analyzable text from complex PDF reports. It automates the messy task of parsing long-form documents—turning them into ready-to-use spreadsheets for labeling, analytics, or model training.

### Key Features
- **Multi-backend PDF parsing** — pick Docling, PyMuPDF4LLM, or AgenticDoc depending on layout complexity.
- **Sentence-level extraction** — convert documents into context-rich rows while preserving headings and table flags.
- **Metadata tagging** — enrich rows with heading hierarchy, bullet state, table membership, and page numbers.
- **Spreadsheet export** — output directly to `.xlsx` and `.csv` for downstream workflows.
- **Streamlit UI** — upload a PDF, choose a backend, preview rows, and download with one click.

## Project Layout
| Path                               | Description                                                                    |
|------------------------------------|--------------------------------------------------------------------------------|
| `docflow/backends/`                | Interfaces for multiple PDF parsing engines (Docling, PyMuPDF4LLM, AgenticDoc) |
| `docflow/cli.py`                   | Command-line entry point for local batch runs                                  |
| `docflow/export.py`                | Excel writer and formatting utilities                                          |
| `docflow/sentence_postprocess.py`  | Sentence segmentation and cleanup routines                                     |
| `docflow/text_clean.py`            | Markdown normalization helpers                                                 |
| `docflow/utils/`                   | Shared utilities (logging, constants, and I/O)                                 |
| `app/`                             | Streamlit prototype for interactive document uploads and backend selection     |

## Output Columns
| Column              | Description                                                     |
|---------------------|-----------------------------------------------------------------|
| `Source`            | Filename or identifier of the uploaded PDF                      |
| `Page_No`           | Source page tracking                                            |
| `Line_No`           | Line number within the parsed Markdown                          |
| `Section Type`      | Sentence, heading, table, bullet, etc.                          |
| `Heading Level`     | Hierarchical depth (H1, H2, H3)                                 |
| `Is Table`          | Indicates if the text originated from a table                   |
| `H1` / `H2` / `H3`  | Captured headings based on detected structure                   |
| `Section`           | Section path constructed from headings                          |
| `Current Section`   | Closest heading context                                         |
| `Text`              | Extracted sentence or paragraph                                 |

## Streamlit Interface
DocFlow ships with a Streamlit UI that makes experimentation simple:
1. Upload a PDF file.
2. Select a backend (Docling, PyMuPDF4LLM, or AgenticDoc).
3. Preview the structured rows and download `.xlsx`/`.csv` outputs.

Run locally with:
```bash
python -m streamlit run app/streamlit_app.py
```

## Command Line Usage
Use the CLI for batch jobs or automation:
```bash
python -m docflow.cli --in path/to/document.pdf --out outputs/document.xlsx --backend docling
```

## Credits
**Syed Ali Tahir**  
✉️ [tahirsy@tcd.ie](mailto:tahirsy@tcd.ie)  
✉️ [s.ali.tahir@outlook.com](mailto:s.ali.tahir@outlook.com)  
🔗 [LinkedIn: syed-ali-tahir](https://www.linkedin.com/in/salitahir/)

© 2025 Syed Ali Tahir. All rights reserved. No redistribution without permission.
