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
    jlc_app_id: str | None
    jlc_access_key: str | None
    jlc_secret_key: str | None
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
                "ATOPILE_COMPONENTS_JLC_API_BASE_URL", "https://open.jlcpcb.com"
            ),
            jlc_app_id=os.getenv("JLC_APP_ID"),
            jlc_access_key=os.getenv("JLC_ACCESS_KEY"),
            jlc_secret_key=os.getenv("JLC_SECRET_KEY"),
            jlc_component_infos_path=os.getenv(
                "ATOPILE_COMPONENTS_JLC_COMPONENT_INFOS_PATH",
                "/overseas/openapi/component/getComponentInfos",
            ),
            jlc_component_detail_path=os.getenv(
                "ATOPILE_COMPONENTS_JLC_COMPONENT_DETAIL_PATH",
                "/overseas/openapi/component/getComponentDetail",
            ),
            request_timeout_s=float(
                os.getenv("ATOPILE_COMPONENTS_FETCH_TIMEOUT_S", "30")
            ),
            target_categories=_csv(os.getenv("ATOPILE_COMPONENTS_TARGET_CATEGORIES")),
        )

    def has_jlc_credentials(self) -> bool:
        return not self.missing_jlc_credentials()

    def missing_jlc_credentials(self) -> tuple[str, ...]:
        missing: list[str] = []
        if not self.jlc_app_id:
            missing.append("JLC_APP_ID")
        if not self.jlc_access_key:
            missing.append("JLC_ACCESS_KEY")
        if not self.jlc_secret_key:
            missing.append("JLC_SECRET_KEY")
        return tuple(missing)


def test_fetch_config_defaults(monkeypatch) -> None:
    for key in (
        "ATOPILE_COMPONENTS_CACHE_DIR",
        "ATOPILE_COMPONENTS_JLC_API_BASE_URL",
        "JLC_APP_ID",
        "JLC_ACCESS_KEY",
        "JLC_SECRET_KEY",
        "ATOPILE_COMPONENTS_JLC_COMPONENT_DETAIL_PATH",
        "ATOPILE_COMPONENTS_TARGET_CATEGORIES",
    ):
        monkeypatch.delenv(key, raising=False)
    cfg = FetchConfig.from_env()
    assert cfg.cache_dir == DEFAULT_CACHE_DIR
    assert cfg.jlc_api_base_url == "https://open.jlcpcb.com"
    expected_detail_path = "/overseas/openapi/component/getComponentDetail"
    assert cfg.jlc_component_detail_path == expected_detail_path
    assert cfg.target_categories == DEFAULT_TARGET_CATEGORIES
    assert not cfg.has_jlc_credentials()
    assert cfg.missing_jlc_credentials() == (
        "JLC_APP_ID",
        "JLC_ACCESS_KEY",
        "JLC_SECRET_KEY",
    )


def test_fetch_config_credentials(monkeypatch) -> None:
    monkeypatch.setenv("JLC_APP_ID", "app-id")
    monkeypatch.setenv("JLC_ACCESS_KEY", "access-key")
    monkeypatch.setenv("JLC_SECRET_KEY", "secret-key")
    cfg = FetchConfig.from_env()
    assert cfg.has_jlc_credentials()
    assert cfg.missing_jlc_credentials() == ()
