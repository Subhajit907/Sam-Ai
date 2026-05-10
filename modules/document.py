"""Document module — extracts text/images from uploaded files for AI context."""

import os
import base64

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
_TEXT_EXTS  = {".txt", ".md", ".csv"}
_PDF_EXTS   = {".pdf"}
_DOCX_EXTS  = {".docx", ".doc"}

SUPPORTED_EXTS = _IMAGE_EXTS | _TEXT_EXTS | _PDF_EXTS | _DOCX_EXTS

MAX_CHARS = 8000   # cap injected text to avoid token overflow


def is_supported(path: str) -> bool:
    return _ext(path) in SUPPORTED_EXTS


def is_image(path: str) -> bool:
    return _ext(path) in _IMAGE_EXTS


def _ext(path: str) -> str:
    return os.path.splitext(path)[1].lower()


def extract_text(path: str) -> str:
    """Return text content of a document, truncated to MAX_CHARS."""
    ext = _ext(path)
    try:
        if ext in _TEXT_EXTS:
            return open(path, encoding="utf-8", errors="ignore").read()[:MAX_CHARS]
        if ext in _PDF_EXTS:
            return _pdf_text(path)
        if ext in _DOCX_EXTS:
            return _docx_text(path)
    except Exception as e:
        return f"[Error reading document: {e}]"
    return ""


def _pdf_text(path: str) -> str:
    try:
        import fitz   # pymupdf
        doc = fitz.open(path)
        pages = [page.get_text() for page in doc]
        doc.close()
        return "\n".join(pages)[:MAX_CHARS]
    except ImportError:
        return "[PDF support requires: pip install pymupdf]"
    except Exception as e:
        return f"[PDF error: {e}]"


def _docx_text(path: str) -> str:
    try:
        from docx import Document
        doc = Document(path)
        lines = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(lines)[:MAX_CHARS]
    except ImportError:
        return "[DOCX support requires: pip install python-docx]"
    except Exception as e:
        return f"[DOCX error: {e}]"


def to_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def mime_type(path: str) -> str:
    return {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png",  ".webp": "image/webp",
        ".gif": "image/gif",  ".bmp":  "image/bmp",
    }.get(_ext(path), "image/jpeg")
