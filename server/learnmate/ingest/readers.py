"""File readers: page counts and page iterators for PDF, Word and photos. No database, no AI."""

import threading
from collections.abc import Iterator
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import pypdfium2
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from PIL import Image, ImageOps
from pypdf import PdfReader

MIN_TEXT_CHARS = 50  # a PDF page with less text than this is read by vision
DOCX_PAGE_CHARS = 3000  # Word has no pages: cut its text into pages of about this size
RENDER_SCALE = 2  # pypdfium2 scale (about 144 dpi)
MAX_IMAGE_SIDE = 1568  # longest side sent to the vision model
IMAGE_MEDIA_TYPE = "image/jpeg"
# PDFium is not thread-safe, even across documents; ingestion runs in worker threads.
# Never hold this across a yield.
_PDFIUM_LOCK = threading.Lock()
PDF_MIME = "application/pdf"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@dataclass(frozen=True)
class RawPage:
    text: str = ""
    image: bytes | None = None  # upright JPEG; set when the page must be read by vision


class UnreadableFile(Exception): ...


def normalise_image(image: Image.Image) -> bytes:
    if image.mode in ("RGBA", "LA", "PA") or "transparency" in image.info:
        rgba = image.convert("RGBA")
        img = Image.new("RGB", rgba.size, "white")
        img.paste(rgba, mask=rgba.getchannel("A"))
    else:
        img = image.convert("RGB")
    img.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
    out = BytesIO()
    img.save(out, "JPEG", quality=85)
    return out.getvalue()


def _kind(mime: str) -> str:
    if mime == PDF_MIME:
        return "pdf"
    if mime == DOCX_MIME:
        return "docx"
    if mime.startswith("image/"):
        return "photo"
    raise UnreadableFile(f"unsupported type {mime}")


def count_pages(path: Path, mime: str) -> int:
    kind = _kind(mime)
    try:
        if kind == "photo":
            return 1
        count = len(PdfReader(path).pages) if kind == "pdf" else len(_docx_pages(path))
    except Exception as exc:
        raise UnreadableFile(str(exc)) from exc
    if count == 0:
        raise UnreadableFile("no pages")
    return count


def iter_pages(path: Path, mime: str) -> Iterator[RawPage]:
    kind = _kind(mime)
    try:
        if kind == "pdf":
            yield from _pdf_pages(path)
        elif kind == "docx":
            for text in _docx_pages(path):
                yield RawPage(text=text)
        else:
            with Image.open(path) as img:
                upright = ImageOps.exif_transpose(img)
                yield RawPage(image=normalise_image(upright))
    except UnreadableFile:
        raise
    except Exception as exc:
        raise UnreadableFile(str(exc)) from exc


def _pdf_pages(path: Path) -> Iterator[RawPage]:
    reader = PdfReader(path)
    with _PDFIUM_LOCK:
        pdf = pypdfium2.PdfDocument(str(path))
    try:
        for i in range(len(reader.pages)):
            text = (reader.pages[i].extract_text() or "").strip()
            if len(text) >= MIN_TEXT_CHARS:
                yield RawPage(text=text)
                continue
            with _PDFIUM_LOCK:
                page = pdf[i]
                try:
                    scale = min(RENDER_SCALE, MAX_IMAGE_SIDE / max(page.get_size()))
                    img = page.render(scale=scale).to_pil()
                finally:
                    page.close()
            yield RawPage(image=normalise_image(img))
    finally:
        with _PDFIUM_LOCK:
            pdf.close()


def _docx_text(path: Path) -> list[str]:
    blocks: list[str] = []
    for item in Document(str(path)).iter_inner_content():
        if isinstance(item, Paragraph):
            blocks.append(item.text)
        elif isinstance(item, Table):
            blocks.extend(
                " | ".join(cell.text for cell in row.cells) for row in item.rows
            )
    return [b for b in blocks if b.strip()]


def _docx_pages(path: Path) -> list[str]:
    pages: list[str] = []
    current: list[str] = []
    size = 0
    for block in _docx_text(path):
        if current and size + len(block) + 1 > DOCX_PAGE_CHARS:
            pages.append("\n".join(current))
            current, size = [], 0
        current.append(block)
        size += len(block) + 1
    if current:
        pages.append("\n".join(current))
    return pages
