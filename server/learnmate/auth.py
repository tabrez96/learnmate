"""Device token check for every API request except the public ones."""

import hmac
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

PUBLIC_PATHS = frozenset({"/api/v1/health"})


def install_device_token_auth(app: FastAPI, token: str) -> None:
    expected = f"Bearer {token}".encode()

    @app.middleware("http")
    async def require_device_token(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        path = request.url.path
        if path.startswith("/api/v1") and path not in PUBLIC_PATHS:
            header = request.headers.get("Authorization")
            # An empty token means the server is unconfigured: fail closed.
            if (
                token == ""
                or header is None
                or not hmac.compare_digest(header.encode(), expected)
            ):
                return JSONResponse({"detail": "Invalid device token"}, status_code=401)
        return await call_next(request)
