"""Utilities for exporting parsed rows to Excel."""

import logging
from typing import Iterable, List, Mapping

import pandas as pd

LOGGER = logging.getLogger("green_guard.extractor.export")

REQUIRED_COLUMNS = [
    "source_file",
    "line_no",
    "section_type",
    "heading_level",
    "is_table",
    "text",
]


def _validate_rows(rows: Iterable[Mapping]) -> List[Mapping]:
    materialized: List[Mapping] = list(rows)
    if not materialized:
        LOGGER.warning("No rows provided for export; resulting workbook will be empty.")
        return materialized

    missing_columns = set()
    for row in materialized:
        missing_columns.update(col for col in REQUIRED_COLUMNS if col not in row)
    if missing_columns:
        raise ValueError(f"Rows missing required columns: {sorted(missing_columns)}")
    return materialized


def to_xlsx(rows: Iterable[Mapping], out_path: str) -> None:
    """Write iterable of row dicts to Excel with a stable column order."""
    materialized = _validate_rows(rows)
    df = pd.DataFrame(materialized, columns=REQUIRED_COLUMNS)
    df.to_excel(out_path, index=False, engine="openpyxl")
    LOGGER.info("Excel export complete: %s (rows=%d)", out_path, len(df))
