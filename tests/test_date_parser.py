"""Tests for date_parser.py

Covers:
- All documented date formats (full-match parse_date)
- Embedded date extraction (find_date_in_name)
- format_xmp_date output
- Invalid / unparseable inputs
- Edge cases (boundary dates, month/day limits, leap years)
"""

import pytest
from neatxmp.date_parser import find_date_in_name, format_xmp_date, parse_date


# ---------------------------------------------------------------------------
# format_xmp_date
# ---------------------------------------------------------------------------

class TestFormatXmpDate:
    def test_month_only(self):
        assert format_xmp_date((2018, 11, None)) == "2018-11"

    def test_full_date(self):
        assert format_xmp_date((2018, 11, 1)) == "2018-11-01"

    def test_zero_padded_month(self):
        assert format_xmp_date((2018, 3, None)) == "2018-03"

    def test_zero_padded_day(self):
        assert format_xmp_date((2018, 3, 5)) == "2018-03-05"

    def test_four_digit_year(self):
        assert format_xmp_date((988, 3, 5)) == "0988-03-05"


# ---------------------------------------------------------------------------
# parse_date — named month + year
# ---------------------------------------------------------------------------

class TestNamedMonthYear:
    @pytest.mark.parametrize("name", [
        "Nov 2018",
        "nov 2018",
        "NOV 2018",
    ])
    def test_short_name_space(self, name):
        assert parse_date(name) == (2018, 11, None)

    @pytest.mark.parametrize("name", [
        "November 2018",
        "november 2018",
        "NOVEMBER 2018",
    ])
    def test_full_name_space(self, name):
        assert parse_date(name) == (2018, 11, None)

    def test_year_first_space(self):
        assert parse_date("2018 Nov") == (2018, 11, None)

    def test_year_first_full_name(self):
        assert parse_date("2018 November") == (2018, 11, None)

    def test_hyphen_separator(self):
        assert parse_date("2018-Nov") == (2018, 11, None)

    def test_underscore_separator(self):
        assert parse_date("2018_Nov") == (2018, 11, None)

    @pytest.mark.parametrize("name, expected_month", [
        ("Jan 2020", 1),
        ("February 2020", 2),
        ("Mar 2020", 3),
        ("April 2020", 4),
        ("May 2020", 5),
        ("Jun 2020", 6),
        ("July 2020", 7),
        ("Aug 2020", 8),
        ("Sep 2020", 9),
        ("Sept 2020", 9),
        ("October 2020", 10),
        ("Nov 2020", 11),
        ("December 2020", 12),
    ])
    def test_all_month_names(self, name, expected_month):
        assert parse_date(name) == (2020, expected_month, None)


# ---------------------------------------------------------------------------
# parse_date — numeric with separator, two parts
# ---------------------------------------------------------------------------

class TestNumericTwoParts:
    def test_mm_yyyy_hyphen(self):
        assert parse_date("11-2018") == (2018, 11, None)

    def test_yyyy_mm_hyphen(self):
        assert parse_date("2018-11") == (2018, 11, None)

    def test_mm_yyyy_slash(self):
        assert parse_date("11/2018") == (2018, 11, None)

    def test_yyyy_mm_dot(self):
        assert parse_date("2018.11") == (2018, 11, None)

    def test_single_digit_month(self):
        assert parse_date("3-2018") == (2018, 3, None)


# ---------------------------------------------------------------------------
# parse_date — numeric with separator, three parts
# ---------------------------------------------------------------------------

class TestNumericThreeParts:
    def test_yyyy_mm_dd(self):
        assert parse_date("2018-11-01") == (2018, 11, 1)

    def test_dd_mm_yyyy(self):
        assert parse_date("01-11-2018") == (2018, 11, 1)

    def test_slash_separator(self):
        assert parse_date("01/11/2018") == (2018, 11, 1)

    def test_dot_separator(self):
        assert parse_date("2018.11.01") == (2018, 11, 1)

    def test_ambiguous_prefers_dd_mm(self):
        # 05-03-2018: could be May 3 or March 5; defaults to DD-MM-YYYY → March 5
        assert parse_date("05-03-2018") == (2018, 3, 5)

    def test_unambiguous_day_gt_12(self):
        # 25-03-2018: day=25 > 12, so must be DD-MM-YYYY
        assert parse_date("25-03-2018") == (2018, 3, 25)


# ---------------------------------------------------------------------------
# parse_date — compact 6-digit
# ---------------------------------------------------------------------------

class TestSixDigits:
    def test_yyyymm(self):
        assert parse_date("201811") == (2018, 11, None)

    def test_mmyyyy(self):
        assert parse_date("112018") == (2018, 11, None)

    def test_yyyymm_january(self):
        assert parse_date("202001") == (2020, 1, None)

    def test_mmyyyy_january(self):
        # 012020 → MMYYYY since 0120 is not a valid year-month (month 20 invalid)
        assert parse_date("012020") == (2020, 1, None)


# ---------------------------------------------------------------------------
# parse_date — compact 8-digit
# ---------------------------------------------------------------------------

class TestEightDigits:
    def test_yyyymmdd(self):
        assert parse_date("20181101") == (2018, 11, 1)

    def test_ddmmyyyy(self):
        assert parse_date("01112018") == (2018, 11, 1)

    def test_yyyymmdd_first_of_month(self):
        assert parse_date("19880325") == (1988, 3, 25)

    def test_ddmmyyyy_day_gt_12(self):
        # 25031988 → DDMMYYYY since 2503 as YYYYMM has month=03 but year=2503 is out of range
        assert parse_date("25031988") == (1988, 3, 25)


# ---------------------------------------------------------------------------
# parse_date — compact no-separator with named month
# ---------------------------------------------------------------------------

class TestCompactNamedMonth:
    def test_dd_mon_yyyy(self):
        assert parse_date("11Nov2018") == (2018, 11, 11)

    def test_dd_fullname_yyyy(self):
        assert parse_date("11November2018") == (2018, 11, 11)

    def test_mon_dd_yyyy(self):
        assert parse_date("Nov112018") == (2018, 11, 11)

    def test_yyyy_mon_dd(self):
        assert parse_date("2018Nov11") == (2018, 11, 11)

    def test_dd_mon_yyyy_march(self):
        assert parse_date("25Mar1988") == (1988, 3, 25)

    def test_single_digit_day(self):
        assert parse_date("5Jan2000") == (2000, 1, 5)


# ---------------------------------------------------------------------------
# parse_date — named month with day and separator
# ---------------------------------------------------------------------------

class TestDayNamedMonthYear:
    def test_dd_mon_yyyy_hyphen(self):
        assert parse_date("01-Nov-2018") == (2018, 11, 1)

    def test_dd_fullname_yyyy_hyphen(self):
        assert parse_date("01-November-2018") == (2018, 11, 1)

    def test_mon_dd_yyyy_hyphen(self):
        assert parse_date("Nov-01-2018") == (2018, 11, 1)

    def test_dd_mon_yyyy_space(self):
        assert parse_date("01 November 2018") == (2018, 11, 1)

    def test_yyyy_mon_dd_space(self):
        assert parse_date("2018 Nov 01") == (2018, 11, 1)


# ---------------------------------------------------------------------------
# find_date_in_name — embedded extraction
# ---------------------------------------------------------------------------

class TestFindDateInName:
    def test_yyyymmdd_in_camera_filename(self):
        assert find_date_in_name("IMG_20181101_123456") == (2018, 11, 1)

    def test_compact_named_at_start(self):
        assert find_date_in_name("25Mar1988 Plumbers Ball copy") == (1988, 3, 25)

    def test_compact_named_with_trailing_text(self):
        assert find_date_in_name("11Nov2018 family dinner") == (2018, 11, 11)

    def test_named_month_year_with_trailing_text(self):
        assert find_date_in_name("Nov 2018 - Hawaii") == (2018, 11, None)

    def test_named_month_year_with_leading_text(self):
        assert find_date_in_name("Holiday Nov 2018") == (2018, 11, None)

    def test_yyyy_mm_dd_with_trailing_text(self):
        assert find_date_in_name("2018-11-01 birthday party") == (2018, 11, 1)

    def test_full_match_still_works(self):
        assert find_date_in_name("Nov 2018") == (2018, 11, None)

    def test_yyyymmdd_embedded_in_longer_number_string_ignored(self):
        # 9-digit number should not match as YYYYMMDD
        assert find_date_in_name("123456789") is None

    def test_video_filename_pattern(self):
        assert find_date_in_name("VID_20181101_120000") == (2018, 11, 1)


# ---------------------------------------------------------------------------
# Invalid / unparseable inputs
# ---------------------------------------------------------------------------

class TestInvalidInputs:
    @pytest.mark.parametrize("name", [
        "",
        "   ",
        "hello world",
        "abc",
        "12345",        # 5 digits — not a valid pattern
        "1234567",      # 7 digits
        "123456789",    # 9 digits
        "Xyz 2018",     # not a month name
        "13-2018",      # month 13 invalid
        "00-2018",      # month 0 invalid
        "2018-13",      # month 13 invalid
        "32-01-2018",   # day 32 invalid
        "2018-02-30",   # Feb 30 doesn't exist
        "99991301",     # month 13 in compact form
    ])
    def test_returns_none(self, name):
        assert parse_date(name) is None

    def test_find_date_returns_none_for_gibberish(self):
        assert find_date_in_name("no date here at all") is None


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_leap_day(self):
        assert parse_date("29-02-2000") == (2000, 2, 29)

    def test_non_leap_day_invalid(self):
        assert parse_date("29-02-2001") is None

    def test_end_of_month(self):
        assert parse_date("31-01-2018") == (2018, 1, 31)

    def test_day_31_in_30_day_month(self):
        assert parse_date("31-04-2018") is None  # April has 30 days

    def test_year_boundary_low(self):
        assert parse_date("Jan 1900") == (1900, 1, None)

    def test_year_boundary_high(self):
        assert parse_date("Jan 2100") == (2100, 1, None)

    def test_year_out_of_range_low(self):
        assert parse_date("Jan 1899") is None

    def test_year_out_of_range_high(self):
        assert parse_date("Jan 2101") is None

    def test_extra_whitespace_trimmed(self):
        assert parse_date("  Nov 2018  ") == (2018, 11, None)
