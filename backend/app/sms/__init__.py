"""
Pluggable SMS delivery — same shape as the Swiggy client.

`console` (default) logs the message and never sends anything, so the whole OTP
flow works in dev with no provider account. `twilio` sends a real SMS once
credentials are set. Swapping is one env var: SMS_PROVIDER.
"""

from typing import Protocol

from app.config import get_settings


class SmsSender(Protocol):
    async def send(self, *, to: str, body: str) -> None: ...


def get_sms_sender() -> SmsSender:
    if get_settings().sms_provider == "twilio":
        from app.sms.twilio import TwilioSmsSender

        return TwilioSmsSender()
    from app.sms.console import ConsoleSmsSender

    return ConsoleSmsSender()
