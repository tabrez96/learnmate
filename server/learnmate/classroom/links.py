"""Parse and normalise a Google Classroom post link (pure code)."""

import base64
import binascii
import re
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlsplit

_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_KINDS: dict[str, Literal["courseWork", "courseWorkMaterials"]] = {
    "a": "courseWork",
    "m": "courseWorkMaterials",
}


class InvalidLink(ValueError):
    pass


@dataclass(frozen=True)
class ClassroomLink:
    course_id: str  # API id (numeric string)
    item_id: str  # API id
    kind: Literal["courseWork", "courseWorkMaterials"]
    url: str  # normalised: https://classroom.google.com/c/<course>/<a|m>/<item>/details


def api_id(token: str) -> str:
    """Web links carry the numeric API id as base64url; plain digits stay as they are."""
    if token.isascii() and token.isdigit():
        return token
    try:
        decoded = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4)).decode(
            "ascii"
        )
    except binascii.Error, ValueError:
        return token
    return decoded if decoded.isdigit() else token


def parse_link(text: str) -> ClassroomLink:
    try:
        parts = urlsplit(text.strip())
        host = (parts.hostname or "").lower()
    except ValueError:
        raise InvalidLink("Not a link") from None
    if parts.scheme != "https" or host != "classroom.google.com":
        raise InvalidLink("Not a Google Classroom link")
    segments = [s for s in parts.path.split("/") if s]
    if len(segments) >= 2 and segments[0] == "u" and segments[1].isdigit():
        segments = segments[2:]
    if (
        len(segments) < 4
        or segments[0] != "c"
        or segments[2] not in _KINDS
        or not _ID.match(segments[1])
        or not _ID.match(segments[3])
    ):
        raise InvalidLink("Not a Classroom assignment or material link")
    course, short, item = segments[1], segments[2], segments[3]
    return ClassroomLink(
        course_id=api_id(course),
        item_id=api_id(item),
        kind=_KINDS[short],
        url=f"https://classroom.google.com/c/{course}/{short}/{item}/details",
    )
