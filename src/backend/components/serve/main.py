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
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles

from .bundle_builder import TarZstdBundleBuilder
from .dashboard_metrics import DashboardMetrics
from .dashboard_routes import router as dashboard_router
from .detail_store_sqlite import SQLiteDetailStore
from .fast_lookup_zig import ZigFastLookupStore
from .interfaces import SnapshotNotFoundError
from .routes import ServeServices, router
from .telemetry import log_event, set_dashboard_metrics

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
    if not config.detail_db_path.exists():
        raise SnapshotNotFoundError(f"detail DB not found: {config.detail_db_path}")

    if not config.fast_db_path.exists():
        raise SnapshotNotFoundError(f"fast DB not found: {config.fast_db_path}")
    fast_lookup = ZigFastLookupStore(
        config.fast_db_path,
        cache_root=config.cache_dir,
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
    dashboard_metrics = DashboardMetrics()
    app = FastAPI(
        title="atopile-components-serve",
        version="0.1.0",
    )
    app.state.components_config = serve_config
    app.state.components_services = build_services(serve_config)
    app.state.dashboard_metrics = dashboard_metrics
    app.state.snapshot_package_stats = {}
    set_dashboard_metrics(dashboard_metrics)
    app.include_router(dashboard_router)
    app.include_router(router)
    _mount_dashboard_frontend(app)

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
        app.state.snapshot_package_stats = package_stats
        log_event(
            "serve.startup",
            host=serve_config.host,
            port=serve_config.port,
            cache_dir=serve_config.cache_dir,
            snapshot=serve_config.current_snapshot_path,
            fast_engine="zig",
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
        set_dashboard_metrics(None)
        log_event(
            "serve.shutdown",
            snapshot=serve_config.current_snapshot_path,
            fast_engine="zig",
        )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {
            "status": "ok",
            "snapshot": str(serve_config.current_snapshot_path),
            "fast_db": str(serve_config.fast_db_path),
            "fast_engine": "zig",
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


def _resolve_dashboard_dist_path() -> Path:
    return Path(__file__).resolve().parents[2] / "dashboard" / "dist"


def _mount_dashboard_frontend(app: FastAPI) -> None:
    dashboard_dist = _resolve_dashboard_dist_path()
    app.state.dashboard_dist_path = dashboard_dist
    index_path = dashboard_dist / "index.html"
    if dashboard_dist.exists() and index_path.exists():
        app.mount(
            "/dashboard",
            StaticFiles(directory=str(dashboard_dist), html=True),
            name="components-dashboard",
        )
        return

    help_text = (
        "Dashboard frontend not built.\n"
        "Run from src/backend/dashboard:\n"
        "  npm install\n"
        "  npm run build\n"
        "Then restart the components serve API.\n"
    )

    @app.get("/dashboard", include_in_schema=False)
    def dashboard_not_built() -> PlainTextResponse:
        return PlainTextResponse(help_text, status_code=503)

    @app.get("/dashboard/{path:path}", include_in_schema=False)
    def dashboard_not_built_nested(path: str) -> PlainTextResponse:
        del path
        return PlainTextResponse(help_text, status_code=503)


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
    dashboard_response = client.get("/v1/dashboard/metrics")
    assert dashboard_response.status_code == 200
    payload = dashboard_response.json()
    assert "services" in payload
    assert "http" in payload


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


def test_resolve_dashboard_dist_path() -> None:
    dashboard_dist = _resolve_dashboard_dist_path()
    assert dashboard_dist.parts[-3:] == ("backend", "dashboard", "dist")
