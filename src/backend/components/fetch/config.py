from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CACHE_DIR = Path("/var/cache/atopile/components")
DEFAULT_TARGET_CATEGORIES = ("Resistors", "Capacitors")


def _csv(value: str | None) -> tuple[str, ...]:
    if not value:
        return DEFAULT_TARGET_CATEGORIES
    parsed = tuple(part.strip() for part in value.split(",") if part.strip())
    return parsed or DEFAULT_TARGET_CATEGORIES


@dataclass(frozen=True)
class FetchConfig:
    cache_dir: Path
    jlc_api_base_url: str
    jlc_app_key: str | None
    jlc_app_secret: str | None
    jlc_token_path: str
    jlc_component_infos_path: str
    jlc_component_detail_path: str
    request_timeout_s: float
    target_categories: tuple[str, ...]

    @classmethod
    def from_env(cls) -> FetchConfig:
        return cls(
            cache_dir=Path(
                os.getenv("ATOPILE_COMPONENTS_CACHE_DIR", str(DEFAULT_CACHE_DIR))
            ),
            jlc_api_base_url=os.getenv(
                "ATOPILE_COMPONENTS_JLC_API_BASE_URL", "https://jlcpcb.com"
            ),
            jlc_app_key=os.getenv("JLC_API_KEY"),
            jlc_app_secret=os.getenv("JLC_API_SECRET"),
            jlc_token_path=os.getenv(
                "ATOPILE_COMPONENTS_JLC_TOKEN_PATH", "/external/genToken"
            ),
            jlc_component_infos_path=os.getenv(
                "ATOPILE_COMPONENTS_JLC_COMPONENT_INFOS_PATH",
                "/external/component/getComponentInfos",
            ),
            jlc_component_detail_path=os.getenv(
                "ATOPILE_COMPONENTS_JLC_COMPONENT_DETAIL_PATH",
                "/external/component/getComponentDetail",
            ),
            request_timeout_s=float(
                os.getenv("ATOPILE_COMPONENTS_FETCH_TIMEOUT_S", "30")
            ),
            target_categories=_csv(os.getenv("ATOPILE_COMPONENTS_TARGET_CATEGORIES")),
        )

    def has_jlc_credentials(self) -> bool:
        return bool(self.jlc_app_key and self.jlc_app_secret)


def test_fetch_config_defaults(monkeypatch) -> None:
    for key in (
        "ATOPILE_COMPONENTS_CACHE_DIR",
        "ATOPILE_COMPONENTS_JLC_API_BASE_URL",
        "JLC_API_KEY",
        "JLC_API_SECRET",
        "ATOPILE_COMPONENTS_JLC_COMPONENT_DETAIL_PATH",
        "ATOPILE_COMPONENTS_TARGET_CATEGORIES",
    ):
        monkeypatch.delenv(key, raising=False)
    cfg = FetchConfig.from_env()
    assert cfg.cache_dir == DEFAULT_CACHE_DIR
    assert cfg.jlc_api_base_url == "https://jlcpcb.com"
    assert cfg.jlc_component_detail_path == "/external/component/getComponentDetail"
    assert cfg.target_categories == DEFAULT_TARGET_CATEGORIES
    assert not cfg.has_jlc_credentials()


def test_fetch_config_credentials(monkeypatch) -> None:
    monkeypatch.setenv("JLC_API_KEY", "key")
    monkeypatch.setenv("JLC_API_SECRET", "secret")
    cfg = FetchConfig.from_env()
    assert cfg.has_jlc_credentials()
