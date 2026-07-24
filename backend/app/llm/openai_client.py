"""
Thin OpenAI Chat Completions client with Structured Outputs.

One function: `chat_json(system, user, schema)` → a dict guaranteed to match the
JSON schema (OpenAI enforces it with `response_format: json_schema, strict`).
Kept to httpx so we don't pull in the SDK — the request is a plain POST.

Every failure mode raises `LlmError`, which is an `UpstreamError`. Callers treat
it as "the model is unavailable" and fall back to the deterministic rules, so no
LLM problem is ever fatal to a deck.
"""

import json
import logging

import httpx

from app.config import get_settings
from app.errors import UpstreamError

log = logging.getLogger("kya.llm")


class LlmError(UpstreamError):
    """The model call failed, returned nothing usable, or was misconfigured."""


async def chat_json(
    system: str, user: str, schema: dict, *, max_tokens: int = 900
) -> dict:
    settings = get_settings()
    if not settings.openai_api_key:
        raise LlmError("OPENAI_API_KEY not set")

    body = {
        "model": settings.openai_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "picks", "strict": True, "schema": schema},
        },
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }

    try:
        async with httpx.AsyncClient(timeout=settings.openai_timeout) as client:
            resp = await client.post(
                f"{settings.openai_base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json=body,
            )
    except httpx.TimeoutException as e:
        raise LlmError(f"OpenAI timed out after {settings.openai_timeout}s") from e
    except httpx.HTTPError as e:
        raise LlmError(f"couldn't reach OpenAI: {type(e).__name__}") from e

    if resp.status_code != 200:
        # The body can echo request content; truncate it and let redaction do
        # the rest. It goes to the log, never to the client.
        raise LlmError(f"OpenAI {resp.status_code}: {resp.text[:200]}")

    try:
        payload = resp.json()
        content = payload["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as e:
        raise LlmError(f"unexpected OpenAI response shape: {type(e).__name__}") from e

    if content is None:
        # Usually a `max_tokens` cut-off mid-JSON.
        raise LlmError("OpenAI returned an empty completion")

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise LlmError(f"bad JSON from model: {e}") from e
