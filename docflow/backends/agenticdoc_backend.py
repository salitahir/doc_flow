"""
Agentic-Doc backend (Landing AI): robust layout-aware parsing via API.

Requires:
- pip install agentic-doc python-dotenv
- Set env var VISION_AGENT_API_KEY=your_key (or put it in .env)

This backend returns a list of row dicts that match the DocFlow schema.
"""

import os
from typing import Dict, List, Optional
from dotenv import load_dotenv

# ADE client
from agentic_doc.parse import parse

# Normalize ADE chunk types to our section_type
TYPE_MAP = {
    "heading": "heading",
    "title": "heading",
    "paragraph": "text",
    "text": "text",
    "list_item": "bullet",
    "bullet": "bullet",
    "table": "table",
    "figure": "text",       # fall back to text (caption)
    "caption": "text",
}

def _section_type(t: Optional[str]) -> str:
    if not t:
        return "text"
    return TYPE_MAP.get(t.lower(), "text")

def extract_rows(path: str) -> List[Dict]:
    """
    Call ADE and convert chunks to our row schema.

    Output keys (kept consistent with your pipeline):
      source_file, line_no, page_no, section_type, heading_level, is_table,
      h1, h2, h3, section_path, current_section, text
    """
    load_dotenv()  # allow .env usage
    api_key = os.getenv("VISION_AGENT_API_KEY")
    if not api_key:
        raise RuntimeError(
            "VISION_AGENT_API_KEY not set. Set it in env or .env to use ADE."
        )

    results = parse(path)  # returns list; take the first doc
    if not results:
        return []

    doc = results[0]
    rows: List[Dict] = []
    current_section = ""  # minimal forward-fill like other backends
    line_no = 0

    # ADE exposes doc.chunks with attributes like: type, text, page, level (for headings), etc.
    for ch in doc.chunks:
        line_no += 1
        ch_type = getattr(ch, "type", None)
        sec_type = _section_type(ch_type)
        text = getattr(ch, "text", "") or ""

        # page number if present (ADE often provides 1-based)
        page_no = int(getattr(ch, "page", 0) or 0)
        heading_level = int(getattr(ch, "level", 0) or 0)
        is_table = 1 if sec_type == "table" else 0

        if sec_type == "heading" and text.strip():
            current_section = text.strip()

        rows.append({
            "source_file": os.path.basename(path),
            "line_no": line_no,
            "page_no": page_no,
            "section_type": sec_type,
            "heading_level": heading_level,
            "is_table": is_table,
            # ADE can return hierarchy in future; keep placeholders to align with your schema
            "h1": "",
            "h2": "",
            "h3": "",
            "section_path": "",
            "current_section": current_section,
            "text": text,
        })

    return rows
