"""Markdown to DOCX conversion for stage 4.3.

Uses markdown + beautifulsoup4 to parse Markdown, then python-docx to build the document.
Handles # ## ### headings, - lists, paragraphs, **bold**, *italic*, tables (optional).
"""
import markdown
from bs4 import BeautifulSoup
from docx import Document


def _add_inline_to_paragraph(p, elem) -> None:
    """Add inline content (bold, italic, etc) from elem to paragraph p."""
    for child in elem:
        if hasattr(child, "name") and child.name:
            if child.name in ("strong", "b"):
                r = p.add_run(child.get_text())
                r.bold = True
            elif child.name in ("em", "i"):
                r = p.add_run(child.get_text())
                r.italic = True
            elif child.name == "code":
                p.add_run(child.get_text())
            elif child.name == "br":
                p.add_run("\n")
            else:
                p.add_run(child.get_text() if hasattr(child, "get_text") else str(child))
        elif isinstance(child, str) or (hasattr(child, "name") and child.name is None):
            txt = str(child) if child else ""
            if txt:
                p.add_run(txt)


def markdown_to_docx(markdown_text: str) -> Document:
    """Convert Markdown string to python-docx Document.

    Handles # ## ### headings, - lists, paragraphs, **bold**, *italic*, tables.
    Returns a Document instance (call .save() to write to file).
    """
    if not markdown_text or not markdown_text.strip():
        doc = Document()
        doc.add_paragraph("（无内容）")
        return doc

    html = markdown.markdown(
        markdown_text,
        extensions=["tables", "fenced_code", "nl2br"],
    )
    soup = BeautifulSoup(html, "html.parser")

    doc = Document()
    root = soup.find("body") or soup

    for elem in root.children:
        if not hasattr(elem, "name"):
            continue
        if elem.name is None:
            continue
        if elem.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(elem.name[1])
            doc.add_heading(elem.get_text(strip=True), level=level)
        elif elem.name == "p":
            text = elem.get_text(strip=True)
            if text:
                p = doc.add_paragraph()
                _add_inline_to_paragraph(p, elem)
            else:
                doc.add_paragraph()
        elif elem.name in ("ul", "ol"):
            list_style = "List Bullet" if elem.name == "ul" else "List Number"
            for li in elem.find_all("li", recursive=False):
                text = li.get_text(strip=True)
                if text:
                    p = doc.add_paragraph(style=list_style)
                    _add_inline_to_paragraph(p, li)
                else:
                    doc.add_paragraph(style=list_style)
        elif elem.name == "table":
            rows = elem.find_all("tr")
            if rows:
                cell_texts = []
                for tr in rows:
                    cells = tr.find_all(["th", "td"])
                    cell_texts.append([c.get_text(strip=True) for c in cells])
                if cell_texts:
                    max_cols = max(len(r) for r in cell_texts)
                    for r in cell_texts:
                        while len(r) < max_cols:
                            r.append("")
                    table = doc.add_table(rows=len(cell_texts), cols=max_cols)
                    table.style = "Table Grid"
                    for i, row_texts in enumerate(cell_texts):
                        for j, text in enumerate(row_texts):
                            table.rows[i].cells[j].text = text
        elif elem.name == "hr":
            doc.add_paragraph()
        elif elem.name == "pre":
            doc.add_paragraph(elem.get_text())
        elif elem.name == "div":
            for sub in elem.children:
                if hasattr(sub, "name") and sub.name:
                    if sub.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
                        level = int(sub.name[1])
                        doc.add_heading(sub.get_text(strip=True), level=level)
                    elif sub.name == "p":
                        text = sub.get_text(strip=True)
                        if text:
                            p = doc.add_paragraph()
                            _add_inline_to_paragraph(p, sub)
                        else:
                            doc.add_paragraph()
                    elif sub.name in ("ul", "ol"):
                        list_style = "List Bullet" if sub.name == "ul" else "List Number"
                        for li in sub.find_all("li", recursive=False):
                            doc.add_paragraph(li.get_text(strip=True), style=list_style)

    return doc
