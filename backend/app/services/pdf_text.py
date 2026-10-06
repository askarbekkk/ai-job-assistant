"""Module 1a — PDF -> text (PyMuPDF). Text PDFs only; scanned images are rejected."""

import pymupdf


class PdfError(ValueError):
    pass


def extract_text(data: bytes) -> str:
    if not data.startswith(b"%PDF"):
        raise PdfError("The file is not a PDF.")
    try:
        with pymupdf.open(stream=data, filetype="pdf") as doc:
            text = "\n".join(page.get_text() for page in doc)
    except Exception as exc:  # corrupted or encrypted file
        raise PdfError(f"Could not read the PDF: {exc}") from exc
    text = text.strip()
    if len(text) < 30:
        raise PdfError(
            "No text found in the PDF. Scanned (image) resumes are not supported — "
            "please upload a PDF exported from a text editor."
        )
    return text
