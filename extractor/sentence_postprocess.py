"""
Parse Markdown into structured rows.

Goals:
- Default: rely on explicit Markdown headings (#, ##, ### ...) for reliability.
- Optional: enable heuristics (numbered/caps) via flag for tricky docs.
- Always forward-fill a simple `current_section` (last seen heading text).
"""

import re
from typing import Dict, Iterator, List, Optional

from extractor.text_clean import clean_text

# Explicit markdown headings
_HEADING_RE = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<text>.+)$")
# Bullets and tables
_BULLET_RE  = re.compile(r"^\s*([-*•]|\d+\.)\s+(.+)$")
_TABLE_RE   = re.compile(r"^\s*\|.+\|\s*$")
# Basic cleaners
_TOC_HINTS  = re.compile(r"(table of contents|contents|index)$", re.I)
_REFERENCES = re.compile(r"^(references|bibliography|works cited)\b", re.I)
# Sentence split (naive but reliable)
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")

# --- Heuristic heading detectors (only used when use_heuristics=True) ---
_NUM_HEADING = re.compile(r"^\s*(\d+(?:\.\d+){0,4})\s+[^\s].*$")
_ALPHA_HEADING = re.compile(r"^\s*([A-Z])\.\s+[^\s].*$")
_ROMAN_HEADING = re.compile(r"^\s*([IVXLCDM]+)\.\s+[^\s].*$", re.I)

def _is_toc_or_reference(line: str) -> bool:
    l = line.strip()
    if not l:
        return False
    return bool(_TOC_HINTS.search(l)) or bool(_REFERENCES.search(l))

def _caps_ratio(s: str) -> float:
    letters = [c for c in s if c.isalpha()]
    if not letters:
        return 0.0
    caps = [c for c in letters if c.isupper()]
    return len(caps) / len(letters)

def _infer_level_from_numbering(s: str) -> Optional[int]:
    m = _NUM_HEADING.match(s)
    if m:
        return min(6, m.group(1).count(".") + 1)
    if _ROMAN_HEADING.match(s):
        return 1
    if _ALPHA_HEADING.match(s):
        return 2
    return None

def _maybe_heading_from_heuristics(s: str, last_level: int) -> Optional[int]:
    text = s.strip()
    if not text:
        return None
    words = text.split()
    if len(words) <= 12 and not text.endswith(('.', '!', '?')) and _caps_ratio(text) >= 0.6:
        return min(max(1, last_level + 1), 3)
    return None
# -----------------------------------------------------------------------

def _emit_row(
    source_file: str,
    line_no: int,
    text: str,
    section_type: str,
    heading_level: int,
    is_table: int,
    current_section: str,
    page_no: int = 0,
    h1: str = "", h2: str = "", h3: str = "", section_path: str = ""
) -> Dict:
    return {
        "source_file": source_file,
        "line_no": line_no,
        "page_no": page_no,
        "section_type": section_type,
        "heading_level": heading_level or 0,
        "is_table": is_table,
        "h1": h1,
        "h2": h2,
        "h3": h3,
        "section_path": section_path,
        "current_section": current_section,
        "text": text.strip(),
    }

def parse_markdown_to_rows(
    md_text: str,
    source_file: str,
    page_no: int = 0,
    use_heuristics: bool = False,
) -> Iterator[Dict]:
    """
    Default behaviour (use_heuristics=False):
        - Only trust explicit markdown headings (#, ##, ...)
        - Forward-fill `current_section` from last heading text
    Optional behaviour (use_heuristics=True):
        - Also detect numbered/roman/alpha headings and caps-heavy short lines
    """
    current_section = ""
    last_heading_level = 0

    for i, raw in enumerate(md_text.splitlines(), start=1):
        line = raw.rstrip()
        if not line or _is_toc_or_reference(line):
            continue

        # 1) Explicit markdown heading (most reliable)
        m = _HEADING_RE.match(line)
        if m:
            level = len(m.group("hashes"))
            text = clean_text(m.group("text").strip())
            if not text:
                continue
            current_section = text  # forward-fill simple context
            last_heading_level = level
            yield _emit_row(
                source_file, i, text,
                section_type="heading", heading_level=level, is_table=0,
                current_section=current_section, page_no=page_no
            )
            continue

        # 2) Table rows
        if _TABLE_RE.match(line):
            cleaned_line = clean_text(line)
            if not cleaned_line:
                continue
            yield _emit_row(
                source_file, i, cleaned_line,
                section_type="table", heading_level=0, is_table=1,
                current_section=current_section, page_no=page_no
            )
            continue

        # 3) Bullets
        if _BULLET_RE.match(line):
            cleaned_bullet = clean_text(line.strip())
            if not cleaned_bullet:
                continue
            yield _emit_row(
                source_file, i, cleaned_bullet,
                section_type="bullet", heading_level=0, is_table=0,
                current_section=current_section, page_no=page_no
            )
            continue

        # 4) Optional heuristic headings (only if enabled)
        if use_heuristics:
            lvl = _infer_level_from_numbering(line)
            if lvl is not None:
                txt_raw = line.split(None, 1)[1] if " " in line else line
                txt = clean_text(txt_raw)
                if not txt:
                    continue
                current_section = txt
                last_heading_level = lvl
                yield _emit_row(
                    source_file, i, txt,
                    section_type="heading", heading_level=lvl, is_table=0,
                    current_section=current_section, page_no=page_no
                )
                continue

            lvl2 = _maybe_heading_from_heuristics(line, last_heading_level)
            if lvl2 is not None:
                current_section = clean_text(line.strip())
                if not current_section:
                    continue
                last_heading_level = lvl2
                yield _emit_row(
                    source_file, i, current_section,
                    section_type="heading", heading_level=lvl2, is_table=0,
                    current_section=current_section, page_no=page_no
                )
                continue

        # 5) Plain text -> naive sentence split
        for s in _SENT_SPLIT.split(line.strip()):
            if s:
                s_clean = clean_text(s)
                if not s_clean:
                    continue
                yield _emit_row(
                    source_file, i, s_clean,
                    section_type="text", heading_level=0, is_table=0,
                    current_section=current_section, page_no=page_no
                )
