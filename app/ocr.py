from __future__ import annotations
import os
import io
from typing import Tuple, Optional, List

from PIL import Image
import pdfplumber
from pdf2image import convert_from_bytes
import pytesseract

def _bool_env(name: str, default: bool = False) -> bool:
    v = os.getenv(name, str(default)).strip().lower()
    return v in ("1", "true", "yes", "y", "on")

def extract_text_from_upload(filename: str, content_type: str, data: bytes) -> Tuple[str, str]:
    """Return (text, method)."""
    disable_ocr = _bool_env("DISABLE_OCR", False)

    ext = (filename or "").lower().split(".")[-1]
    is_pdf = (content_type == "application/pdf") or (ext == "pdf")
    is_image = content_type.startswith("image/") or ext in ("jpg", "jpeg", "png", "webp")

    if is_pdf:
        # 1) Try extracting embedded text first
        text = _pdf_text(data)
        if text.strip():
            return (text, "pdf-text")

        if disable_ocr:
            return ("", "pdf-no-text-ocr-disabled")

        # 2) OCR rendered pages (scanned PDFs)
        return (_pdf_ocr(data), "pdf-ocr")

    if is_image:
        if disable_ocr:
            return ("", "image-ocr-disabled")
        return (_image_ocr(data), "image-ocr")

    raise ValueError("Unsupported file type. Please upload a PDF or image (JPEG/PNG).")

def _pdf_text(data: bytes) -> str:
    out: List[str] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            if txt.strip():
                out.append(txt)
    return "\n\n".join(out)

def _pdf_ocr(data: bytes, max_pages: int = 12) -> str:
    # Convert PDF to images, then OCR each page.
    images = convert_from_bytes(data, fmt="png")
    chunks: List[str] = []
    for i, img in enumerate(images[:max_pages]):
        chunks.append(pytesseract.image_to_string(img))
    if len(images) > max_pages:
        chunks.append(f"\n[Note: OCR limited to first {max_pages} pages]\n")
    return "\n\n".join(chunks)

def _image_ocr(data: bytes) -> str:
    img = Image.open(io.BytesIO(data)).convert("RGB")
    return pytesseract.image_to_string(img)
