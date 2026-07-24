"""
Every failure the API can produce, as one small hierarchy.

Domain modules raise these instead of `HTTPException`, so business logic stays
free of web framework imports and the status code is decided next to the rule
that was broken. `register_error_handlers` turns them into JSON at the edge.

Anything not derived from `AppError` is a bug: it becomes a 500 with a generic
message, and the traceback goes to the log rather than to the client.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("kya.error")


class AppError(Exception):
    """Base for everything we raise deliberately. `message` is user-facing."""

    status_code = 500
    code = "internal_error"

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class ValidationError(AppError):
    """The request was well-formed but the values don't make sense."""

    status_code = 400
    code = "invalid_request"


class AuthError(AppError):
    """Missing, invalid or expired credentials."""

    status_code = 401
    code = "unauthorized"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    """The account isn't in a state that allows this yet (e.g. Swiggy not linked)."""

    status_code = 409
    code = "conflict"


class RateLimitError(AppError):
    status_code = 429
    code = "rate_limited"


class UpstreamError(AppError):
    """A third party we depend on (Swiggy, OpenAI, Google, Twilio) failed us."""

    status_code = 502
    code = "upstream_error"


def _payload(message: str, code: str, request_id: str | None) -> dict:
    body = {"detail": message, "code": code}
    if request_id:
        body["request_id"] = request_id
    return body


def request_id_of(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def register_error_handlers(app: FastAPI) -> None:
    """Install the handlers that guarantee every error leaves as JSON."""

    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:
        rid = request_id_of(request)
        # 5xx is our fault and worth a stack trace; 4xx is the caller's and isn't.
        if exc.status_code >= 500:
            log.error("%s: %s", exc.code, exc.message, exc_info=exc)
        else:
            log.info("%s: %s", exc.code, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(exc.message, exc.code, rid),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(str(exc.detail), "http_error", request_id_of(request)),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Pydantic's raw error list is noise to a client; name the fields instead.
        fields = ", ".join(
            ".".join(str(p) for p in err.get("loc", ()) if p != "body")
            for err in exc.errors()
        )
        message = f"Invalid request: check {fields}" if fields else "Invalid request"
        return JSONResponse(
            status_code=422,
            content=_payload(message, "invalid_request", request_id_of(request)),
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        rid = request_id_of(request)
        # The client gets nothing specific — an exception message can carry a
        # connection string, a token or a file path. The log gets everything.
        log.exception("unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content=_payload("Something went wrong on our side.", "internal_error", rid),
        )
