"""Where uploaded material lives on disk and which file types are accepted."""

import shutil
from collections.abc import Callable, Iterable
from pathlib import Path

FILES_DIRNAME = "files"
# extension -> (mime, magic-bytes check)
ALLOWED: dict[str, tuple[str, Callable[[bytes], bool]]] = {
    ".pdf": ("application/pdf", lambda h: h.startswith(b"%PDF-")),
    ".docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        lambda h: h.startswith(b"PK\x03\x04"),
    ),
    ".jpg": ("image/jpeg", lambda h: h.startswith(b"\xff\xd8\xff")),
    ".jpeg": ("image/jpeg", lambda h: h.startswith(b"\xff\xd8\xff")),
    ".png": ("image/png", lambda h: h.startswith(b"\x89PNG\r\n\x1a\n")),
    ".webp": ("image/webp", lambda h: h[:4] == b"RIFF" and h[8:12] == b"WEBP"),
}
UNSUPPORTED_HINT = "Upload a PDF, a Word file (.docx) or a photo (JPG, PNG or WebP)."


class UnsupportedFile(ValueError):
    pass


def files_dir(data_dir: Path) -> Path:
    return data_dir / FILES_DIRNAME


# Storage convention: every file that belongs to a material, including figures
# written later by ingest, lives under files/<material_id>/. MaterialFile.path
# and Figure.path are stored relative to files/. Uploaded files are saved as
# <material_id>/<nn><ext>, where nn is the 2-digit 1-based order in the upload,
# for example 7/01.pdf. The user's filename is never used on disk.
def material_dir(data_dir: Path, material_id: int) -> Path:
    return files_dir(data_dir) / str(material_id)


def sniff(filename: str, head: bytes) -> tuple[str, str]:
    """Return (extension, mime) for an accepted file, else raise UnsupportedFile."""
    ext = Path(filename).suffix.lower()
    if ext == ".doc":
        raise UnsupportedFile(
            f"Can't use {filename}: old Word files aren't supported. "
            "Save it as .docx and upload again."
        )
    allowed = ALLOWED.get(ext)
    if allowed is None or not allowed[1](head):
        raise UnsupportedFile(f"Can't use {filename}. {UNSUPPORTED_HINT}")
    return ext, allowed[0]


def resolve_stored(data_dir: Path, rel: str) -> Path:
    root = files_dir(data_dir).resolve()
    path = (root / rel).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"{rel} is outside the files directory")
    return path


def remove_material_dirs(data_dir: Path, material_ids: Iterable[int]) -> None:
    for material_id in material_ids:
        try:
            shutil.rmtree(material_dir(data_dir, material_id))
        except FileNotFoundError:
            pass
