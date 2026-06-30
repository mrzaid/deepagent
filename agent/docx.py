"""Minimal, dependency-free .docx writer.

A .docx is just a ZIP of a few XML parts, so we build one with the standard
library — no python-docx dependency. Enough to produce the attorney-review draft
file the paralegal skill specifies: paragraphs, bold headings, preserved
[BRACKETED PLACEHOLDERS], with the skill's annotation comments
(// NOTE, // ALT, // RISK) stripped.
"""
from __future__ import annotations

import io
import re
import zipfile
from xml.sax.saxutils import escape

_ANNOT = re.compile(r"//\s*(NOTE|ALT|RISK)\b.*$", re.IGNORECASE)
_DISCLAIMER = "This document is a draft for attorney review only and does not constitute legal advice."

_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""


def strip_annotations(text: str) -> str:
    """Remove // NOTE / // ALT / // RISK annotations; drop lines that were only
    annotations. Bracketed placeholders are left untouched."""
    out = []
    for line in text.split("\n"):
        cleaned = _ANNOT.sub("", line).rstrip()
        if cleaned.strip() == "" and line.strip() != "":
            continue  # the line was purely an annotation
        out.append(cleaned)
    return "\n".join(out)


def _para(text: str, bold: bool = False) -> str:
    if not text.strip():
        return "<w:p/>"
    rpr = "<w:rPr><w:b/></w:rPr>" if bold else ""
    return (f"<w:p><w:r>{rpr}"
            f'<w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>')


def _markdown_to_paragraphs(md: str) -> list[str]:
    paras = []
    for raw in md.split("\n"):
        line = raw.rstrip()
        if line.startswith("### "):
            paras.append(_para(line[4:], bold=True))
        elif line.startswith("## "):
            paras.append(_para(line[3:], bold=True))
        elif line.startswith("# "):
            paras.append(_para(line[2:], bold=True))
        elif line.startswith(("- ", "* ")):
            paras.append(_para("• " + line[2:]))
        else:
            paras.append(_para(line))
    return paras


def build_docx_bytes(title: str, body_md: str) -> bytes:
    body_md = strip_annotations(body_md)
    if _DISCLAIMER.lower() not in body_md.lower():
        body_md = _DISCLAIMER + "\n\n" + body_md

    paras = [_para(title, bold=True), "<w:p/>"] + _markdown_to_paragraphs(body_md)
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>" + "".join(paras) + "<w:sectPr/></w:body></w:document>"
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CONTENT_TYPES)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("word/document.xml", document)
    return buf.getvalue()


def write_docx(path, title: str, body_md: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(build_docx_bytes(title, body_md))
