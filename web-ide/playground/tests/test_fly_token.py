from __future__ import annotations

import subprocess

import pytest

from playground_app.fly_token import FlyTokenError, resolve_fly_api_token


def test_resolve_token_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FLY_API_TOKEN", "env-token")
    assert resolve_fly_api_token() == "env-token"


def test_resolve_token_from_flyctl(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FLY_API_TOKEN", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: "fly" if name == "fly" else None)

    def fake_run(*args, **kwargs):  # noqa: ANN002, ANN003
        _ = args, kwargs
        return subprocess.CompletedProcess(
            args=["fly", "auth", "token"],
            returncode=0,
            stdout="fly-token\n",
            stderr="",
        )

    monkeypatch.setattr("subprocess.run", fake_run)

    assert resolve_fly_api_token() == "fly-token"


def test_resolve_token_raises_when_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FLY_API_TOKEN", raising=False)
    monkeypatch.setattr("shutil.which", lambda _: None)
    with pytest.raises(FlyTokenError):
        resolve_fly_api_token()
