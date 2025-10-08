from typing import List, Tuple

import fitz  # PyMuPDF


def get_outline_ranges(pdf_path: str) -> List[Tuple[int, str, int, int]]:
    """
    Return list of (level, title, start_page, end_page) (1-indexed pages, inclusive).
    If no outline, returns [].
    """
    doc = fitz.open(pdf_path)
    toc = doc.get_toc()  # rows: [level(int), title(str), page(int, 1-based)]
    if not toc:
        doc.close()
        return []

    # Build (level, title, start, end) by peeking next start
    ranges: List[Tuple[int, str, int, int]] = []
    for i, (lvl, title, start) in enumerate(toc):
        end = (toc[i + 1][2] - 1) if i + 1 < len(toc) else doc.page_count
        # clamp
        start = max(1, start)
        end = max(start, min(end, doc.page_count))
        ranges.append((lvl, title.strip(), start, end))
    doc.close()
    return ranges


def label_for_page(ranges: List[Tuple[int, str, int, int]], page_no: int) -> Tuple[str, str, str]:
    """
    For a given page_no (1-based), return best (h1,h2,h3) derived from outline levels.
    """
    # collect all outline entries covering this page
    covers = [(lvl, title) for (lvl, title, s, e) in ranges if s <= page_no <= e]
    # Keep top 3 levels
    h1 = h2 = h3 = ""
    for lvl, title in sorted(covers, key=lambda x: x[0]):
        if lvl == 1 and not h1:
            h1 = title
        elif lvl == 2 and not h2:
            h2 = title
        elif lvl >= 3 and not h3:
            h3 = title
    return h1, h2, h3
