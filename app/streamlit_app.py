import os
import io
import pandas as pd
import streamlit as st

from extractor.backends.docling_backend import docling_md
from extractor.sentence_postprocess import parse_markdown_to_rows

def _pymu_md_pages(path):
    from extractor.backends.pymupdf4llm_backend import extract_markdown_pages
    return list(extract_markdown_pages(path))

def _ade_rows(path):
    from extractor.backends.agenticdoc_backend import extract_rows
    return extract_rows(path)

st.set_page_config(page_title="Green Guard – Extractor", layout="wide")
st.title("Green Guard — ESG PDF Extractor (MVP)")
backend = st.selectbox("Backend", ["docling", "pymupdf4llm", "agenticdoc"])
st.caption("Set VISION_AGENT_API_KEY in your environment for Agentic-Doc.")

uploaded = st.file_uploader("Upload a PDF", type=["pdf"])
run = st.button("Extract")

def download_buttons(df: pd.DataFrame):
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", data=csv, file_name="extracted.csv", mime="text/csv")
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="extracted")
    st.download_button("Download Excel", data=bio.getvalue(), file_name="extracted.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if run:
    if not uploaded:
        st.warning("Please upload a PDF first.")
        st.stop()

    tmp_path = f"/tmp/{uploaded.name}"
    with open(tmp_path, "wb") as f:
        f.write(uploaded.read())

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

    st.subheader("Preview")
    st.dataframe(df.head(300), use_container_width=True)
    st.subheader("Download")
    download_buttons(df)
