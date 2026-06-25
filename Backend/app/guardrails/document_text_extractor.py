"""Extract plain text from uploaded spec documents for guardrail scanning."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

from app.guardrails.config import MAX_SCAN_CHARS


@dataclass
class DocumentExtract:
    text: str
    page_spans: List[Tuple[int, int, int]] = field(default_factory=list)
    paragraph_spans: List[Tuple[int, int, int]] = field(default_factory=list)
    source_ext: str = ""


def extract_document_for_scan(file_path: Path, max_chars: int = MAX_SCAN_CHARS) -> DocumentExtract:
    """
    Extract readable text plus page/paragraph span metadata for location reporting.
    """
    path = Path(file_path)
    if not path.exists():
        return DocumentExtract(text="", source_ext=path.suffix.lower())

    ext = path.suffix.lower()
    text = ""
    page_spans: List[Tuple[int, int, int]] = []
    paragraph_spans: List[Tuple[int, int, int]] = []

    try:
        if ext == ".pdf":
            text, page_spans = _extract_pdf_with_spans(path)
        elif ext in (".docx", ".doc"):
            text, paragraph_spans = _extract_docx_with_spans(path)
        elif ext in (".txt", ".html", ".htm"):
            text = path.read_text(encoding="utf-8", errors="replace")
        else:
            text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        print(f"⚠️ Guardrail text extraction failed for {path}: {exc}")
        return DocumentExtract(text="", source_ext=ext)

    if len(text) > max_chars:
        text = text[:max_chars]
        page_spans = _clip_spans(page_spans, max_chars)
        paragraph_spans = _clip_spans(paragraph_spans, max_chars)

    return DocumentExtract(
        text=text,
        page_spans=page_spans,
        paragraph_spans=paragraph_spans,
        source_ext=ext,
    )


def extract_text_for_scan(file_path: Path, max_chars: int = MAX_SCAN_CHARS) -> str:
    """Extract readable text from a document for security scanning."""
    return extract_document_for_scan(file_path, max_chars=max_chars).text


def _clip_spans(spans: List[Tuple[int, int, int]], max_chars: int) -> List[Tuple[int, int, int]]:
    clipped: List[Tuple[int, int, int]] = []
    for start, end, num in spans:
        if start >= max_chars:
            break
        clipped.append((start, min(end, max_chars), num))
    return clipped


def _extract_pdf_with_spans(pdf_path: Path) -> tuple[str, List[Tuple[int, int, int]]]:
    import fitz  # PyMuPDF

    parts: list[str] = []
    page_spans: List[Tuple[int, int, int]] = []
    offset = 0
    doc = fitz.open(str(pdf_path))
    try:
        for page_num in range(min(doc.page_count, 50)):
            page = doc.load_page(page_num)
            page_text = page.get_text()
            start = offset
            parts.append(page_text)
            offset += len(page_text)
            if page_num < min(doc.page_count, 50) - 1:
                offset += 1
            page_spans.append((start, offset, page_num + 1))
    finally:
        doc.close()
    return "\n".join(parts), page_spans


def _extract_docx_with_spans(docx_path: Path) -> tuple[str, List[Tuple[int, int, int]]]:
    from docx import Document

    doc = Document(str(docx_path))
    parts: list[str] = []
    paragraph_spans: List[Tuple[int, int, int]] = []
    offset = 0
    para_num = 0
    for paragraph in doc.paragraphs:
        text = paragraph.text
        if not text.strip():
            continue
        para_num += 1
        start = offset
        parts.append(text)
        offset += len(text) + 1
        paragraph_spans.append((start, offset, para_num))
    return "\n".join(parts), paragraph_spans


def _extract_pdf(pdf_path: Path) -> str:
    text, _ = _extract_pdf_with_spans(pdf_path)
    return text


def _extract_docx(docx_path: Path) -> str:
    text, _ = _extract_docx_with_spans(docx_path)
    return text


def chunk_text(text: str, max_chars: int = 2000, overlap: int = 200) -> list[str]:
    """Split long documents into overlapping chunks for per-chunk scanning."""
    return [chunk for chunk, _, _ in chunk_text_with_spans(text, max_chars, overlap)]


def chunk_text_with_spans(
    text: str,
    max_chars: int = 2000,
    overlap: int = 200,
) -> List[Tuple[str, int, int]]:
    """Split text into chunks with global (start, end) character offsets."""
    if not text:
        return []
    if len(text) <= max_chars:
        return [(text, 0, len(text))]

    chunks: List[Tuple[str, int, int]] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunks.append((text[start:end], start, end))
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return chunks
