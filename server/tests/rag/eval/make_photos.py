"""Generates the committed notebook photos for the retrieval eval from corpus.yaml.

Each photo page's vision_text is drawn as handwriting-like lines on a ruled page. The
eval does not read the pixels (it uses the recorded vision_text), but the file goes
through the same reader as a real phone photo. All content is invented.

Run: cd server && python tests/rag/eval/make_photos.py
"""

from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
OUT = HERE / "photos"
SIDEWAYS = {"heat-notes.jpg"}  # saved the way a phone stores a rotated shot


def photo_pages() -> dict[str, str]:
    corpus = yaml.safe_load((HERE / "corpus.yaml").read_text())
    return {
        page["photo"]: page["vision_text"]
        for subject in corpus["subjects"]
        for material in subject["materials"]
        for chapter in material["chapters"]
        for page in chapter["pages"]
        if "photo" in page
    }


def notebook_page(vision_text: str) -> Image.Image:
    img = Image.new("RGB", (900, 1200), (250, 248, 240))
    draw = ImageDraw.Draw(img)
    for y in range(100, 1200, 44):
        draw.line([(0, y), (900, y)], fill=(150, 170, 220), width=2)
    draw.line([(70, 0), (70, 1200)], fill=(210, 60, 60), width=3)
    font = ImageFont.load_default(size=30)
    for i, line in enumerate(vision_text.splitlines()):
        draw.text((90 + (i * 7) % 15, 62 + i * 44), line, fill=(30, 30, 120), font=font)
    return img.rotate(2, expand=True, fillcolor=(128, 128, 128))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, text in photo_pages().items():
        img = notebook_page(text)
        exif = Image.Exif()
        exif[0x010F] = "PhoneCam"
        if name in SIDEWAYS:
            img = img.transpose(Image.Transpose.ROTATE_90)
            exif[0x0112] = 6
        img.save(OUT / name, "JPEG", quality=80, exif=exif)


if __name__ == "__main__":
    main()
