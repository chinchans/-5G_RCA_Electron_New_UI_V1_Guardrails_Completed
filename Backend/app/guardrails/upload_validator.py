"""Server-side upload validation for Specification Intelligence documents."""

from pathlib import Path
from typing import Optional, Tuple

from fastapi import HTTPException, UploadFile

from app.guardrails.config import ALLOWED_EXTENSIONS, MAX_UPLOAD_BYTES


def _read_magic_header(data: bytes) -> str:
    if data.startswith(b"%PDF"):
        return "pdf"
    if data.startswith(b"PK\x03\x04"):
        return "zip"  # docx is OOXML zip
    if data.startswith(b"<!DOCTYPE") or data.startswith(b"<html") or data.startswith(b"<HTML"):
        return "html"
    # Plain text — no reliable magic; allow if extension matches
    try:
        data[:4096].decode("utf-8")
        return "text"
    except UnicodeDecodeError:
        return "unknown"


def validate_filename(filename: Optional[str]) -> str:
    if not filename or not str(filename).strip():
        raise HTTPException(status_code=400, detail="Filename is required")
    name = Path(filename).name
    if name.startswith(".") or ".." in name:
        raise HTTPException(status_code=400, detail="Invalid filename")
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext or 'none'}' not allowed. "
                   f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    return ext


def validate_magic_bytes(content: bytes, ext: str) -> None:
    if len(content) < 4:
        raise HTTPException(status_code=400, detail="File is empty or too small")

    kind = _read_magic_header(content)

    if ext == ".pdf" and kind != "pdf":
        raise HTTPException(status_code=400, detail="File content does not match PDF format")
    if ext in (".docx", ".doc") and ext == ".docx" and kind != "zip":
        raise HTTPException(status_code=400, detail="File content does not match DOCX format")
    if ext in (".html", ".htm") and kind not in ("html", "text"):
        raise HTTPException(status_code=400, detail="File content does not match HTML format")
    if ext == ".txt" and kind == "unknown":
        raise HTTPException(status_code=400, detail="File does not appear to be valid UTF-8 text")


async def read_upload_with_limit(file: UploadFile, max_bytes: int = MAX_UPLOAD_BYTES) -> Tuple[bytes, str]:
    """
    Read upload stream with size cap.
    Returns (file_bytes, extension).
    """
    ext = validate_filename(file.filename)
    chunks: list[bytes] = []
    total = 0
    chunk_size = 1024 * 1024

    while True:
        piece = await file.read(chunk_size)
        if not piece:
            break
        total += len(piece)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds maximum size of {max_bytes // (1024 * 1024)} MB",
            )
        chunks.append(piece)

    content = b"".join(chunks)
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    validate_magic_bytes(content, ext)
    return content, ext
