from __future__ import annotations

import logging
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Request

from .bundle_builder import TarZstdBundleBuilder
from .detail_store_sqlite import SQLiteDetailStore
from .fast_lookup_sqlite import SQLiteFastLookupStore
from .fast_lookup_zig import ZigFastLookupStore
from .interfaces import SnapshotNotFoundError
from .routes import ServeServices, router
from .telemetry import log_event

DEFAULT_CACHE_DIR = Path("/var/cache/atopile/components")


@dataclass(frozen=True)
class ServeConfig:
    cache_dir: Path
    current_snapshot_name: str = "current"
    fast_db_filename: str = "fast.sqlite"
    fast_engine: str = "zig"
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
            fast_engine=os.getenv("ATOPILE_COMPONENTS_FAST_ENGINE", "zig").strip(),
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
    if not config.detail_db_path.exists():
        raise SnapshotNotFoundError(f"detail DB not found: {config.detail_db_path}")

    engine = config.fast_engine.lower()
    if not config.fast_db_path.exists():
        raise SnapshotNotFoundError(f"fast DB not found: {config.fast_db_path}")
    if engine == "sqlite":
        fast_lookup = SQLiteFastLookupStore(config.fast_db_path)
    elif engine == "zig":
        fast_lookup = ZigFastLookupStore(
            config.fast_db_path,
            cache_root=config.cache_dir,
        )
    else:
        raise SnapshotNotFoundError(
            f"unsupported fast engine: {config.fast_engine!r} "
            "(expected 'sqlite' or 'zig')"
        )

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

    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = request_id
        started_at = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - started_at) * 1000.0, 3)
            log_event(
                "serve.http.unhandled_error",
                level=logging.ERROR,
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                client_ip=request.client.host if request.client else None,
                duration_ms=duration_ms,
                error_type=type(exc).__name__,
            )
            raise

        duration_ms = round((time.perf_counter() - started_at) * 1000.0, 3)
        route = request.scope.get("route")
        route_path = getattr(route, "path", request.url.path)
        response.headers["x-request-id"] = request_id
        log_event(
            "serve.http.request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            route=route_path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            client_ip=request.client.host if request.client else None,
        )
        return response

    @app.on_event("startup")
    async def on_startup() -> None:
        metadata = _load_snapshot_metadata(serve_config.current_snapshot_path)
        package_stats = _load_package_stats(serve_config.detail_db_path)
        log_event(
            "serve.startup",
            host=serve_config.host,
            port=serve_config.port,
            cache_dir=serve_config.cache_dir,
            snapshot=serve_config.current_snapshot_path,
            fast_engine=serve_config.fast_engine,
            fast_db=serve_config.fast_db_path,
            detail_db=serve_config.detail_db_path,
            source_component_count=metadata.get("source_component_count"),
            fast_component_count=metadata.get("fast_component_count"),
            detail_component_count=metadata.get("detail_component_count"),
            built_at_utc=metadata.get("built_at_utc"),
        )
        if package_stats:
            log_event(
                "serve.snapshot.package_stats",
                total_components=package_stats.get("total_components"),
                distinct_packages=package_stats.get("distinct_packages"),
                distinct_packages_by_component_type=package_stats.get(
                    "distinct_packages_by_component_type"
                ),
                top_packages=package_stats.get("top_packages"),
            )

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        log_event(
            "serve.shutdown",
            snapshot=serve_config.current_snapshot_path,
            fast_engine=serve_config.fast_engine,
        )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {
            "status": "ok",
            "snapshot": str(serve_config.current_snapshot_path),
            "fast_db": str(serve_config.fast_db_path),
            "fast_engine": serve_config.fast_engine,
            "detail_db": str(serve_config.detail_db_path),
        }

    return app


def _load_snapshot_metadata(snapshot_path: Path) -> dict[str, Any]:
    metadata_path = snapshot_path / "metadata.json"
    if not metadata_path.exists():
        return {}
    try:
        import json

        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_package_stats(detail_db_path: Path, *, top_n: int = 20) -> dict[str, Any]:
    if not detail_db_path.exists():
        return {}
    try:
        conn = sqlite3.connect(str(detail_db_path))
    except Exception:
        return {}
    try:
        conn.row_factory = sqlite3.Row
        total_components = conn.execute(
            "SELECT COUNT(*) FROM components_full"
        ).fetchone()[0]
        distinct_packages = conn.execute(
            "SELECT COUNT(DISTINCT package) FROM components_full"
        ).fetchone()[0]
        distinct_by_type_rows = conn.execute(
            """
            SELECT component_type, COUNT(DISTINCT package) AS package_count
            FROM components_full
            GROUP BY component_type
            ORDER BY component_type
            """
        ).fetchall()
        top_packages_rows = conn.execute(
            """
            SELECT package, COUNT(*) AS part_count
            FROM components_full
            GROUP BY package
            ORDER BY part_count DESC, package ASC
            LIMIT ?
            """,
            (top_n,),
        ).fetchall()
    except Exception:
        return {}
    finally:
        conn.close()

    return {
        "total_components": int(total_components or 0),
        "distinct_packages": int(distinct_packages or 0),
        "distinct_packages_by_component_type": {
            str(row["component_type"]): int(row["package_count"])
            for row in distinct_by_type_rows
        },
        "top_packages": [
            {"package": str(row["package"]), "part_count": int(row["part_count"])}
            for row in top_packages_rows
        ],
    }


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


def test_create_app_adds_request_id_header(monkeypatch, tmp_path) -> None:
    from fastapi.testclient import TestClient

    class _FastLookup:
        def query_component(self, _component_type, _query):
            return []

        def query_resistors(self, query):
            return self.query_component("resistor", query)

        def query_capacitors(self, query):
            return self.query_component("capacitor", query)

        def query_capacitors_polarized(self, query):
            return self.query_component("capacitor_polarized", query)

        def query_inductors(self, query):
            return self.query_component("inductor", query)

        def query_diodes(self, query):
            return self.query_component("diode", query)

        def query_leds(self, query):
            return self.query_component("led", query)

        def query_bjts(self, query):
            return self.query_component("bjt", query)

        def query_mosfets(self, query):
            return self.query_component("mosfet", query)

    class _Detail:
        def get_components(self, _ids):
            return {}

        def get_asset_manifest(self, _ids):
            return {}

        def lookup_component_ids_by_manufacturer_part(
            self, _manufacturer_name, _part_number, *, limit=50
        ):
            return [][:limit]

    class _Bundle:
        def build_bundle(self, _ids):
            raise AssertionError("bundle path should not be called in this test")

    monkeypatch.setattr(
        "components.serve.main.build_services",
        lambda _cfg: ServeServices(
            fast_lookup=_FastLookup(),
            detail_store=_Detail(),
            bundle_store=_Bundle(),
        ),
    )
    app = create_app(ServeConfig(cache_dir=tmp_path))
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.headers.get("x-request-id")


def test_load_package_stats_reads_detail_db(tmp_path) -> None:
    db_path = tmp_path / "detail.sqlite"
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE components_full (
                lcsc_id INTEGER PRIMARY KEY,
                component_type TEXT NOT NULL,
                package TEXT NOT NULL
            );
            INSERT INTO components_full (lcsc_id, component_type, package) VALUES
                (1, 'resistor', '0402'),
                (2, 'resistor', '0603'),
                (3, 'capacitor', '0402');
            """
        )
        conn.commit()
    finally:
        conn.close()

    stats = _load_package_stats(db_path, top_n=5)
    assert stats["total_components"] == 3
    assert stats["distinct_packages"] == 2
    assert stats["distinct_packages_by_component_type"] == {
        "capacitor": 1,
        "resistor": 2,
    }
    assert stats["top_packages"][0]["package"] == "0402"
    assert stats["top_packages"][0]["part_count"] == 2
