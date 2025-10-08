import pandas as pd
from typing import Dict, List, Optional
from io import BytesIO

_REQUIRED_COLS = [
    "source_file", "line_no", "page_no",
    "section_type", "heading_level", "is_table",
    "h1", "h2", "h3", "section_path",
    "current_section", "text",
]

# Default renames you asked for
DEFAULT_RENAME = {
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

DEFAULT_HIDDEN = {"Page_No", "H1", "H2", "H3"}


def _ensure_cols(df: pd.DataFrame) -> pd.DataFrame:
    for col in _REQUIRED_COLS:
        if col not in df.columns:
            df[col] = None
    return df


def _order_cols(df: pd.DataFrame, meta_cols: List[str], rename_map: Dict[str, str]) -> pd.DataFrame:
    base_keys = [
        "source_file", "line_no", "page_no", "section_type", "heading_level", "is_table",
        "section_path", "current_section", "text", "h1", "h2", "h3",
    ]
    renamed_base = [rename_map.get(key, key) for key in base_keys]
    ordered = meta_cols + [col for col in renamed_base if col in df.columns]
    extras = [col for col in df.columns if col not in ordered]
    return df[ordered + extras]


def to_xlsx(rows: List[Dict], out_path: str) -> None:
    """Backwards-compatible: no meta, default names."""
    if not rows:
        pd.DataFrame(columns=_REQUIRED_COLS).rename(columns=DEFAULT_RENAME).to_excel(out_path, index=False)
        return
    df = pd.DataFrame(rows)
    df = _ensure_cols(df).rename(columns=DEFAULT_RENAME)
    df = _order_cols(df, meta_cols=[], rename_map=DEFAULT_RENAME)
    df.to_excel(out_path, index=False)


def to_xlsx_with_options(
    rows: List[Dict],
    out_path: Optional[str] = None,
    metadata: Optional[Dict[str, str]] = None,  # {"Company": "...", "Year": "2024", "Document Type": "..."}
    rename_map: Optional[Dict[str, str]] = None,
    hidden_cols: Optional[List[str]] = None,
) -> BytesIO:
    """
    Write Excel with metadata columns, renamed headers, and hidden columns.
    If out_path is None, returns an in-memory BytesIO (useful for Streamlit download).
    """
    if rows:
        df = pd.DataFrame(rows)
    else:
        df = pd.DataFrame(columns=_REQUIRED_COLS)

    df = _ensure_cols(df)

    rename_map = rename_map or DEFAULT_RENAME
    df = df.rename(columns=rename_map)

    meta = metadata or {}
    for key in ["Company", "Year", "Document Type"]:
        df[key] = meta.get(key, "")
    df = _order_cols(df, meta_cols=["Company", "Year", "Document Type"], rename_map=rename_map)

    bio = BytesIO()
    with pd.ExcelWriter(out_path or bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="extracted")
        worksheet = writer.sheets["extracted"]
        to_hide = set(hidden_cols or DEFAULT_HIDDEN)
        header_row = 1
        header_names = {
            worksheet.cell(row=header_row, column=col).value: col
            for col in range(1, worksheet.max_column + 1)
        }
        for name in to_hide:
            col_idx = header_names.get(name)
            if col_idx:
                column_letter = worksheet.cell(row=1, column=col_idx).column_letter
                worksheet.column_dimensions[column_letter].hidden = True

    if out_path:
        bio.seek(0)
        return bio
    bio.seek(0)
    return bio
