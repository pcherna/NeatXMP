"""Read fields from an XMP sidecar file."""

from __future__ import annotations

import re
from pathlib import Path

from lxml import etree

RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"

# All known XMP date fields: Clark-notation key -> human label
_DATE_FIELDS: dict[str, str] = {
    "{http://ns.adobe.com/xap/1.0/}CreateDate":         "xmp:CreateDate",
    "{http://ns.adobe.com/xap/1.0/}ModifyDate":         "xmp:ModifyDate",
    "{http://ns.adobe.com/xap/1.0/}MetadataDate":       "xmp:MetadataDate",
    "{http://ns.adobe.com/photoshop/1.0/}DateCreated":  "photoshop:DateCreated",
    "{http://ns.adobe.com/exif/1.0/}DateTimeOriginal":  "exif:DateTimeOriginal",
    "{http://ns.adobe.com/exif/1.0/}DateTimeDigitized": "exif:DateTimeDigitized",
    "{http://purl.org/dc/elements/1.1/}date":           "dc:date",
}

# Well-known namespace URIs -> preferred prefix
_KNOWN_NS: dict[str, str] = {
    "http://ns.adobe.com/xap/1.0/":                       "xmp",
    "http://ns.adobe.com/xap/1.0/rights/":                "xmpRights",
    "http://ns.adobe.com/xap/1.0/mm/":                    "xmpMM",
    "http://ns.adobe.com/xap/1.0/bj/":                    "xmpBJ",
    "http://ns.adobe.com/xap/1.0/t/pg/":                  "xmpTPg",
    "http://ns.adobe.com/photoshop/1.0/":                  "photoshop",
    "http://ns.adobe.com/camera-raw-settings/1.0/":        "crs",
    "http://ns.adobe.com/lightroom/1.0/":                  "lr",
    "http://ns.adobe.com/exif/1.0/":                       "exif",
    "http://ns.adobe.com/tiff/1.0/":                       "tiff",
    "http://purl.org/dc/elements/1.1/":                    "dc",
    "http://iptc.org/std/Iptc4xmpCore/1.0/xmlns/":         "Iptc4xmpCore",
    "http://iptc.org/std/Iptc4xmpExt/2008-02-29/":         "Iptc4xmpExt",
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#":         "rdf",
    "adobe:ns:meta/":                                       "x",
}

# Attributes that carry no user-visible information
_SKIP_ATTRS = {
    f"{{{RDF_NS}}}about",
}


def _parse_xml(xmp_path: Path) -> etree._Element | None:
    """Read and parse an XMP file, stripping xpacket PIs. Returns root or None."""
    try:
        content = xmp_path.read_text(encoding="utf-8")
    except OSError:
        return None

    lines = [
        l for l in content.splitlines(keepends=True)
        if not re.match(r"\s*<\?xpacket", l.strip())
    ]
    xml_content = "".join(lines).strip()
    if not xml_content:
        return None

    try:
        return etree.fromstring(xml_content.encode("utf-8"))
    except etree.XMLSyntaxError:
        return None


def _clark_to_label(clark: str) -> str:
    """'{http://ns.adobe.com/xap/1.0/}CreateDate' -> 'xmp:CreateDate'"""
    m = re.fullmatch(r"\{([^}]+)\}(.*)", clark)
    if m:
        ns_uri, local = m.groups()
        prefix = _KNOWN_NS.get(ns_uri)
        if prefix:
            return f"{prefix}:{local}"
        # Unknown namespace — show verbatim Clark notation
        return clark
    return clark


def _element_value(elem: etree._Element) -> str:
    """Extract a human-readable value from an XMP element (handles bags/seqs/alts)."""
    # rdf:Seq / rdf:Bag / rdf:Alt -> semicolon-joined list
    for container_tag in ("Seq", "Bag", "Alt"):
        container = elem.find(f"{{{RDF_NS}}}{container_tag}")
        if container is not None:
            items = [
                (li.text or "").strip()
                for li in container.findall(f"{{{RDF_NS}}}li")
            ]
            return "; ".join(i for i in items if i)

    # Simple text
    if elem.text and elem.text.strip():
        return elem.text.strip()

    # Structured value — serialize compactly
    return etree.tostring(elem, encoding="unicode").strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def read_xmp_dates(xmp_path: Path) -> dict[str, str]:
    """Return {label: value} for every date field found in the sidecar."""
    root = _parse_xml(xmp_path)
    if root is None:
        return {}

    result: dict[str, str] = {}
    for desc in root.iter(f"{{{RDF_NS}}}Description"):
        for clark_key, label in _DATE_FIELDS.items():
            if clark_key in desc.attrib and label not in result:
                result[label] = desc.attrib[clark_key]
    return result


def read_all_xmp_fields(xmp_path: Path) -> list[tuple[str, str]]:
    """Return all XMP fields as (label, value) pairs, in document order.

    Well-known namespaces are shown with their conventional prefix (e.g.
    'xmp:CreateDate').  Unknown namespaces are shown verbatim in Clark
    notation (e.g. '{http://example.com/}field').
    """
    root = _parse_xml(xmp_path)
    if root is None:
        return []

    results: list[tuple[str, str]] = []
    seen: set[str] = set()

    for desc in root.iter(f"{{{RDF_NS}}}Description"):
        # Simple values stored as attributes
        for clark_key, value in desc.attrib.items():
            if clark_key in _SKIP_ATTRS:
                continue
            label = _clark_to_label(clark_key)
            if label not in seen:
                results.append((label, value))
                seen.add(label)

        # Complex values stored as child elements
        for child in desc:
            label = _clark_to_label(child.tag)
            if label not in seen:
                results.append((label, _element_value(child)))
                seen.add(label)

    return results
