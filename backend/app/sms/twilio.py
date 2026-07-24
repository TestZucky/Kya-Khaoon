"""
Real SMS via Twilio's Messages API. One authenticated POST — no SDK needed.

For India specifically you'll more likely use MSG91 / Fast2SMS with a
DLT-registered template; that's the same `SmsSender.send` with a different HTTP
call, so only this file changes.
"""

import logging

import httpx

from app.config import get_settings
from app.errors import UpstreamError
from app.logging_config import mask_phone

log = logging.getLogger("kya.sms")


class TwilioSmsSender:
    def __init__(self) -> None:
        s = get_settings()
        if not (s.twilio_account_sid and s.twilio_auth_token and s.twilio_from):
            raise RuntimeError(
                "SMS_PROVIDER=twilio requires TWILIO_ACCOUNT_SID, "
                "TWILIO_AUTH_TOKEN and TWILIO_FROM"
            )
        self._sid = s.twilio_account_sid
        self._token = s.twilio_auth_token
        self._from = s.twilio_from

    async def send(self, *, to: str, body: str) -> None:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self._sid}/Messages.json"
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    url,
                    auth=(self._sid, self._token),
                    data={"To": to, "From": self._from, "Body": body},
                )
                resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            # Twilio's error body names the account and the number; keep it out
            # of the log and report only the status.
            raise UpstreamError(f"Twilio rejected the message ({e.response.status_code})") from e
        except httpx.HTTPError as e:
            raise UpstreamError(f"couldn't reach Twilio: {type(e).__name__}") from e
        log.info("sms sent to %s", mask_phone(to))
