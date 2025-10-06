import pandas as pd
from typing import Dict, List

_REQUIRED_COLS = [
    "source_file","line_no","page_no",
    "section_type","heading_level","is_table",
    "h1","h2","h3","section_path",
    "current_section",   # NEW
    "text",
]

def to_xlsx(rows: List[Dict], out_path: str) -> None:
    if not rows:
        df = pd.DataFrame(columns=_REQUIRED_COLS)
        df.to_excel(out_path, index=False)
        return

    df = pd.DataFrame(rows)
    for c in _REQUIRED_COLS:
        if c not in df.columns:
            df[c] = None
    df = df[_REQUIRED_COLS]
    df.to_excel(out_path, index=False)
