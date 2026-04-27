"""PDF content extraction — extracts readable text from user-uploaded PDFs."""
from pathlib import Path
import fitz  # PyMuPDF


def extract_pdf_content(filepath: str | Path) -> str:
    """Extract full text from a PDF file.

    Returns clean text with page markers for citation.
    This is for CONTENT extraction from user research/data PDFs,
    not visual pattern analysis (which extractors/ does).
    """
    filepath = Path(filepath)
    doc = fitz.open(str(filepath))
    pages = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text").strip()
        if text:
            pages.append(f"[Page {page_num + 1}]\n{text}")

    doc.close()
    return "\n\n".join(pages)
