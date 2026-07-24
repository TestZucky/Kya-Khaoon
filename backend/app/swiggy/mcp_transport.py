"""
Minimal MCP client over the Streamable HTTP transport.

A remote OAuth MCP server (which is what `swiggy-food` is) speaks JSON-RPC 2.0
over a single HTTP endpoint. One tool call is three messages:

  1. initialize           → server may return an `Mcp-Session-Id` header
  2. notifications/initialized
  3. tools/call            → the CallToolResult we want

Responses come back as either `application/json` (one message) or
`text/event-stream` (SSE, one `data:` line per message), so both are handled. We
only need the client half of MCP, so this is a few functions over httpx rather
than the full SDK (which drags in server-side deps that conflict with FastAPI).

Everything that can go wrong here surfaces as `McpError`, an `UpstreamError`:
callers shouldn't have to know whether the failure was a socket, a status code,
a malformed envelope, or the tool itself refusing.
"""

import json
import logging

import httpx

from app.errors import UpstreamError

log = logging.getLogger("kya.swiggy")

PROTOCOL_VERSION = "2025-06-18"
CLIENT_INFO = {"name": "kya-khaoon-backend", "version": "0.1.0"}


class McpError(UpstreamError):
    """A JSON-RPC error, a transport failure, or a tool returning isError."""


def extract_messages(resp: httpx.Response) -> list[dict]:
    """Pull JSON-RPC messages out of a response, JSON or SSE."""
    ctype = resp.headers.get("content-type", "")
    if "text/event-stream" in ctype:
        messages: list[dict] = []
        for block in resp.text.split("\n\n"):
            data = "\n".join(
                line[len("data:") :].lstrip()
                for line in block.splitlines()
                if line.startswith("data:")
            )
            if not data:
                continue
            try:
                messages.append(json.loads(data))
            except json.JSONDecodeError:
                continue
        return messages
    if not resp.content:
        return []
    try:
        body = resp.json()
    except ValueError as e:
        raise McpError("MCP server returned a non-JSON body") from e
    return body if isinstance(body, list) else [body]


def result_for(messages: list[dict], request_id: int) -> dict | None:
    """Find the response to our request id; raise on a JSON-RPC error."""
    for m in messages:
        if m.get("id") == request_id:
            if "error" in m:
                raise McpError(m["error"].get("message", "MCP error"))
            return m.get("result")
    raise McpError(f"no JSON-RPC response for request {request_id}")


def _first_text(result: dict) -> str | None:
    for block in result.get("content") or []:
        if block.get("type") == "text":
            return block.get("text")
    return None


def tool_payload(result: dict | None) -> dict:
    """
    Unwrap a CallToolResult into the dict the tool returned. Swiggy's tools return
    their JSON as a text content block (some servers also mirror it in
    `structuredContent`, which we prefer when present).
    """
    if result is None:
        raise McpError("empty tool result")
    if result.get("isError"):
        raise McpError(_first_text(result) or "tool returned an error")
    if result.get("structuredContent") is not None:
        return result["structuredContent"]
    text = _first_text(result)
    if text is None:
        raise McpError("tool result had no text content")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise McpError("tool returned malformed JSON") from e


class StreamableHttpMcp:
    """One short-lived MCP session: initialize → initialized → one tools/call."""

    def __init__(self, url: str, timeout: float, token: str | None) -> None:
        self._url = url
        self._timeout = timeout
        self._token = token

    def _headers(self, session_id: str | None = None) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        if session_id:
            headers["Mcp-Session-Id"] = session_id
        return headers

    async def call_tool(self, name: str, arguments: dict) -> dict:
        try:
            return await self._call_tool(name, arguments)
        except McpError:
            raise
        except httpx.TimeoutException as e:
            raise McpError(f"Swiggy timed out after {self._timeout}s") from e
        except httpx.HTTPStatusError as e:
            # 401 here means the user's OAuth token is dead. It still reads as an
            # upstream failure to us — the client re-connects, it doesn't re-login.
            raise McpError(f"Swiggy returned {e.response.status_code}") from e
        except httpx.HTTPError as e:
            raise McpError(f"couldn't reach Swiggy: {type(e).__name__}") from e

    async def _call_tool(self, name: str, arguments: dict) -> dict:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            init = await client.post(
                self._url,
                headers=self._headers(),
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": PROTOCOL_VERSION,
                        "capabilities": {},
                        "clientInfo": CLIENT_INFO,
                    },
                },
            )
            init.raise_for_status()
            session_id = init.headers.get("mcp-session-id")
            result_for(extract_messages(init), 1)

            # Notification — no response expected.
            await client.post(
                self._url,
                headers=self._headers(session_id),
                json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            )

            call = await client.post(
                self._url,
                headers=self._headers(session_id),
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": name, "arguments": arguments},
                },
            )
            call.raise_for_status()
            return tool_payload(result_for(extract_messages(call), 2))
