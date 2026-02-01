"""Document parsing: PDF and DOCX to plain text."""
from pathlib import Path


def parse_document(file_path: str | Path) -> str:
    """Extract plain text from a PDF or DOCX file.

    Args:
        file_path: Absolute path to the file.

    Returns:
        Extracted text (may be empty string).

    Raises:
        FileNotFoundError: File does not exist.
        ValueError: Unsupported extension (e.g. .doc) or parse error.
        Other exceptions from PyMuPDF or python-docx are propagated.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _parse_pdf(path)
    if suffix == ".docx":
        return _parse_docx(path)
    if suffix == ".doc":
        raise ValueError("暂不支持 .doc，请使用 .docx 或 PDF")
    raise ValueError(f"Unsupported file type: {suffix}; use .pdf or .docx")


def _parse_pdf(path: Path) -> str:
    import fitz

    doc = fitz.open(path)
    try:
        parts = []
        for page in doc:
            parts.append(page.get_text())
        return "\n".join(parts)
    finally:
        doc.close()


def _parse_docx(path: Path) -> str:
    from docx import Document

    doc = Document(path)
    parts = [p.text for p in doc.paragraphs]
    return "\n".join(parts)
