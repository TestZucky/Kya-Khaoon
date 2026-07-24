"""
Readable, colourful, PII-safe logs.

Two things this file exists for:

1. **Colour.** A dev tailing the server should see at a glance which line is an
   error and which is a routine request. Colour is auto-disabled when stdout
   isn't a terminal (or `NO_COLOR` is set), so piped and captured logs stay clean.
2. **Redaction.** Log lines outlive the request and end up in files, terminals
   and log aggregators. Phone numbers, emails, OAuth tokens and API keys must
   never reach any of those, so a filter scrubs them from every record — including
   ones written by libraries we don't control.

Log a masked value on purpose (`mask_phone`) rather than relying on the filter:
the filter is the safety net, not the plan.
"""

import logging
import os
import re
import sys

RESET = "\033[0m"
DIM = "\033[2m"
BOLD = "\033[1m"

_LEVEL_COLOUR = {
    logging.DEBUG: "\033[36m",  # cyan
    logging.INFO: "\033[32m",  # green
    logging.WARNING: "\033[33m",  # yellow
    logging.ERROR: "\033[31m",  # red
    logging.CRITICAL: "\033[97;41m",  # white on red
}

STATUS_COLOUR = {2: "\033[32m", 3: "\033[36m", 4: "\033[33m", 5: "\033[31m"}

# Kept to five characters so the message column always lines up.
_LEVEL_NAME = {logging.WARNING: "WARN", logging.CRITICAL: "CRIT"}


def colour_enabled() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


# ── Redaction ───────────────────────────────────────────────────────────────
# Deliberately blunt. A false positive costs a masked log line; a false negative
# leaks a credential, so the patterns lean greedy.
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?i)\b(bearer)\s+[\w\-.~+/=]{8,}"), r"\1 «token»"),
    (re.compile(r"\bsk-[A-Za-z0-9\-_]{8,}"), "«api-key»"),
    (
        re.compile(
            r"(?i)\b(authorization|api[-_]?key|access_token|refresh_token|id_token"
            r"|client_secret|code_verifier|password|secret)"
            r"([\"']?\s*[:=]\s*[\"']?)[^\s,;\"'}\)]+"
        ),
        r"\1\2«redacted»",
    ),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b"), "«email»"),
    (re.compile(r"(?<!\d)(\+?\d{1,3}[- ]?)?(\d{2})\d{5,7}(\d{3})(?!\d)"), r"\1\2•••••\3"),
]


def redact(text: str) -> str:
    """Scrub anything that looks like a credential or personal identifier."""
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class RedactingFilter(logging.Filter):
    """Redacts the rendered message of every record, ours or a library's."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            rendered = record.getMessage()
        except (TypeError, ValueError):
            return True
        cleaned = redact(rendered)
        if cleaned != rendered:
            record.msg = cleaned
            record.args = ()
        return True


def mask_phone(phone: str) -> str:
    """`+919876543210` → `+91987•••210`. Enough to correlate, not to identify."""
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) < 6:
        return "•••"
    prefix = "+" if phone.startswith("+") else ""
    return f"{prefix}{digits[:-7]}{'•' * 4}{digits[-3:]}"


def mask_email(email: str) -> str:
    name, _, domain = email.partition("@")
    if not domain:
        return "•••"
    return f"{name[:1]}•••@{domain}"


def mask_token(token: str | None) -> str:
    """A token's last 4 chars — enough to tell two sessions apart in a log."""
    if not token:
        return "«none»"
    return f"…{token[-4:]}" if len(token) > 4 else "«short»"


# ── Formatting ──────────────────────────────────────────────────────────────
class ColourFormatter(logging.Formatter):
    """`14:22:01 INFO  kya.deck  built deck of 5`, with the level colourised."""

    def __init__(self, *, colour: bool) -> None:
        super().__init__(datefmt="%H:%M:%S")
        self.colour = colour

    def format(self, record: logging.LogRecord) -> str:
        time = self.formatTime(record, self.datefmt)
        level = _LEVEL_NAME.get(record.levelno, record.levelname)[:5].ljust(5)
        name = record.name
        message = record.getMessage()

        if self.colour:
            level_colour = _LEVEL_COLOUR.get(record.levelno, "")
            time = f"{DIM}{time}{RESET}"
            level = f"{level_colour}{BOLD}{level}{RESET}"
            name = f"{DIM}{name}{RESET}"

        line = f"{time} {level} {name}  {message}"
        if record.exc_info:
            line = f"{line}\n{self.formatException(record.exc_info)}"
        return line


def setup_logging(level: str = "info") -> None:
    """Install the formatter and redaction filter on the root logger."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ColourFormatter(colour=colour_enabled()))
    handler.addFilter(RedactingFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Uvicorn ships its own handlers; drop them so every line goes through ours
    # (and therefore through the redaction filter). Its access log is redundant
    # with our request middleware, which reports duration too.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers = []
        logger.propagate = True
    logging.getLogger("uvicorn.access").disabled = True

    # httpx logs every outbound request at INFO, URLs included.
    logging.getLogger("httpx").setLevel(logging.WARNING)
