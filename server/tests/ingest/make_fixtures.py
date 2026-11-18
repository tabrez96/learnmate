"""Generates the committed ingest fixtures. All content is invented.

Run: cd server && python tests/ingest/make_fixtures.py
"""

from pathlib import Path

from docx import Document
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent / "fixtures"

TYPED_PAGES = [
    [
        "Chapter 1: The Water Cycle",
        "Water rises from the sea as vapour when the sun warms it.",
        "High in the sky the vapour cools and forms clouds.",
    ],
    [
        "Clouds release rain, snow or hail when the drops grow heavy.",
        "The water runs into rivers and flows back to the sea.",
    ],
    [
        "Chapter 2: Rocks and Soil",
        "Rocks break into small pieces over many years.",
        "Soil is a mix of tiny rock pieces and rotted leaves.",
    ],
]
SCANNED_PAGES = [
    ["The Water Cycle", "Sun heats the sea.", "Vapour rises and cools."],
    ["Rocks and Soil", "Rocks wear down slowly.", "Soil feeds the plants."],
]


def typed_pdf() -> bytes:
    """A PDF with a real text layer (Helvetica, one content stream per page)."""
    objects: list[bytes] = [b"<< /Type /Catalog /Pages 2 0 R >>"]
    kids = " ".join(f"{4 + 2 * i} 0 R" for i in range(len(TYPED_PAGES)))
    objects.append(
        f"<< /Type /Pages /Kids [{kids}] /Count {len(TYPED_PAGES)} >>".encode()
    )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for i, lines in enumerate(TYPED_PAGES):
        content_id = 5 + 2 * i
        objects.append(
            (
                "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"
            ).encode()
        )
        body = (
            "BT /F1 12 Tf 72 760 Td 16 TL "
            + " T* ".join(f"({line}) Tj" for line in lines)
            + " ET"
        )
        stream = body.encode()
        objects.append(
            b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream)
        )

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (number, obj)
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref,
    )
    return bytes(out)


def scanned_pdf(path: Path) -> None:
    font = ImageFont.load_default(size=28)
    images = []
    for lines in SCANNED_PAGES:
        img = Image.new("RGB", (850, 1100), "white")
        draw = ImageDraw.Draw(img)
        for i, line in enumerate(lines):
            draw.text((80, 100 + i * 60), line, fill="black", font=font)
        images.append(img)
    images[0].save(path, "PDF", save_all=True, append_images=images[1:], resolution=100)


def notes_docx(path: Path) -> None:
    doc = Document()
    doc.add_heading("Magnets and Light", level=1)
    doc.add_paragraph("A magnet pulls iron towards it.")
    doc.add_paragraph("Light travels in straight lines.")
    table = doc.add_table(rows=2, cols=2)
    cells = [["Material", "Magnetic"], ["Iron", "Yes"]]
    for r, row in enumerate(cells):
        for c, value in enumerate(row):
            table.cell(r, c).text = value
    doc.save(str(path))


def notebook_photo(path: Path) -> None:
    """A sideways phone photo (EXIF orientation 6) of an invented notebook page."""
    img = Image.new("RGB", (600, 800), (250, 248, 240))
    draw = ImageDraw.Draw(img)
    for y in range(120, 780, 40):
        draw.line([(0, y), (600, y)], fill=(150, 170, 220), width=2)
    draw.line([(70, 0), (70, 800)], fill=(210, 60, 60), width=3)
    font = ImageFont.load_default(size=26)
    notes = ["Plants need light", "Roots drink water", "Leaves make food"]
    for i, line in enumerate(notes):
        draw.text((90, 128 + i * 40), line, fill=(30, 30, 120), font=font)
    draw.rectangle([0, 0, 39, 39], fill=(255, 0, 0))
    sideways = img.transpose(Image.Transpose.ROTATE_90)
    exif = Image.Exif()
    exif[0x0112] = 6
    exif[0x010F] = "PhoneCam"
    sideways.save(path, "JPEG", quality=80, exif=exif)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "typed.pdf").write_bytes(typed_pdf())
    scanned_pdf(OUT / "scanned.pdf")
    notes_docx(OUT / "notes.docx")
    notebook_photo(OUT / "notebook_photo.jpg")


if __name__ == "__main__":
    main()
