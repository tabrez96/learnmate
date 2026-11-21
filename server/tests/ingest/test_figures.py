from io import BytesIO

from PIL import Image, ImageDraw

from learnmate.ingest.figures import (
    MAX_FIGURES_PER_PAGE,
    crop_figures,
    figure_path,
    find_figures,
    remove_figure_files,
    save_crop,
)
from learnmate.llm.fake import FakeLlm
from learnmate.llm.types import FigureBox, LlmUnavailableError, Usage


def page() -> bytes:
    img = Image.new("RGB", (800, 1000), "white")
    ImageDraw.Draw(img).rectangle((200, 200, 600, 500), fill="black")
    out = BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def box(*coords: float, description: str = "A drawing") -> FigureBox:
    return FigureBox(description=description, box=list(coords))


def test_crop_figures_cuts_box_as_png() -> None:
    crops = crop_figures(page(), [box(0.25, 0.2, 0.75, 0.5, description="  Leaf  ")])
    assert len(crops) == 1
    assert crops[0].description == "Leaf"
    assert crops[0].png.startswith(b"\x89PNG")
    assert Image.open(BytesIO(crops[0].png)).size == (400, 300)


def test_crop_figures_skips_blank_tiny_and_reversed_boxes() -> None:
    boxes = [
        box(0.1, 0.1, 0.9, 0.9, description="  "),
        box(0.1, 0.1, 0.11, 0.11),
        box(0.8, 0.2, 0.2, 0.5),
    ]
    assert crop_figures(page(), boxes) == []


def test_crop_figures_clamps_and_caps_at_four() -> None:
    clamped = crop_figures(page(), [box(-0.1, -0.1, 0.5, 0.5)])
    assert Image.open(BytesIO(clamped[0].png)).size == (400, 500)
    six = [box(0.1, 0.1, 0.5, 0.5, description=f"d{i}") for i in range(6)]
    crops = crop_figures(page(), six)
    assert [c.description for c in crops] == ["d0", "d1", "d2", "d3"]
    assert len(crops) == MAX_FIGURES_PER_PAGE


def test_find_figures_llm_error_returns_empty(settings) -> None:
    class Down(FakeLlm):
        def find_figures(self, image, media_type):
            raise LlmUnavailableError("down", Usage("m", "figures"))

    assert find_figures(Down(settings), page()) == []


def test_save_crop_does_not_recreate_deleted_folder(settings) -> None:
    assert save_crop(settings.data_dir, "7/fig-001-1.png", b"x") is False
    assert not (settings.data_dir / "files" / "7").exists()


def test_save_crop_writes_into_existing_folder(settings) -> None:
    folder = settings.data_dir / "files" / "7"
    folder.mkdir(parents=True)
    assert save_crop(settings.data_dir, "7/fig-001-1.png", b"x") is True
    assert (folder / "fig-001-1.png").read_bytes() == b"x"


def test_remove_figure_files_leaves_other_generations_alone(settings) -> None:
    folder = settings.data_dir / "files" / "7"
    folder.mkdir(parents=True)
    mine, other = figure_path(7, 111, 1, 1), figure_path(7, 222, 1, 1)
    for rel in (mine, other):
        assert save_crop(settings.data_dir, rel, b"x")
    remove_figure_files(settings.data_dir, 7, 111)
    assert not (settings.data_dir / "files" / mine).exists()
    assert (settings.data_dir / "files" / other).exists()
