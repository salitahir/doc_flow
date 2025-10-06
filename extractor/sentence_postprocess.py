"""
Markdown -> structured rows with lightweight heuristics.

We preserve:
- Headings with level (#, ##, ### ...)
- Bulleted lines (-, *, •) as one row each
- Table rows (markdown pipes) as one row each (is_table=1)
- Paragraph lines -> naive sentence split (but not inside tables/bullets/headings)

We also filter out typical TOC / references lines using simple keyword rules.
"""

import re
from typing import Dict, Iterator, List, Optional


_HEADING_RE = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<text>.+)$")
_BULLET_RE  = re.compile(r"^\s*([-*•]|\d+\.)\s+(.+)$")
_TABLE_RE   = re.compile(r"^\s*\|.+\|\s*$")  # loose: line starts/ends with pipe
_TOC_HINTS  = re.compile(r"(table of contents|contents|index)$", re.I)
_REFERENCES = re.compile(r"^(references|bibliography|works cited)\b", re.I)

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


def _is_toc_or_reference(line: str) -> bool:
    l = line.strip()
    if not l:
        return False
    return bool(_TOC_HINTS.search(l)) or bool(_REFERENCES.search(l))


def _emit_row(
    source_file: str,
    line_no: int,
    text: str,
    section_type: str,
    heading_level: Optional[int],
    is_table: int,
    h1: Optional[str],
    h2: Optional[str],
    h3: Optional[str],
    page_no: int = 0,
) -> Dict:
    path = " > ".join([x for x in [h1, h2, h3] if x])
    return {
        "source_file": source_file,
        "line_no": line_no,
        "page_no": page_no,
        "section_type": section_type,  # one of: heading, bullet, table, text
        "heading_level": heading_level or 0,
        "is_table": is_table,
        "h1": h1 or "",
        "h2": h2 or "",
        "h3": h3 or "",
        "section_path": path,
        "text": text.strip(),
    }


def parse_markdown_to_rows(md_text: str, source_file: str, page_no: int = 0) -> Iterator[Dict]:
    """
    Generate row dicts from markdown text.
    Each row has: source_file, line_no, page_no, section_type, heading_level,
    is_table, h1/h2/h3, section_path, text.
    """
    current_h1: Optional[str] = ""
    current_h2: Optional[str] = ""
    current_h3: Optional[str] = ""

    for i, raw in enumerate(md_text.splitlines(), start=1):
        line = raw.rstrip()
        if not line:
            continue
        if _is_toc_or_reference(line):
            # Skip obvious non-content sections; we could add more rules later
            continue

        # Headings
        m = _HEADING_RE.match(line)
        if m:
            level = len(m.group("hashes"))
            heading_text = m.group("text").strip()

            if level == 1:
                current_h1 = heading_text
                current_h2 = ""
                current_h3 = ""
            elif level == 2:
                if not current_h1:
                    current_h1 = ""
                current_h2 = heading_text
                current_h3 = ""
            else:
                if not current_h1:
                    current_h1 = ""
                if not current_h2:
                    current_h2 = ""
                current_h3 = heading_text

            yield _emit_row(
                source_file=source_file,
                line_no=i,
                text=heading_text,
                section_type="heading",
                heading_level=level,
                is_table=0,
                h1=current_h1,
                h2=current_h2,
                h3=current_h3,
                page_no=page_no,
            )
            continue

        # Table rows
        if _TABLE_RE.match(line):
            yield _emit_row(
                source_file=source_file,
                line_no=i,
                text=line,
                section_type="table",
                heading_level=None,
                is_table=1,
                h1=current_h1,
                h2=current_h2,
                h3=current_h3,
                page_no=page_no,
            )
            continue

        # Bullets
        if _BULLET_RE.match(line):
            # Keep bullet as a single row; downstream may sentence-split if desired
            bullet_text = _BULLET_RE.sub(lambda m: m.group(0), line).strip()
            yield _emit_row(
                source_file=source_file,
                line_no=i,
                text=bullet_text,
                section_type="bullet",
                heading_level=None,
                is_table=0,
                h1=current_h1,
                h2=current_h2,
                h3=current_h3,
                page_no=page_no,
            )
            continue

        # Paragraph / plain text: naive sentence split
        sentences: List[str] = _SENT_SPLIT.split(line.strip())
        for s in sentences:
            if s:
                yield _emit_row(
                    source_file=source_file,
                    line_no=i,
                    text=s,
                    section_type="text",
                    heading_level=None,
                    is_table=0,
                    h1=current_h1,
                    h2=current_h2,
                    h3=current_h3,
                    page_no=page_no,
                )
