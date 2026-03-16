"""Read and write XMP sidecar files.

Creates a minimal sidecar if none exists; updates xmp:CreateDate if one does.
The xpacket processing instructions (<?xpacket ...?>) are preserved on update.
"""

from __future__ import annotations

import re
from pathlib import Path

from lxml import etree

XMP_NS = "adobe:ns:meta/"
RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
XMP_BASIC_NS = "http://ns.adobe.com/xap/1.0/"

_XPACKET_BEGIN = '<?xpacket begin="\xef\xbb\xbf" id="W5M0MpCehiHzreSzNTczkc9d"?>'
_XPACKET_END = '<?xpacket end="w"?>'

_XMP_TEMPLATE = (
    '{begin}\n'
    '<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="NeatXMP">\n'
    ' <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
    '  <rdf:Description rdf:about=""\n'
    '    xmlns:xmp="http://ns.adobe.com/xap/1.0/"\n'
    '    xmp:CreateDate="{date}"/>\n'
    ' </rdf:RDF>\n'
    '</x:xmpmeta>\n'
    '{end}\n'
)


def apply_date_to_xmp(media_path: Path, date_str: str) -> None:
    """Create or update the .xmp sidecar for *media_path*, setting xmp:CreateDate."""
    xmp_path = media_path.with_suffix(".xmp")
    if xmp_path.exists():
        _update_xmp(xmp_path, date_str)
    else:
        _create_xmp(xmp_path, date_str)


def _create_xmp(xmp_path: Path, date_str: str) -> None:
    content = _XMP_TEMPLATE.format(
        begin=_XPACKET_BEGIN,
        end=_XPACKET_END,
        date=date_str,
    )
    xmp_path.write_text(content, encoding="utf-8")


def _update_xmp(xmp_path: Path, date_str: str) -> None:
    content = xmp_path.read_text(encoding="utf-8")

    # xpacket PIs live outside the root element and are not valid XML.
    # Strip them before parsing, then re-add after serializing.
    header_lines: list[str] = []
    footer_lines: list[str] = []
    body_lines: list[str] = []
    in_body = False
    body_done = False

    for line in content.splitlines(keepends=True):
        stripped = line.strip()
        if not in_body and re.match(r"<\?xpacket\s+begin", stripped):
            header_lines.append(line)
        elif in_body and not body_done and re.match(r"<\?xpacket\s+end", stripped):
            footer_lines.append(line)
            body_done = True
        elif body_done:
            footer_lines.append(line)
        else:
            in_body = True
            body_lines.append(line)

    xml_content = "".join(body_lines).strip()
    if not xml_content:
        _create_xmp(xmp_path, date_str)
        return

    try:
        root = etree.fromstring(xml_content.encode("utf-8"))
    except etree.XMLSyntaxError:
        _create_xmp(xmp_path, date_str)
        return

    desc = root.find(f".//{{{RDF_NS}}}Description")
    if desc is None:
        _create_xmp(xmp_path, date_str)
        return

    create_date_key = f"{{{XMP_BASIC_NS}}}CreateDate"

    if XMP_BASIC_NS in desc.nsmap.values():
        # Namespace already declared on this element or an ancestor — lxml will
        # use the correct prefix when serializing.
        desc.set(create_date_key, date_str)
    else:
        # Rebuild the Description element with the xmp namespace added so that
        # lxml doesn't auto-generate a prefix like ns0:.
        new_nsmap = {**desc.nsmap, "xmp": XMP_BASIC_NS}
        new_desc = etree.Element(desc.tag, nsmap=new_nsmap)
        new_desc.text = desc.text
        new_desc.tail = desc.tail
        for k, v in desc.attrib.items():
            new_desc.set(k, v)
        for child in desc:
            new_desc.append(child)
        new_desc.set(create_date_key, date_str)
        parent = desc.getparent()
        if parent is not None:
            idx = list(parent).index(desc)
            parent.remove(desc)
            parent.insert(idx, new_desc)

    xml_str = etree.tostring(root, pretty_print=True, encoding="unicode", xml_declaration=False)

    header = "".join(header_lines) or (_XPACKET_BEGIN + "\n")
    footer = "".join(footer_lines) or (_XPACKET_END + "\n")
    xmp_path.write_text(header + xml_str + footer, encoding="utf-8")
