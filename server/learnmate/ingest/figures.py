"""Figures on page images: crops from the vision model's boxes, saved as PNG."""

import datetime as dt
import logging
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image

from learnmate.files import material_dir, resolve_stored
from learnmate.ingest.readers import IMAGE_MEDIA_TYPE
from learnmate.llm.types import FigureBox, Llm, LlmError

log = logging.getLogger(__name__)

MAX_FIGURES_PER_PAGE = 4
MIN_SIDE_PX = 32  # smaller boxes are noise, not drawings


@dataclass(frozen=True)
class FigureCrop:
    description: str
    png: bytes


def _clamp(v: float) -> float:
    return min(1.0, max(0.0, v))


def crop_figures(image: bytes, boxes: list[FigureBox]) -> list[FigureCrop]:
    img = Image.open(BytesIO(image)).convert("RGB")
    w, h = img.size
    crops: list[FigureCrop] = []
    for fig in boxes:
        description = fig.description.strip()
        if not description:
            continue
        bx0, by0, bx1, by1 = (_clamp(v) for v in fig.box)
        x0, y0, x1, y1 = round(bx0 * w), round(by0 * h), round(bx1 * w), round(by1 * h)
        if x1 - x0 < MIN_SIDE_PX or y1 - y0 < MIN_SIDE_PX:
            continue
        out = BytesIO()
        img.crop((x0, y0, x1, y1)).save(out, format="PNG")
        crops.append(FigureCrop(description, out.getvalue()))
        if len(crops) == MAX_FIGURES_PER_PAGE:
            break
    return crops


def generation_stamp(created_at: dt.datetime) -> int:
    """Tells apart the jobs that used the same material id (ids are reused after a delete)."""
    return int(created_at.timestamp() * 1e6)


def figure_path(material_id: int, stamp: int, page: int, n: int) -> str:
    return f"{material_id}/fig-{stamp}-{page:03d}-{n}.png"


def save_crop(data_dir: Path, rel: str, png: bytes) -> bool:
    """False when the material's folder is gone (deleted meanwhile); it is never recreated."""
    path = resolve_stored(data_dir, rel)
    if not path.parent.is_dir():
        return False
    path.write_bytes(png)
    return True


def remove_figure_files(data_dir: Path, material_id: int, stamp: int) -> None:
    for p in material_dir(data_dir, material_id).glob(f"fig-{stamp}-*.png"):
        p.unlink(missing_ok=True)


def find_figures(llm: Llm, image: bytes) -> list[FigureCrop]:
    try:
        result = llm.find_figures(image, IMAGE_MEDIA_TYPE)
    except LlmError as exc:
        log.warning("finding figures failed, the page text is kept: %s", exc)
        return []
    return crop_figures(image, result.value.figures)
