import os
import io
import pandas as pd
import streamlit as st

from extractor.backends.docling_backend import docling_md
from extractor.sentence_postprocess import parse_markdown_to_rows
from extractor.export import to_xlsx_with_options

# Optional backends
def _pymu_md_pages(path):
    from extractor.backends.pymupdf4llm_backend import extract_markdown_pages
    return list(extract_markdown_pages(path))

def _ade_rows(path):
    from extractor.backends.agenticdoc_backend import extract_rows
    return extract_rows(path)

# ── Page config & header ───────────────────────────────────────────────
st.set_page_config(
    page_title="🌿 Green Guard 3.0",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

col_left, col_right = st.columns([3, 1])
with col_left:
    st.title("🌿 Green Guard 2.0")

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
      AI-powered NLP pipeline for detecting and classifying sustainability claims; within a larger greenwashing detection framework. Green Guard enables researchers and 
      analysts to upload corporate reports and generate clean, structured sentences for 
      further classification and analytics.
    </div>
    """,
    unsafe_allow_html=True,
)
st.divider()

# ── Sidebar controls ──────────────────────────────────────────────────
st.sidebar.header("Extraction Settings")
backend = st.sidebar.selectbox(
    "Select Backend", ["docling", "pymupdf4llm", "agenticdoc"]
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
    
# ── Upload Form ───────────────────────────────────────────────────────
st.markdown("### Upload File and Metadata")
with st.form("upload_form", clear_on_submit=False):
    uploaded = st.file_uploader("Upload ESG / Sustainability PDF", type=["pdf"])
    company = st.text_input("Company Name", value="")
    year = st.text_input("Reporting Year", value="")
    reporting_options = [
        "CDP (Carbon Disclosure Project)",
        "ESRS (European Sustainability Reporting Standards)",
        "GRI (Global Reporting Initiative)",
        "IFRS S1 & S2",
        "ISO 14001 (Environmental Management Systems)",
        "ISO 26000 (Social Responsibility)",
        "ISSB (International Sustainability Standards Board)",
        "Other",
        "SASB (Sustainability Accounting Standards Board)",
        "TCFD (Taskforce on Climate-related Financial Disclosures)",
    ]
    reporting_std = st.selectbox("Reporting Standard", reporting_options, index=0)
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
        "Reporting Standard": reporting_std,
    }

    with st.status("Starting extraction...", state="running") as status:
        progress = st.progress(0, text="Initializing extraction backend...")
        try:
            if backend == "agenticdoc":
                status.update(label="Connecting to Landing AI Agentic Doc API...")
                rows = _ade_rows(tmp_path)

            elif backend == "pymupdf4llm":
                status.update(label="Parsing document pages via PyMuPDF 4LLM...")
                rows = []
                md_pages = _pymu_md_pages(tmp_path)
                total_pages = len(md_pages)
                for i, (page_no, md) in enumerate(md_pages, start=1):
                    for r in parse_markdown_to_rows(md, source_file=uploaded.name, page_no=page_no):
                        rows.append(r)
                    progress.progress(
                        i / total_pages,
                        text=f"Processed page {i}/{total_pages}…"
                    )

            else:
                status.update(label="Converting PDF to Markdown via Docling…")
                md = docling_md(tmp_path)
                status.update(
                    label="Parsing Markdown into structured rows — this may take a few minutes for large PDFs."
                )
                rows = list(parse_markdown_to_rows(md, source_file=uploaded.name))

            status.update(label=f"Extraction complete — {len(rows)} rows generated.", state="complete")

        except Exception as e:
            status.update(label="Extraction failed.", state="error")
            st.error(f"❌ {e}")
            st.stop()

    st.session_state["df_rows"] = rows
    st.session_state["metadata"] = metadata``

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
    for k in ["Company", "Year", "Reporting Standard"]:
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
