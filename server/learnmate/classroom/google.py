"""The Classroom and Drive client. The token goes only in the Authorization header."""

import tempfile
from dataclasses import dataclass
from typing import BinaryIO
from urllib.parse import quote

import httpx

from learnmate.classroom.links import ClassroomLink
from learnmate.files import UnsupportedFile, sniff

CLASSROOM_API = "https://classroom.googleapis.com/v1"
DRIVE_API = "https://www.googleapis.com/drive/v3"
PDF = "application/pdf"
EXPORTS = {  # Google editor files -> what to export them as
    "application/vnd.google-apps.document": PDF,
    "application/vnd.google-apps.presentation": PDF,
}
MIME_EXT = {  # Drive mime -> extension accepted by learnmate.files.sniff
    PDF: ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
TIMEOUT_SECONDS = 30.0

SIGN_IN_AGAIN = (
    "classroom_sign_in_again",
    409,
    "Google sign-in has expired. Sign in to Google again and paste the link.",
)
ACCESS_DENIED = (
    "classroom_access_denied",
    403,
    (
        "Google didn't allow access to this Classroom post. "
        "Download the file from Classroom and upload it instead."
    ),
)
NOT_FOUND = (
    "classroom_not_found",
    404,
    "Couldn't find this Classroom post. Check the link, or upload the file instead.",
)
UNAVAILABLE = (
    "classroom_unavailable",
    502,
    "Google Classroom didn't answer. Try again in a minute, or upload the file instead.",
)
CLASSROOM_ERRORS = {401: SIGN_IN_AGAIN, 403: ACCESS_DENIED, 404: NOT_FOUND}
# Drive answers 404 for files the account may not see, so it counts as denied.
DRIVE_ERRORS = {401: SIGN_IN_AGAIN, 403: ACCESS_DENIED, 404: ACCESS_DENIED}


class ClassroomError(Exception):
    """The message is shown to the user; code and status tell the app which state to show."""

    def __init__(self, code: str, status: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


@dataclass(frozen=True)
class Download:
    file: BinaryIO  # tempfile.TemporaryFile, positioned at 0; the caller closes it
    ext: str
    mime: str
    size: int


@dataclass(frozen=True)
class Coursework:
    title: str
    downloads: list[Download]


def _check(response: httpx.Response, errors: dict[int, tuple[str, int, str]]) -> None:
    if 200 <= response.status_code < 300:
        return
    # A streamed response must be read before it is closed; the body is never used.
    response.read()
    raise ClassroomError(*errors.get(response.status_code, UNAVAILABLE))


def _too_large(name: str, max_bytes: int) -> ClassroomError:
    return ClassroomError(
        "classroom_file_too_large",
        413,
        f"{name} is larger than {max_bytes // (1024 * 1024)} MB. "
        "Download it from Classroom and upload a smaller copy.",
    )


def _plan(
    client: httpx.Client, drive_id: str, max_bytes: int
) -> tuple[str, dict[str, str], str, str] | None:
    """Return (url, params, ext, mime) for a Drive file we can use, else None."""
    file_url = f"{DRIVE_API}/files/{quote(drive_id, safe='')}"
    response = client.get(
        file_url,
        params={"fields": "id,name,mimeType,size", "supportsAllDrives": "true"},
    )
    _check(response, DRIVE_ERRORS)
    meta = response.json()
    mime = meta.get("mimeType")
    if mime in EXPORTS:
        return f"{file_url}/export", {"mimeType": PDF}, ".pdf", PDF
    if mime in MIME_EXT:
        if meta.get("size") is not None and int(meta["size"]) > max_bytes:
            raise _too_large(meta.get("name") or "A file", max_bytes)
        return (
            file_url,
            {"alt": "media", "supportsAllDrives": "true"},
            MIME_EXT[mime],
            mime,
        )
    return None


def _download(
    client: httpx.Client,
    url: str,
    params: dict[str, str],
    ext: str,
    mime: str,
    max_bytes: int,
) -> Download | None:
    out = tempfile.TemporaryFile()  # noqa: SIM115 - closed by the caller
    try:
        size = 0
        with client.stream("GET", url, params=params) as response:
            _check(response, DRIVE_ERRORS)
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > max_bytes:
                    raise _too_large("A file", max_bytes)
                out.write(chunk)
        out.seek(0)
        head = out.read(16)
        out.seek(0)
        if size == 0:
            out.close()
            return None
        try:
            sniff(f"file{ext}", head)
        except UnsupportedFile:
            out.close()
            return None
        return Download(out, ext, mime, size)
    except BaseException:
        out.close()
        raise


def fetch_coursework(
    link: ClassroomLink,
    token: str,
    *,
    max_bytes: int,
    max_files: int,
    transport: httpx.BaseTransport | None = None,
) -> Coursework:
    downloads: list[Download] = []
    try:
        with httpx.Client(
            headers={"Authorization": f"Bearer {token}"},
            transport=transport,
            timeout=TIMEOUT_SECONDS,
            follow_redirects=True,
        ) as client:
            post_url = (
                f"{CLASSROOM_API}/courses/{quote(link.course_id, safe='')}"
                f"/{link.kind}/{quote(link.item_id, safe='')}"
            )
            response = client.get(post_url)
            _check(response, CLASSROOM_ERRORS)
            body = response.json()
            title = (body.get("title") or "").strip()

            plans = []
            for material in body.get("materials", []):
                drive_id = (
                    (material.get("driveFile") or {}).get("driveFile", {}).get("id")
                )
                if not drive_id:
                    continue
                plan = _plan(client, drive_id, max_bytes)
                if plan is not None:
                    plans.append(plan)
            if len(plans) > max_files:
                raise ClassroomError(
                    "classroom_too_many_files",
                    422,
                    f"This Classroom post has more than {max_files} files. "
                    "Download the ones you need and upload them.",
                )
            for url, params, ext, mime in plans:
                got = _download(client, url, params, ext, mime, max_bytes)
                if got is not None:
                    downloads.append(got)
            if not downloads:
                raise ClassroomError(
                    "classroom_no_files",
                    422,
                    "This Classroom post has no PDF, Word file, Google Doc or photo "
                    "attached. Download the file and upload it instead.",
                )
            return Coursework(title=title, downloads=downloads)
    except BaseException as exc:
        for d in downloads:
            d.file.close()
        if isinstance(exc, httpx.HTTPError):
            raise ClassroomError(*UNAVAILABLE) from None
        raise
