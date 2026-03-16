"""Parse dates from folder and file name strings.

Supports month+year and day+month+year in many formats:
  - Named month: "Nov 2018", "November 2018", "2018 Nov"
  - Numeric with separator: "11-2018", "2018-11", "01-11-2018", "2018-11-01"
  - Compact numeric: "201811" (YYYYMM), "112018" (MMYYYY)
                     "20181101" (YYYYMMDD), "01112018" (DDMMYYYY)
  - Mixed: "01-Nov-2018", "Nov-01-2018"

Ambiguous DD vs MM ordering defaults to DD-MM-YYYY (European convention).
"""

from __future__ import annotations

import calendar
import re
from typing import Optional

MONTH_NAMES: dict[str, int] = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

# (year, month, day_or_None)
DateResult = tuple[int, int, Optional[int]]


def parse_date(name: str) -> Optional[DateResult]:
    """Full-match parse: the entire string must be a date."""
    s = name.strip()
    return (
        _named_month_year(s)
        or _sep_two_parts(s)
        or _sep_three_parts(s)
        or _six_digits(s)
        or _eight_digits(s)
        or _day_named_month_year(s)
        or _compact_named_month(s)
    )


def find_date_in_name(name: str) -> Optional[DateResult]:
    """Find a date within a string that may contain extra text (e.g. camera filenames)."""
    result = parse_date(name)
    if result:
        return result

    # YYYYMMDD embedded (most common in camera filenames like IMG_20181101_123456)
    for m in re.finditer(r"(?<!\d)(\d{8})(?!\d)", name):
        r = _eight_digits(m.group(1))
        if r:
            return r

    # YYYY-MM-DD or YYYY_MM_DD
    m = re.search(r"(\d{4})[-_.](\d{2})[-_.](\d{2})", name)
    if m:
        r = _valid(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if r:
            return r

    # YYYY-MM or YYYY_MM (not followed by another separator+digits that would make it a date)
    m = re.search(r"(\d{4})[-_](\d{2})(?![-_.]\d)", name)
    if m:
        r = _valid(int(m.group(1)), int(m.group(2)))
        if r:
            return r

    # DDMonYYYY / MonDDYYYY / YYYYMonDD compact form embedded in string
    # e.g. "25Mar1988 Plumbers Ball copy" -> 25Mar1988
    for pattern in (r"(\d{1,2})([A-Za-z]+)(\d{4})", r"([A-Za-z]+)(\d{1,2})(\d{4})", r"(\d{4})([A-Za-z]+)(\d{1,2})"):
        m = re.search(pattern, name)
        if m:
            groups = m.groups()
            r = _compact_named_month("".join(groups))
            if r:
                return r

    # Named month + year somewhere in the string
    m = re.search(r"([A-Za-z]+)\s+(\d{4})", name)
    if m:
        month = MONTH_NAMES.get(m.group(1).lower())
        if month:
            r = _valid(int(m.group(2)), month)
            if r:
                return r

    m = re.search(r"(\d{4})\s+([A-Za-z]+)", name)
    if m:
        month = MONTH_NAMES.get(m.group(2).lower())
        if month:
            r = _valid(int(m.group(1)), month)
            if r:
                return r

    return None


def format_xmp_date(parsed: DateResult) -> str:
    """Format a DateResult as an XMP-compatible date string."""
    y, m, d = parsed
    if d is not None:
        return f"{y:04d}-{m:02d}-{d:02d}"
    return f"{y:04d}-{m:02d}"


# ---------------------------------------------------------------------------
# Internal parsers
# ---------------------------------------------------------------------------

def _valid(y: int, m: int, d: Optional[int] = None) -> Optional[DateResult]:
    if not (1900 <= y <= 2100 and 1 <= m <= 12):
        return None
    if d is not None:
        try:
            max_day = calendar.monthrange(y, m)[1]
        except Exception:
            return None
        if not (1 <= d <= max_day):
            return None
    return (y, m, d)


def _named_month_year(s: str) -> Optional[DateResult]:
    """'Nov 2018', 'November 2018', '2018-Nov', '2018 November'"""
    sep = r"[\s\-_]+"
    m = re.fullmatch(rf"([A-Za-z]+){sep}(\d{{4}})", s)
    if m:
        month = MONTH_NAMES.get(m.group(1).lower())
        if month:
            return _valid(int(m.group(2)), month)
    m = re.fullmatch(rf"(\d{{4}}){sep}([A-Za-z]+)", s)
    if m:
        month = MONTH_NAMES.get(m.group(2).lower())
        if month:
            return _valid(int(m.group(1)), month)
    return None


def _sep_two_parts(s: str) -> Optional[DateResult]:
    """'11-2018', '2018-11' with a separator character"""
    m = re.fullmatch(r"(\d{1,4})([-/._])(\d{1,4})", s)
    if not m:
        return None
    a_s, b_s = m.group(1), m.group(3)
    a, b = int(a_s), int(b_s)
    if len(a_s) == 4:
        return _valid(a, b)
    if len(b_s) == 4:
        return _valid(b, a)
    return None


def _sep_three_parts(s: str) -> Optional[DateResult]:
    """'01-11-2018', '2018-11-01' with a separator; defaults to DD-MM-YYYY."""
    m = re.fullmatch(r"(\d{1,4})([-/._])(\d{1,2})\2(\d{1,4})", s)
    if not m:
        return None
    a_s, b_s, c_s = m.group(1), m.group(3), m.group(4)
    a, b, c = int(a_s), int(b_s), int(c_s)
    if len(a_s) == 4:  # YYYY-MM-DD
        return _valid(a, b, c)
    if len(c_s) == 4:  # DD-MM-YYYY preferred, fall back to MM-DD-YYYY
        return _valid(c, b, a) or _valid(c, a, b)
    return None


def _six_digits(s: str) -> Optional[DateResult]:
    """'201811' (YYYYMM) or '112018' (MMYYYY)"""
    if not re.fullmatch(r"\d{6}", s):
        return None
    # YYYYMM first (year 1900-2100 validates it)
    r = _valid(int(s[:4]), int(s[4:]))
    if r:
        return r
    # MMYYYY
    return _valid(int(s[2:]), int(s[:2]))


def _eight_digits(s: str) -> Optional[DateResult]:
    """'20181101' (YYYYMMDD) or '01112018' (DDMMYYYY)"""
    if not re.fullmatch(r"\d{8}", s):
        return None
    # YYYYMMDD first
    r = _valid(int(s[:4]), int(s[4:6]), int(s[6:]))
    if r:
        return r
    # DDMMYYYY
    return _valid(int(s[4:]), int(s[2:4]), int(s[:2]))


def _compact_named_month(s: str) -> Optional[DateResult]:
    """'11Nov2018' (DDMonYYYY), 'Nov112018' (MonDDYYYY), '2018Nov11' (YYYYMonDD)"""
    m = re.fullmatch(r"(\d{1,2})([A-Za-z]+)(\d{4})", s)
    if m:
        month = MONTH_NAMES.get(m.group(2).lower())
        if month:
            return _valid(int(m.group(3)), month, int(m.group(1)))
    m = re.fullmatch(r"([A-Za-z]+)(\d{1,2})(\d{4})", s)
    if m:
        month = MONTH_NAMES.get(m.group(1).lower())
        if month:
            return _valid(int(m.group(3)), month, int(m.group(2)))
    m = re.fullmatch(r"(\d{4})([A-Za-z]+)(\d{1,2})", s)
    if m:
        month = MONTH_NAMES.get(m.group(2).lower())
        if month:
            return _valid(int(m.group(1)), month, int(m.group(3)))
    return None


def _day_named_month_year(s: str) -> Optional[DateResult]:
    """'01-Nov-2018', 'Nov-01-2018', '01 November 2018', 'YYYY Mon DD'"""
    sep = r"[\s\-/_]"
    # DD Mon YYYY
    m = re.fullmatch(rf"(\d{{1,2}}){sep}([A-Za-z]+){sep}(\d{{4}})", s)
    if m:
        month = MONTH_NAMES.get(m.group(2).lower())
        if month:
            return _valid(int(m.group(3)), month, int(m.group(1)))
    # Mon DD YYYY
    m = re.fullmatch(rf"([A-Za-z]+){sep}(\d{{1,2}}){sep}(\d{{4}})", s)
    if m:
        month = MONTH_NAMES.get(m.group(1).lower())
        if month:
            return _valid(int(m.group(3)), month, int(m.group(2)))
    # YYYY Mon DD
    m = re.fullmatch(rf"(\d{{4}}){sep}([A-Za-z]+){sep}(\d{{1,2}})", s)
    if m:
        month = MONTH_NAMES.get(m.group(2).lower())
        if month:
            return _valid(int(m.group(1)), month, int(m.group(3)))
    return None
