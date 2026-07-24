"""
One request-scoped middleware: correlation id, timing, and the access log line.

We log requests ourselves rather than using uvicorn's access log because we want
the duration, a request id that also appears on any error response, and a path
that has been stripped of secrets — OAuth callbacks arrive with `?code=…&state=…`
in the URL, which uvicorn would happily write to disk verbatim.
"""

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from app.logging_config import DIM, RESET, STATUS_COLOUR, colour_enabled

log = logging.getLogger("kya.request")

# Query parameters that are credentials in transit.
_SECRET_PARAMS = {"code", "state", "token", "id_token", "access_token"}

# Chatty and uninteresting once you've seen one.
_QUIET_PATHS = {"/health"}


def _safe_target(request: Request) -> str:
    path = request.url.path
    if not request.url.query:
        return path
    params = sorted({k for k in request.query_params if k in _SECRET_PARAMS})
    return f"{path}?«{','.join(params)} redacted»" if params else f"{path}?…"


async def request_context(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    request.state.request_id = rid

    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        # The exception handlers turn this into a response; we only need the
        # timing line so a failed request still shows up in the access log.
        elapsed_ms = (time.perf_counter() - started) * 1000
        log.error("%s %s → crashed in %.0fms", request.method, _safe_target(request), elapsed_ms)
        raise

    elapsed_ms = (time.perf_counter() - started) * 1000
    response.headers["X-Request-Id"] = rid

    if request.url.path not in _QUIET_PATHS:
        status = str(response.status_code)
        timing = f"{elapsed_ms:.0f}ms"
        if colour_enabled():
            status = f"{STATUS_COLOUR.get(response.status_code // 100, '')}{status}{RESET}"
            timing = f"{DIM}{timing}{RESET}"
        log.info("%s %s → %s %s", request.method, _safe_target(request), status, timing)

    return response
