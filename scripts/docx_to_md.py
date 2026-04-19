"""One-shot conversion of INVEX-SRS-v2.3.1.docx → Markdown.

Not a general tool; tuned for this document's structure (Heading 1/2/3 styles,
requirement blocks, tables, ordered/unordered lists).
"""

import re
import sys
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn


def iter_block_items(parent):
    """Yield paragraphs and tables in document order."""
    from docx.document import Document as _Document
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.table import _Cell, Table
    from docx.text.paragraph import Paragraph

    if isinstance(parent, _Document):
        parent_elm = parent.element.body
    elif isinstance(parent, _Cell):
        parent_elm = parent._tc
    else:
        raise ValueError("unsupported parent")

    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def render_runs(paragraph):
    """Render a paragraph's runs with basic bold/italic/code."""
    parts = []
    for run in paragraph.runs:
        text = run.text
        if not text:
            continue
        # Detect monospace via font name (best-effort)
        font_name = (run.font.name or "").lower()
        is_code = any(f in font_name for f in ("consolas", "courier", "mono"))
        if is_code:
            parts.append(f"`{text}`")
        elif run.bold and run.italic:
            parts.append(f"***{text}***")
        elif run.bold:
            parts.append(f"**{text}**")
        elif run.italic:
            parts.append(f"*{text}*")
        else:
            parts.append(text)
    return "".join(parts).strip()


def heading_level(style_name):
    """Map Word heading style name to Markdown heading level (int) or None."""
    if not style_name:
        return None
    m = re.match(r"Heading\s+(\d+)", style_name, re.IGNORECASE)
    if m:
        return int(m.group(1))
    if style_name.lower() == "title":
        return 1
    return None


def list_info(paragraph):
    """Return (is_list, is_numbered) for a paragraph.

    Word lists expose numId via w:numPr; we treat any such paragraph as a list
    item. Numbered vs bullet is detected via the style name.
    """
    pPr = paragraph._p.find(qn("w:pPr"))
    if pPr is None:
        return False, False
    numPr = pPr.find(qn("w:numPr"))
    if numPr is None:
        return False, False
    style = (paragraph.style.name or "").lower() if paragraph.style else ""
    is_numbered = "number" in style or "ordered" in style
    return True, is_numbered


def render_table(table):
    rows = []
    for row in table.rows:
        cells = [" ".join(p.text.strip() for p in cell.paragraphs).replace("\n", " ") for cell in row.cells]
        rows.append(cells)
    if not rows:
        return ""
    header = rows[0]
    body = rows[1:]
    out = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    for r in body:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def convert(docx_path: Path, md_path: Path):
    doc = Document(str(docx_path))
    out_lines = []
    prev_was_list = False

    for block in iter_block_items(doc):
        if block.__class__.__name__ == "Table":
            out_lines.append("")
            out_lines.append(render_table(block))
            out_lines.append("")
            prev_was_list = False
            continue

        # Paragraph
        para = block
        text = render_runs(para)
        style_name = para.style.name if para.style else ""
        level = heading_level(style_name)

        if level is not None:
            if not text:
                continue
            out_lines.append("")
            out_lines.append(f"{'#' * min(level, 6)} {text}")
            out_lines.append("")
            prev_was_list = False
            continue

        is_list, is_numbered = list_info(para)
        if is_list and text:
            marker = "1." if is_numbered else "-"
            out_lines.append(f"{marker} {text}")
            prev_was_list = True
            continue

        if not text:
            if not prev_was_list:
                out_lines.append("")
            prev_was_list = False
            continue

        if prev_was_list:
            out_lines.append("")
        out_lines.append(text)
        out_lines.append("")
        prev_was_list = False

    # Collapse >2 consecutive blank lines
    md = "\n".join(out_lines)
    md = re.sub(r"\n{3,}", "\n\n", md)
    md_path.write_text(md, encoding="utf-8")
    print(f"wrote {md_path} ({len(md)} chars, {md.count(chr(10))} lines)")


if __name__ == "__main__":
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    convert(src, dst)
