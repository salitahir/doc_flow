import pandas as pd
import streamlit as st

from extractor.backends.docling_backend import docling_md
from extractor.sentence_postprocess import parse_markdown_to_rows
from extractor.export import to_xlsx_with_options

# Optional backends wired in earlier tasks
def _pymu_md_pages(path):
    from extractor.backends.pymupdf4llm_backend import extract_markdown_pages
    return list(extract_markdown_pages(path))

def _ade_rows(path):
    from extractor.backends.agenticdoc_backend import extract_rows
    return extract_rows(path)

st.set_page_config(page_title="Green Guard – ESG Extractor", layout="wide")
st.title("Green Guard — ESG PDF Extractor (MVP)")

with st.sidebar:
    st.markdown("### Extraction Settings")
    backend = st.selectbox("Backend", ["docling", "pymupdf4llm", "agenticdoc"])
    st.caption("Agentic-Doc requires VISION_AGENT_API_KEY.")

st.markdown("### Upload & Metadata")
with st.form("upload_form", clear_on_submit=False):
    uploaded = st.file_uploader("Upload ESG / Sustainability PDF", type=["pdf"])
    company = st.text_input("Company", value="")
    year = st.text_input("Year", value="")
    reporting_options = [
        "GRI (Global Reporting Initiative)",
        "ISSB (International Sustainability Standards Board)",
        "IFRS S1 & S2",
        "ESRS (European Sustainability Reporting Standards)",
        "TCFD (Taskforce on Climate-related Financial Disclosures)",
        "CDP (Carbon Disclosure Project)",
        "SASB (Sustainability Accounting Standards Board)",
        "ISO 14001 (Environmental Management Systems)",
        "ISO 26000 (Social Responsibility)",
        "Other",
    ]
    reporting_std = st.selectbox("Reporting Standard", reporting_options, index=0)
    submitted = st.form_submit_button("Extract")

if submitted:
    if not uploaded:
        st.warning("Please upload a PDF.")
        st.stop()

    tmp_path = f"/tmp/{uploaded.name}"
    with open(tmp_path, "wb") as f:
        f.write(uploaded.read())

    metadata = {"Company": company, "Year": year, "Reporting Standard": reporting_std}

    with st.status("Extracting...", state="running") as status:
        try:
            if backend == "agenticdoc":
                status.update(label="Calling Agentic-Doc…")
                rows = _ade_rows(tmp_path)
            elif backend == "pymupdf4llm":
                status.update(label="Converting per-page via PyMuPDF…")
                rows = []
                for page_no, md in _pymu_md_pages(tmp_path):
                    for r in parse_markdown_to_rows(md, source_file=uploaded.name, page_no=page_no):
                        rows.append(r)
            else:
                status.update(label="Converting via Docling…")
                md = docling_md(tmp_path)
                rows = list(parse_markdown_to_rows(md, source_file=uploaded.name))

            df = pd.DataFrame(rows)
            status.update(label=f"Done. {len(df)} rows.", state="complete")

        except Exception as e:
            st.error(f"Extraction failed: {e}")
            st.stop()

    # Build an Excel with renamed headers + hidden columns and metadata
    excel_bytes = to_xlsx_with_options(
        rows,
        out_path=None,  # in-memory for download
        metadata=metadata,
        rename_map=None,  # use defaults
        hidden_cols=["Page_No", "H1", "H2", "H3"],  # your preference
    )

    # Apply the same renaming to the on-screen preview for consistency
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
    if not df.empty:
        df = df.rename(columns=rename_map)
        df.insert(0, "Company", company)
        df.insert(1, "Year", year)
        df.insert(2, "Reporting Standard", reporting_std)

    st.markdown("### Preview")
    st.dataframe(df.head(300), use_container_width=True)

    st.markdown("### Download")
    # CSV
    st.download_button(
        "Download CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="extracted.csv",
        mime="text/csv",
    )
    # Excel (hidden cols applied)
    st.download_button(
        "Download Excel (with hidden columns)",
        data=excel_bytes.getvalue(),
        file_name="extracted.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
