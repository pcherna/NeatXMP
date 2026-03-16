"""Tests for xmp_writer.py

Covers:
- Creating a new sidecar file
- Updating an existing sidecar (attribute already present)
- Adding xmp:CreateDate to an existing sidecar that lacks it
- Updating a sidecar where xmp namespace is not yet declared
- xpacket processing instructions are preserved
- Malformed XML falls back to a fresh create
- Month-only (YYYY-MM) and full (YYYY-MM-DD) date strings
- Works for all supported media extensions
"""

import pytest
from pathlib import Path
from lxml import etree

from neatxmp.xmp_writer import apply_date_to_xmp

XMP_NS        = "adobe:ns:meta/"
RDF_NS        = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
XMP_BASIC_NS  = "http://ns.adobe.com/xap/1.0/"
PHOTOSHOP_NS  = "http://ns.adobe.com/photoshop/1.0/"


def _parse_desc(xmp_path: Path):
    import re
    content = xmp_path.read_text(encoding="utf-8")
    lines = [l for l in content.splitlines(keepends=True)
             if not re.match(r"\s*<\?xpacket", l.strip())]
    root = etree.fromstring("".join(lines).strip().encode("utf-8"))
    desc = root.find(f".//{{{RDF_NS}}}Description")
    assert desc is not None, "rdf:Description not found"
    return desc


def _read_create_date(xmp_path: Path) -> str:
    desc = _parse_desc(xmp_path)
    key = f"{{{XMP_BASIC_NS}}}CreateDate"
    assert key in desc.attrib, f"xmp:CreateDate not found in {dict(desc.attrib)}"
    return desc.attrib[key]


def _read_photoshop_date(xmp_path: Path) -> str:
    desc = _parse_desc(xmp_path)
    key = f"{{{PHOTOSHOP_NS}}}DateCreated"
    assert key in desc.attrib, f"photoshop:DateCreated not found in {dict(desc.attrib)}"
    return desc.attrib[key]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_img(tmp_path) -> Path:
    img = tmp_path / "photo.jpg"
    img.touch()
    return img


@pytest.fixture
def xmp_with_date(tmp_path) -> Path:
    """A .xmp sidecar that already has xmp:CreateDate."""
    xmp = tmp_path / "photo.xmp"
    xmp.write_text(
        '<?xpacket begin="\xef\xbb\xbf" id="W5M0MpCehiHzreSzNTczkc9d"?>\n'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="NeatXMP">\n'
        ' <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
        '  <rdf:Description rdf:about=""\n'
        '    xmlns:xmp="http://ns.adobe.com/xap/1.0/"\n'
        '    xmp:CreateDate="2000-01-01"/>\n'
        ' </rdf:RDF>\n'
        '</x:xmpmeta>\n'
        '<?xpacket end="w"?>\n',
        encoding="utf-8",
    )
    img = tmp_path / "photo.jpg"
    img.touch()
    return img


@pytest.fixture
def xmp_without_create_date(tmp_path) -> Path:
    """A .xmp sidecar that has the xmp namespace but no CreateDate attribute."""
    xmp = tmp_path / "photo.xmp"
    xmp.write_text(
        '<?xpacket begin="\xef\xbb\xbf" id="W5M0MpCehiHzreSzNTczkc9d"?>\n'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">\n'
        ' <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
        '  <rdf:Description rdf:about=""\n'
        '    xmlns:xmp="http://ns.adobe.com/xap/1.0/"\n'
        '    xmp:Rating="5"/>\n'
        ' </rdf:RDF>\n'
        '</x:xmpmeta>\n'
        '<?xpacket end="w"?>\n',
        encoding="utf-8",
    )
    img = tmp_path / "photo.jpg"
    img.touch()
    return img


@pytest.fixture
def xmp_without_xmp_namespace(tmp_path) -> Path:
    """A .xmp sidecar that has no xmp namespace declaration at all."""
    xmp = tmp_path / "photo.xmp"
    xmp.write_text(
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">\n'
        ' <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
        '  <rdf:Description rdf:about=""\n'
        '    xmlns:dc="http://purl.org/dc/elements/1.1/"\n'
        '    dc:description="some photo"/>\n'
        ' </rdf:RDF>\n'
        '</x:xmpmeta>\n',
        encoding="utf-8",
    )
    img = tmp_path / "photo.jpg"
    img.touch()
    return img


# ---------------------------------------------------------------------------
# Creating new sidecars
# ---------------------------------------------------------------------------

class TestCreateNewSidecar:
    def test_creates_xmp_file(self, tmp_img):
        apply_date_to_xmp(tmp_img, "2018-11")
        assert tmp_img.with_suffix(".xmp").exists()

    def test_month_only_date(self, tmp_img):
        apply_date_to_xmp(tmp_img, "2018-11")
        assert _read_create_date(tmp_img.with_suffix(".xmp")) == "2018-11"

    def test_full_date(self, tmp_img):
        apply_date_to_xmp(tmp_img, "2018-11-01")
        assert _read_create_date(tmp_img.with_suffix(".xmp")) == "2018-11-01"

    def test_xpacket_present(self, tmp_img):
        apply_date_to_xmp(tmp_img, "2018-11")
        content = tmp_img.with_suffix(".xmp").read_text()
        assert "<?xpacket" in content

    def test_xpacket_begin_and_end(self, tmp_img):
        apply_date_to_xmp(tmp_img, "2018-11")
        content = tmp_img.with_suffix(".xmp").read_text()
        assert "begin=" in content
        assert 'end="w"' in content

    def test_photoshop_date_created(self, tmp_img):
        apply_date_to_xmp(tmp_img, "2018-11")
        assert _read_photoshop_date(tmp_img.with_suffix(".xmp")) == "2018-11"

    def test_both_date_fields_match(self, tmp_img):
        apply_date_to_xmp(tmp_img, "2018-11-01")
        xmp = tmp_img.with_suffix(".xmp")
        assert _read_create_date(xmp) == _read_photoshop_date(xmp)

    def test_utf8_encoding(self, tmp_img):
        apply_date_to_xmp(tmp_img, "2018-11")
        raw = tmp_img.with_suffix(".xmp").read_bytes()
        raw.decode("utf-8")  # should not raise

    @pytest.mark.parametrize("ext", [".jpg", ".jpeg", ".png", ".heic", ".mp4", ".mov"])
    def test_all_media_extensions(self, tmp_path, ext):
        media = tmp_path / f"file{ext}"
        media.touch()
        apply_date_to_xmp(media, "2018-11")
        assert (tmp_path / f"file.xmp").exists()


# ---------------------------------------------------------------------------
# Updating existing sidecars
# ---------------------------------------------------------------------------

class TestUpdateExistingSidecar:
    def test_overwrites_existing_date(self, xmp_with_date):
        apply_date_to_xmp(xmp_with_date, "2018-11")
        assert _read_create_date(xmp_with_date.with_suffix(".xmp")) == "2018-11"

    def test_old_date_not_present(self, xmp_with_date):
        apply_date_to_xmp(xmp_with_date, "2018-11")
        content = xmp_with_date.with_suffix(".xmp").read_text()
        assert "2000-01-01" not in content

    def test_xpacket_preserved_on_update(self, xmp_with_date):
        apply_date_to_xmp(xmp_with_date, "2018-11")
        content = xmp_with_date.with_suffix(".xmp").read_text()
        assert "<?xpacket" in content
        assert 'end="w"' in content

    def test_update_to_full_date(self, xmp_with_date):
        apply_date_to_xmp(xmp_with_date, "2018-11-25")
        assert _read_create_date(xmp_with_date.with_suffix(".xmp")) == "2018-11-25"

    def test_adds_missing_create_date(self, xmp_without_create_date):
        apply_date_to_xmp(xmp_without_create_date, "2018-11")
        assert _read_create_date(xmp_without_create_date.with_suffix(".xmp")) == "2018-11"

    def test_preserves_other_attributes(self, xmp_without_create_date):
        apply_date_to_xmp(xmp_without_create_date, "2018-11")
        content = xmp_without_create_date.with_suffix(".xmp").read_text()
        assert 'xmp:Rating="5"' in content or "Rating" in content

    def test_no_xmp_namespace_declared(self, xmp_without_xmp_namespace):
        apply_date_to_xmp(xmp_without_xmp_namespace, "2018-11")
        assert _read_create_date(xmp_without_xmp_namespace.with_suffix(".xmp")) == "2018-11"

    def test_photoshop_date_updated(self, xmp_with_date):
        apply_date_to_xmp(xmp_with_date, "2018-11")
        assert _read_photoshop_date(xmp_with_date.with_suffix(".xmp")) == "2018-11"

    def test_backup_created_on_update(self, xmp_with_date):
        apply_date_to_xmp(xmp_with_date, "2018-11")
        assert xmp_with_date.with_suffix(".xmp_bak").exists()

    def test_backup_contains_original_content(self, xmp_with_date):
        apply_date_to_xmp(xmp_with_date, "2018-11")
        bak = xmp_with_date.with_suffix(".xmp_bak").read_text()
        assert "2000-01-01" in bak

    def test_backup_overwritten_on_second_update(self, xmp_with_date):
        apply_date_to_xmp(xmp_with_date, "2018-11")
        apply_date_to_xmp(xmp_with_date, "2019-06")
        bak = xmp_with_date.with_suffix(".xmp_bak").read_text()
        # Backup should reflect the state before the second update (2018-11)
        assert "2018-11" in bak
        assert "2000-01-01" not in bak

    def test_no_backup_on_create(self, tmp_img):
        apply_date_to_xmp(tmp_img, "2018-11")
        assert not tmp_img.with_suffix(".xmp_bak").exists()

    def test_update_multiple_times(self, xmp_with_date):
        apply_date_to_xmp(xmp_with_date, "2018-11")
        apply_date_to_xmp(xmp_with_date, "2019-06-15")
        assert _read_create_date(xmp_with_date.with_suffix(".xmp")) == "2019-06-15"


# ---------------------------------------------------------------------------
# Malformed / edge-case existing files
# ---------------------------------------------------------------------------

class TestMalformedXmp:
    def test_empty_xmp_file(self, tmp_path):
        img = tmp_path / "photo.jpg"
        img.touch()
        xmp = tmp_path / "photo.xmp"
        xmp.write_text("", encoding="utf-8")
        apply_date_to_xmp(img, "2018-11")
        assert _read_create_date(xmp) == "2018-11"

    def test_corrupt_xml(self, tmp_path):
        img = tmp_path / "photo.jpg"
        img.touch()
        xmp = tmp_path / "photo.xmp"
        xmp.write_text("<<not valid xml>>", encoding="utf-8")
        apply_date_to_xmp(img, "2018-11")
        assert _read_create_date(xmp) == "2018-11"

    def test_xmp_with_only_xpacket_pis(self, tmp_path):
        img = tmp_path / "photo.jpg"
        img.touch()
        xmp = tmp_path / "photo.xmp"
        xmp.write_text(
            '<?xpacket begin="\xef\xbb\xbf" id="W5M0MpCehiHzreSzNTczkc9d"?>\n'
            '<?xpacket end="w"?>\n',
            encoding="utf-8",
        )
        apply_date_to_xmp(img, "2018-11")
        assert _read_create_date(xmp) == "2018-11"
