"""Remote asset fetching helpers for UI websocket actions."""

from __future__ import annotations

import asyncio
import base64
import os
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen


def _allowed_hosts() -> set[str]:
    allowed = {
        host.strip()
        for host in os.getenv("ATOPILE_PACKAGES_ASSET_HOSTS", "").split(",")
        if host.strip()
    }
    if allowed:
        return allowed
    return {
        "cloudfront.net",
        "s3.amazonaws.com",
        "s3.us-east-1.amazonaws.com",
        "s3.us-west-2.amazonaws.com",
        "atopileapi.com",
    }


def _is_allowed_host(host: str) -> bool:
    allowed = _allowed_hosts()
    if not allowed:
        return os.getenv("ATOPILE_ALLOW_UNSAFE_ASSET_PROXY", "").lower() in {
            "1",
            "true",
            "yes",
        }
    return host in allowed or any(
        host.endswith(f".{allowed_host}") for allowed_host in allowed
    )


async def proxy_remote_asset(url: str, filename: str | None) -> dict[str, str]:
    """Fetch a whitelisted remote asset and return a base64-encoded payload."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Invalid asset URL")
    if not _is_allowed_host(parsed.netloc):
        raise ValueError("Asset host not allowed")

    def _fetch() -> dict[str, str]:
        with urlopen(url, timeout=30) as response:
            content_type = (
                response.headers.get_content_type() or "application/octet-stream"
            )
            data = response.read()
        return {
            "contentType": content_type,
            "filename": filename or Path(parsed.path).name or "asset",
            "data": base64.b64encode(data).decode("ascii"),
        }

    return await asyncio.to_thread(_fetch)
