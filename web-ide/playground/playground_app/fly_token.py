from __future__ import annotations

import os
import shutil
import subprocess


class FlyTokenError(RuntimeError):
    pass


def resolve_fly_api_token(timeout_seconds: float = 5.0) -> str:
    env_token = os.environ.get("FLY_API_TOKEN", "").strip()
    if env_token:
        return env_token

    fly_bin = shutil.which("fly") or shutil.which("flyctl")
    if fly_bin:
        try:
            result = subprocess.run(
                [fly_bin, "auth", "token"],
                check=False,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
            )
            token = result.stdout.strip()
            if result.returncode == 0 and token:
                return token
        except (OSError, subprocess.TimeoutExpired):
            pass

    raise FlyTokenError(
        "FLY_API_TOKEN not configured. Set FLY_API_TOKEN or run `fly auth login` so `fly auth token` can be used."
    )
