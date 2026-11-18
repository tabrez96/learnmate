from io import BytesIO
from pathlib import Path

import pytest
from docx import Document
from PIL import Image
from pypdf import PdfWriter

from learnmate.ingest.readers import (
    DOCX_MIME,
    DOCX_PAGE_CHARS,
    MAX_IMAGE_SIDE,
    PDF_MIME,
    UnreadableFile,
    count_pages,
    iter_pages,
    normalise_image,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_typed_pdf_uses_text_layer():
    pages = list(iter_pages(FIXTURES / "typed.pdf", PDF_MIME))
    assert len(pages) == count_pages(FIXTURES / "typed.pdf", PDF_MIME) == 3
    assert all(p.image is None for p in pages)
    assert "Chapter 1: The Water Cycle" in pages[0].text
    assert "Chapter 2: Rocks and Soil" in pages[2].text


def test_scanned_pdf_pages_are_rendered():
    pages = list(iter_pages(FIXTURES / "scanned.pdf", PDF_MIME))
    assert len(pages) == 2
    for p in pages:
        assert p.text == ""
        assert p.image is not None and p.image.startswith(b"\xff\xd8")


def test_huge_pdf_page_is_rendered_within_the_size_cap(tmp_path):
    writer = PdfWriter()
    writer.add_blank_page(14400, 14400)
    path = tmp_path / "huge.pdf"
    with path.open("wb") as f:
        writer.write(f)
    (page,) = iter_pages(path, PDF_MIME)
    assert max(Image.open(BytesIO(page.image)).size) <= MAX_IMAGE_SIDE


def test_docx_reads_paragraphs_and_tables():
    pages = list(iter_pages(FIXTURES / "notes.docx", DOCX_MIME))
    assert len(pages) == 1
    text = pages[0].text
    assert "Magnets and Light" in text
    assert "A magnet pulls iron towards it." in text
    assert "Material | Magnetic" in text
    assert "Iron | Yes" in text


def test_docx_long_text_is_split_into_pages(tmp_path):
    path = tmp_path / "long.docx"
    doc = Document()
    for i in range(10):
        doc.add_paragraph(str(i) * 1000)
    doc.save(str(path))
    pages = list(iter_pages(path, DOCX_MIME))
    assert len(pages) > 1
    assert count_pages(path, DOCX_MIME) == len(pages)
    assert all(len(p.text) <= DOCX_PAGE_CHARS for p in pages)


def test_photo_is_turned_upright_from_exif():
    path = FIXTURES / "notebook_photo.jpg"
    with Image.open(path) as raw:
        assert raw.size == (800, 600)
    [page] = list(iter_pages(path, "image/jpeg"))
    with Image.open(BytesIO(page.image)) as img:
        assert img.size == (600, 800)
        r, g, b = img.getpixel((10, 10))
    assert r > 180 and g < 80 and b < 80


def test_transparent_image_is_composited_on_white():
    img = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
    img.paste((0, 0, 0, 255), (10, 10, 20, 20))
    out = Image.open(BytesIO(normalise_image(img))).convert("RGB")
    assert min(out.getpixel((2, 2))) > 240
    assert max(out.getpixel((15, 15))) < 60


def test_large_image_is_shrunk(tmp_path):
    path = tmp_path / "big.png"
    Image.new("RGB", (4000, 3000), "white").save(path)
    [page] = list(iter_pages(path, "image/png"))
    with Image.open(BytesIO(page.image)) as img:
        assert max(img.size) == MAX_IMAGE_SIDE


def test_unknown_type_is_unreadable(tmp_path):
    with pytest.raises(UnreadableFile):
        count_pages(tmp_path / "x.txt", "text/plain")


@pytest.mark.parametrize(
    ("name", "mime", "data"),
    [
        ("a.pdf", PDF_MIME, b"%PDF-1.4\n" + b"\x00junk" * 50),
        ("a.docx", DOCX_MIME, b"PK\x03\x04" + b"junk" * 50),
        ("a.jpg", "image/jpeg", b"\xff\xd8\xff" + b"junk" * 50),
    ],
)
def test_damaged_files_raise_unreadable(tmp_path, name, mime, data):
    path = tmp_path / name
    path.write_bytes(data)
    with pytest.raises(UnreadableFile):
        count_pages(path, mime)
        list(iter_pages(path, mime))
