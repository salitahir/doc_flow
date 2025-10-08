import os
import pandas as pd
import streamlit as st

# --- make sure local package "docflow" is importable on Streamlit Cloud ---
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]   # repo root
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# ----------------------------------------------------------------------------

from docflow.backends.docling_backend import docling_md
from docflow.sentence_postprocess import parse_markdown_to_rows
from docflow.export import to_xlsx_with_options

# Optional backends
def _pymu_md_pages(path):
    try:
        from docflow.backends.pymupdf4llm_backend import extract_markdown_pages
        pages = list(extract_markdown_pages(path))
        if not pages:
            raise RuntimeError("No pages extracted (empty or unsupported PDF).")
        return pages
    except Exception as e:
        # Let the caller show a nice error
        raise RuntimeError(f"PyMuPDF extraction failed: {e}") from e

def _ade_rows(path):
    from docflow.backends.agenticdoc_backend import extract_rows
    return extract_rows(path)

# ── Page config & header ───────────────────────────────────────────────
st.set_page_config(
    page_title="Doc Flow",
    page_icon="📃",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Hide Streamlit’s default underline on <h1> elements
st.markdown(
    """
    <style>
    h1 {
        border-bottom: none !important;
        padding-bottom: 0 !important;
        margin-bottom: 0.2em !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

col_left, col_right = st.columns([3, 1])
with col_left:
    st.title("DocFlow: Parsing Tool")

with col_right:
    st.markdown(
        """
        <div style="text-align:right; font-size:0.8em;">
          Developed & Deployed by 
          <a href="https://www.linkedin.com/in/salitahir/" target="_blank">
            Ali Tahir 
          </a>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    """
    <div style="text-align:right; font-size:0.8em; margin-bottom:0.5em;">
      <a href="https://github.com/salitahir/green_guard" target="_blank">
        Project Overview and Documentation
      </a>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div style="text-align:justify; line-height:1.5em;">
      DocFlow converts complex PDFs into clean, structured rows (sentences, headings, bullets, tables) for any downstream NLP or analytics workflow.
    </div>
    """,
    unsafe_allow_html=True,
)

# Keep only this one divider under your description
st.divider()

# ── Sidebar controls ──────────────────────────────────────────────────
st.sidebar.header("Extraction Settings")
backend = st.sidebar.selectbox(
    "Select Backend", ["docling (recommended)", "pymupdf4llm", "agenticdoc"]
)

# Optional Landing.AI key input (only shows if AgenticDoc selected)
if backend == "agenticdoc":
    st.sidebar.markdown("**Landing.AI API Key (for Agentic Doc)**")
    landing_api_key = st.sidebar.text_input(
        "Enter your Landing.AI API key",
        type="password",
        placeholder="sk-xxxxxxxxxxxxxxxxx",
    )
    if landing_api_key:
        os.environ["VISION_AGENT_API_KEY"] = landing_api_key
        st.session_state["landing_api_key"] = landing_api_key

    st.sidebar.caption(
        "🔗 [Landing AI Docs](https://landing.ai/agentic-document-extraction)  "
        "| 💰 [Pricing Info](https://landing.ai/pricing)\n\n"
        "Your key is used locally so you’re billed directly by Landing AI."
    )
else:
    landing_api_key = None

with st.sidebar.expander("⚙️ Backend Info", expanded=False):
    st.markdown(
        """
**Docling (default)**  
- ✅ Best overall text quality & reading order  
- ✅ Good at headings/bullets/tables (markdown)  
- ℹ️ No per-page progress by default (unless using page-wise mode)

**PyMuPDF (pymupdf4llm)**  
- ✅ Fast on CPU, page-by-page progress  
- ✅ Great for simple PDFs; resilient when Docling struggles  
- ⚠️ Complex layouts may lose structure (use as fallback)

**Agentic Doc (Landing AI)**  
- ✅ Most robust for complex layouts (multi-columns, tables, captions)  
- ✅ Returns richer structure; great for tricky ESG reports  
- 💳 Requires API key (billed by Landing AI)  
- 🔗 [Docs](https://landing.ai/agentic-document-extraction) · [Pricing](https://landing.ai/pricing)
        """,
        unsafe_allow_html=True,
    )
    
# ── Upload Form ───────────────────────────────────────────────────────
st.markdown("### Upload File and Metadata")
with st.form("upload_form", clear_on_submit=False):
    uploaded = st.file_uploader("Upload PDF", type=["pdf"])
    company = st.text_input("Company Name", value="")
    year = st.text_input("Document Year", value="")
    document_type_options = [
        "Company Filings",
        "Financial Reports",
        "Marketing Collateral",
        "Regulatory Filings",
        "Research Papers",
        "Technical Manuals",
        "Other",
    ]
    document_type = st.selectbox("Document Type", document_type_options, index=0)
    submitted = st.form_submit_button("🧾 Extract Text")

# ── Run Extraction Only Once per Session ─────────────────────────────
if submitted:
    if not uploaded:
        st.warning("Please upload a PDF file first.")
        st.stop()

    tmp_path = f"/tmp/{uploaded.name}"
    with open(tmp_path, "wb") as f:
        f.write(uploaded.read())

    metadata = {
        "Company": company,
        "Year": year,
        "Document Type": document_type,
    }

    with st.status("Starting extraction...", state="running") as status:
        progress = st.progress(0, text="Initializing extraction backend...")
        try:
            if backend == "agenticdoc":
                status.update(label="Connecting to Landing AI Agentic Doc API...")
                rows = _ade_rows(tmp_path)

            elif backend == "pymupdf4llm":
                status.update(label="Parsing document pages via PyMuPDF 4LLM…")
                rows = []
                md_pages = _pymu_md_pages(tmp_path)
                total_pages = max(1, len(md_pages))  # avoid div-by-zero

                for i, (page_no, md) in enumerate(md_pages, start=1):
                    try:
                        for r in parse_markdown_to_rows(
                            md, source_file=uploaded.name, page_no=page_no
                        ):
                            rows.append(r)
                    except Exception:
                        # Skip only this page if parsing broke (rare)
                        pass

                    progress.progress(i / total_pages, text=f"Processed page {i}/{total_pages}…")

            else:
                status.update(label="Converting PDF to Markdown via Docling: — this may take a few minutes for large PDFs…")
                md = docling_md(tmp_path)
                status.update(
                    label="Parsing Markdown into structured rows — this may take a few minutes for large PDFs."
                )
                rows = list(parse_markdown_to_rows(md, source_file=uploaded.name))

            status.update(label=f"Extraction complete — {len(rows)} rows generated.", state="complete")

        except Exception as e:
            status.update(label="Extraction failed.", state="error")
            st.exception(e)   # shows the stack trace in Streamlit
            st.stop()

    st.session_state["df_rows"] = rows
    st.session_state["metadata"] = metadata

# ── If DataFrame Exists in Session, Show Results ─────────────────────
if "df_rows" in st.session_state:
    rows = st.session_state["df_rows"]
    metadata = st.session_state["metadata"]

    df = pd.DataFrame(rows)
    if df.empty:
        st.warning("No content extracted from the file.")
        st.stop()

    # Apply rename and metadata for display
    rename_map = {
        "source_file": "Source",
        "line_no": "Line_No",
        "page_no": "Page_No",
        "section_type": "Section Type",
        "heading_level": "Heading Level",
        "is_table": "Is Table",
        "h1": "H1",
        "h2": "H2",
        "h3": "H3",
        "section_path": "Section",
        "text": "Text",
        "current_section": "Current Section",
    }
    df = df.rename(columns=rename_map)
    for k in ["Company", "Year", "Document Type"]:
        df.insert(0, k, metadata.get(k, ""))

    st.markdown("### Preview of Extracted Content")
    st.dataframe(df.head(300), use_container_width=True, height=450)

    # Prepare Excel + CSV downloads without clearing session state
    excel_bytes = to_xlsx_with_options(
        rows,
        out_path=None,
        metadata=metadata,
        rename_map=None,
        hidden_cols=["Page_No", "H1", "H2", "H3"],
    )

    st.markdown("### Download Results")
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "💾 Download CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="extracted.csv",
            mime="text/csv",
            key="csv_btn",
        )
    with c2:
        st.download_button(
            "📘 Download Excel (Recommended)",
            data=excel_bytes.getvalue(),
            file_name="extracted.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="xlsx_btn",
        )

else:
    st.info("Upload a PDF and click **Extract Text** to begin.")
