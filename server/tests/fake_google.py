"""A fake Google API (Classroom and Drive) on httpx.MockTransport."""

import re

import httpx

TOKEN = "ya29.fake-classroom-token-7f3c"


class FakeGoogle:
    def __init__(self) -> None:
        self.posts: dict[tuple[str, str, str], dict] = {}  # course, kind, item -> JSON
        self.files: dict[
            str, tuple[dict, bytes]
        ] = {}  # drive id -> (metadata, content)
        self.exports: dict[str, bytes] = {}  # drive id -> PDF bytes
        self.fail: dict[str, int | Exception] = {}  # path prefix -> status or error
        self.requests: list[httpx.Request] = []

    @property
    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handler)

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        prefixes = [p for p in self.fail if path.startswith(p)]
        if prefixes:
            forced = self.fail[max(prefixes, key=len)]
            if isinstance(forced, Exception):
                raise forced
            return httpx.Response(
                forced, json={"error": {"code": forced, "status": "PERMISSION_DENIED"}}
            )
        if request.headers.get("Authorization") != f"Bearer {TOKEN}":
            return httpx.Response(401, json={"error": {"code": 401}})
        if match := re.fullmatch(r"/v1/courses/([^/]+)/([^/]+)/([^/]+)", path):
            post = self.posts.get(match.groups())
            return httpx.Response(200, json=post) if post else _not_found()
        if match := re.fullmatch(r"/drive/v3/files/([^/]+)/export", path):
            assert request.url.params["mimeType"] == "application/pdf"
            data = self.exports.get(match[1])
            return httpx.Response(200, content=data) if data else _not_found()
        if match := re.fullmatch(r"/drive/v3/files/([^/]+)", path):
            entry = self.files.get(match[1])
            if entry is None:
                return _not_found()
            if request.url.params.get("alt") == "media":
                return httpx.Response(200, content=entry[1])
            return httpx.Response(200, json=entry[0])
        return _not_found()


def _not_found() -> httpx.Response:
    return httpx.Response(404, json={"error": {"code": 404}})
