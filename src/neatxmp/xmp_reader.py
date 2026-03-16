"""Read date fields from an XMP sidecar file."""

from __future__ import annotations

import re
from pathlib import Path

from lxml import etree

RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"

# All known XMP date fields: Clark-notation key -> human label
_DATE_FIELDS: dict[str, str] = {
    "{http://ns.adobe.com/xap/1.0/}CreateDate":              "xmp:CreateDate",
    "{http://ns.adobe.com/xap/1.0/}ModifyDate":              "xmp:ModifyDate",
    "{http://ns.adobe.com/xap/1.0/}MetadataDate":            "xmp:MetadataDate",
    "{http://ns.adobe.com/photoshop/1.0/}DateCreated":       "photoshop:DateCreated",
    "{http://ns.adobe.com/exif/1.0/}DateTimeOriginal":       "exif:DateTimeOriginal",
    "{http://ns.adobe.com/exif/1.0/}DateTimeDigitized":      "exif:DateTimeDigitized",
    "{http://purl.org/dc/elements/1.1/}date":                "dc:date",
}


def read_xmp_dates(xmp_path: Path) -> dict[str, str]:
    """Return a dict of {label: value} for every date field found in the sidecar."""
    try:
        content = xmp_path.read_text(encoding="utf-8")
    except OSError:
        return {}

    # Strip xpacket PIs before parsing
    lines = [
        l for l in content.splitlines(keepends=True)
        if not re.match(r"\s*<\?xpacket", l.strip())
    ]
    xml_content = "".join(lines).strip()
    if not xml_content:
        return {}

    try:
        root = etree.fromstring(xml_content.encode("utf-8"))
    except etree.XMLSyntaxError:
        return {}

    result: dict[str, str] = {}
    for desc in root.iter(f"{{{RDF_NS}}}Description"):
        for clark_key, label in _DATE_FIELDS.items():
            if clark_key in desc.attrib and label not in result:
                result[label] = desc.attrib[clark_key]

    return result
