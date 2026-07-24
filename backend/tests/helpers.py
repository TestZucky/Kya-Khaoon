"""Shared test helper: run the OTP login and return an auth header."""

from fastapi.testclient import TestClient


def login(client: TestClient, phone: str) -> dict[str, str]:
    """request-otp → verify-otp (console provider hands back the code)."""
    code = client.post("/auth/request-otp", json={"phone": phone}).json()["dev_code"]
    token = client.post(
        "/auth/verify-otp", json={"phone": phone, "code": code}
    ).json()["token"]
    return {"Authorization": f"Bearer {token}"}
