import html
import re
import unicodedata

# precompile small regex set
MULTISPACE_RE = re.compile(r"[ \t]{2,}")
NBSP_RE       = re.compile(r"\u00A0")         # non-breaking space
CTRL_RE       = re.compile(r"[\u0000-\u001F\u007F]")
DUP_EN_RE     = re.compile(r"^(?P<a>.+?)\s+\1$", re.IGNORECASE)  # "abc abc" -> "abc"
# common bilingual prefix pattern: non-Latin block then the English
NON_LATIN_PREFIX_RE = re.compile(r"^(?P<nonlatin>[^\x00-\x7F]{2,}[\s:|-/]+)(?P<latin>[A-Za-z].+)$")
# stray pipes from markdown tables when one cell leaks
LEADING_PIPE_RE = re.compile(r"^\s*\|\s*")
TRAILING_PIPE_RE = re.compile(r"\s*\|\s*$")


def _strip_bilingual_prefix(s: str) -> str:
    """
    If line begins with a non-Latin chunk followed by the same English phrase,
    prefer the English portion. Example:
      'CEO 메시지 Message from the CEO' -> 'Message from the CEO'
    """
    m = NON_LATIN_PREFIX_RE.match(s)
    if not m:
        return s
    latin = m.group("latin").strip()

    # If the latin part repeats tokens from the tail or contains clear English words,
    # keep it; otherwise keep original.
    if any(tok in latin.lower() for tok in ("message", "report", "sustainability", "ceo", "target", "governance")):
        return latin
    return s


def clean_text(s: str) -> str:
    if s is None:
        return ""

    # 1) HTML entity decode (&amp; -> &, &nbsp; -> space)
    s = html.unescape(s)

    # 2) Unicode normalization (folds weird diacritics/widths)
    s = unicodedata.normalize("NFKC", s)

    # 3) Remove control chars, normalize spaces
    s = CTRL_RE.sub(" ", s)
    s = NBSP_RE.sub(" ", s)

    # 4) Drop leading/trailing table pipes that sometimes slip into single cells
    s = LEADING_PIPE_RE.sub("", s)
    s = TRAILING_PIPE_RE.sub("", s)

    # 5) Trim, collapse multi-spaces
    s = s.strip()
    s = MULTISPACE_RE.sub(" ", s)

    # 6) Bilingual prefix cleanup (non-Latin then English)
    s = _strip_bilingual_prefix(s)

    # 7) Simple duplicate phrase collapse: "abc abc" -> "abc"
    m = DUP_EN_RE.match(s)
    if m:
        s = m.group("a")

    return s.strip()
