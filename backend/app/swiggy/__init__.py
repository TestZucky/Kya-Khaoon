from typing import TYPE_CHECKING

from app.config import get_settings
from app.swiggy.client import Address, MenuItem, RestaurantInfo, SwiggyClient
from app.swiggy.fake import FakeSwiggyClient

if TYPE_CHECKING:
    from app.models import User

__all__ = [
    "Address",
    "MenuItem",
    "RestaurantInfo",
    "SwiggyClient",
    "get_swiggy_client",
    "swiggy_for_user",
]


def get_swiggy_client() -> SwiggyClient:
    """Config-driven pick. Used where there's no specific user (rare)."""
    settings = get_settings()
    if settings.swiggy_client == "mcp":
        from app.swiggy.mcp import McpSwiggyClient

        return McpSwiggyClient()
    return FakeSwiggyClient()


def swiggy_for_user(user: "User") -> SwiggyClient:
    """
    Real Swiggy for a connected user, fake otherwise. Presence of the user's
    OAuth token (plus a configured MCP URL) is what flips it to real — so the app
    works for everyone and gets real the moment they tap "Connect Swiggy".
    """
    settings = get_settings()
    if user.swiggy_token and settings.swiggy_mcp_url:
        from app.swiggy.mcp import McpSwiggyClient

        return McpSwiggyClient()
    return FakeSwiggyClient()
