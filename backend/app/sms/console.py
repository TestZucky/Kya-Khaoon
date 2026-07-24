import logging

from app.logging_config import mask_phone

log = logging.getLogger("kya.otp")


class ConsoleSmsSender:
    """
    Dev sender: prints the message to the server log instead of texting it.

    The destination number is masked — a log line outlives the request and this
    one would otherwise pair a real phone number with a live credential. The code
    itself is printed because that is the entire point of this provider, and it
    is also returned as `dev_code`. Never select `console` outside development.
    """

    async def send(self, *, to: str, body: str) -> None:
        log.warning("[dev SMS → %s] %s", mask_phone(to), body)
