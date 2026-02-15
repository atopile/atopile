from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from .bundle_builder import TarZstdBundleBuilder
from .detail_store_sqlite import SQLiteDetailStore
from .fast_lookup_sqlite import SQLiteFastLookupStore
from .interfaces import SnapshotNotFoundError
from .routes import ServeServices, router

DEFAULT_CACHE_DIR = Path("/var/cache/atopile/components")


@dataclass(frozen=True)
class ServeConfig:
    cache_dir: Path
    current_snapshot_name: str = "current"
    fast_db_filename: str = "fast.sqlite"
    detail_db_filename: str = "detail.sqlite"
    host: str = "127.0.0.1"
    port: int = 8079

    @classmethod
    def from_env(cls) -> "ServeConfig":
        return cls(
            cache_dir=Path(
                os.getenv("ATOPILE_COMPONENTS_CACHE_DIR", str(DEFAULT_CACHE_DIR))
            ),
            current_snapshot_name=os.getenv(
                "ATOPILE_COMPONENTS_CURRENT_SNAPSHOT_NAME",
                "current",
            ),
            fast_db_filename=os.getenv(
                "ATOPILE_COMPONENTS_FAST_DB_FILENAME",
                "fast.sqlite",
            ),
            detail_db_filename=os.getenv(
                "ATOPILE_COMPONENTS_DETAIL_DB_FILENAME",
                "detail.sqlite",
            ),
            host=os.getenv("ATOPILE_COMPONENTS_SERVE_HOST", "127.0.0.1"),
            port=int(os.getenv("ATOPILE_COMPONENTS_SERVE_PORT", "8079")),
        )

    @property
    def current_snapshot_path(self) -> Path:
        return self.cache_dir / self.current_snapshot_name

    @property
    def fast_db_path(self) -> Path:
        return self.current_snapshot_path / self.fast_db_filename

    @property
    def detail_db_path(self) -> Path:
        return self.current_snapshot_path / self.detail_db_filename


def build_services(config: ServeConfig) -> ServeServices:
    if not config.current_snapshot_path.exists():
        raise SnapshotNotFoundError(
            f"snapshot path not found: {config.current_snapshot_path}"
        )
    if not config.fast_db_path.exists():
        raise SnapshotNotFoundError(f"fast DB not found: {config.fast_db_path}")
    if not config.detail_db_path.exists():
        raise SnapshotNotFoundError(f"detail DB not found: {config.detail_db_path}")

    fast_lookup = SQLiteFastLookupStore(config.fast_db_path)
    detail_store = SQLiteDetailStore(config.detail_db_path)
    bundle_store = TarZstdBundleBuilder(
        detail_store=detail_store, cache_root=config.cache_dir
    )
    return ServeServices(
        fast_lookup=fast_lookup,
        detail_store=detail_store,
        bundle_store=bundle_store,
    )


def create_app(config: ServeConfig | None = None) -> FastAPI:
    serve_config = config or ServeConfig.from_env()
    app = FastAPI(
        title="atopile-components-serve",
        version="0.1.0",
    )
    app.state.components_config = serve_config
    app.state.components_services = build_services(serve_config)
    app.include_router(router)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {
            "status": "ok",
            "snapshot": str(serve_config.current_snapshot_path),
            "fast_db": str(serve_config.fast_db_path),
            "detail_db": str(serve_config.detail_db_path),
        }

    return app


def main() -> None:
    config = ServeConfig.from_env()
    uvicorn.run(
        create_app(config),
        host=config.host,
        port=config.port,
    )


if __name__ == "__main__":
    main()


def test_serve_config_defaults(monkeypatch) -> None:
    monkeypatch.delenv("ATOPILE_COMPONENTS_CACHE_DIR", raising=False)
    monkeypatch.delenv("ATOPILE_COMPONENTS_SERVE_PORT", raising=False)
    cfg = ServeConfig.from_env()
    assert cfg.cache_dir == DEFAULT_CACHE_DIR
    assert cfg.port == 8079


def test_build_services_requires_snapshot_files(tmp_path) -> None:
    cfg = ServeConfig(cache_dir=tmp_path)
    try:
        build_services(cfg)
    except SnapshotNotFoundError as exc:
        assert "snapshot path not found" in str(exc)
    else:
        assert False, "Expected SnapshotNotFoundError"
