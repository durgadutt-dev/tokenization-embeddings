"""
pdf_extractor.py
----------------
PDF text and table extraction using pdfplumber.

This module is intentionally decoupled from the model and UI layers.
It can be used standalone to extract raw text from any PDF:

    from pdf_extractor import extract_pdf
    pages = extract_pdf("path/to/file.pdf")  # returns list[str], one per page
"""
import logging
import pdfplumber


def _extract_tables(page) -> str:
    """
    Extract table content from a pdfplumber page object.

    Tries bordered-table detection first ('lines' strategy, works for tables
    with visible borders like SBC coverage tables). Falls back to text-based
    detection for borderless tables.

    Returns:
        Pipe-separated table rows as a single string, or "" if no tables found.
    """
    # Strategy 1: bordered tables (most SBC tables use visible lines)
    tables = page.extract_tables({
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
    })

    # Strategy 2: borderless tables (fallback)
    if not tables:
        tables = page.extract_tables({
            "vertical_strategy": "text",
            "horizontal_strategy": "text",
        })

    if not tables:
        return ""

    rows = []
    for table in tables:
        for row in table:
            cleaned = [cell.strip() if cell else "" for cell in row]
            if any(cleaned):  # skip fully empty rows
                rows.append(" | ".join(cleaned))

    return "\n".join(rows)


def extract_page_text(page) -> str:
    """
    Extract all text content from a single pdfplumber page.

    Combines plain text (preserving reading order) with table data
    (serialised as pipe-separated rows). Table data is appended under
    a [TABLE DATA] header so downstream parsers can distinguish it.

    Args:
        page: A pdfplumber page object.

    Returns:
        Combined plain text + table content for the page.
        Returns "" if the page has no extractable content.
    """
    plain_text = page.extract_text() or ""
    table_text = _extract_tables(page)

    if table_text:
        return f"{plain_text}\n\n[TABLE DATA]\n{table_text}"
    return plain_text


def extract_pdf(file_path: str) -> list[str]:
    """
    Extract text from every page of a PDF file.

    Args:
        file_path: Path to the PDF file.

    Returns:
        List of strings, one per page (preserving page index alignment).
        Empty pages are included as empty strings so that page indices
        remain aligned with physical page numbers.

    Logs:
        Per-page content and total character count to the active log handler.
    """
    pages = []

    with pdfplumber.open(file_path) as pdf:
        logging.info(f"--- PDF Extraction started: {len(pdf.pages)} page(s) | {file_path} ---")

        for i, page in enumerate(pdf.pages):
            page_text = extract_page_text(page)
            logging.info(f"[Page {i + 1}]\n{page_text or '(no text extracted)'}")
            pages.append(page_text)  # append even if empty to keep page alignment

    total_chars = sum(len(p) for p in pages)
    logging.info(f"--- PDF Extraction complete: {total_chars} characters across {len(pages)} pages ---")

    return pages
