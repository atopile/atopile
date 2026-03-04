from __future__ import annotations

import hashlib
import hmac
import secrets

from fastapi import Response


class SessionSigner:
    def __init__(self, cookie_name: str, max_age_seconds: int, fly_api_token: str):
        self.cookie_name = cookie_name
        self.max_age_seconds = max_age_seconds
        self._secret = hashlib.sha256(f"playground-hmac:{fly_api_token}".encode("utf-8")).digest()

    def sign(self, machine_id: str) -> str:
        tag = hmac.new(
            self._secret,
            machine_id.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"{machine_id}.{tag}"

    def verify(self, value: str | None) -> str | None:
        if not value:
            return None
        dot = value.rfind(".")
        if dot == -1:
            return None
        machine_id = value[:dot]
        provided = value[dot + 1 :]
        expected = hmac.new(
            self._secret,
            machine_id.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not secrets.compare_digest(provided, expected):
            return None
        return machine_id

    def set_session_cookie(self, response: Response, machine_id: str) -> None:
        response.set_cookie(
            key=self.cookie_name,
            value=self.sign(machine_id),
            httponly=True,
            samesite="lax",
            path="/",
            max_age=self.max_age_seconds,
        )

    def clear_session_cookie(self, response: Response) -> None:
        response.delete_cookie(self.cookie_name, path="/")
