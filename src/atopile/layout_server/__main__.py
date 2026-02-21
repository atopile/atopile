"""Standalone layout-editor server.

CLI entry point: ``python -m atopile.layout_server <path.kicad_pcb> [--port 8100]``.

Only the CLI, the ``create_app`` factory, and the index / static-file serving
live here.  All API routes and the ``LayoutService`` are shared with the
backend integration server.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path

import typer
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from atopile.layout_server.server import create_layout_router
from atopile.server.domains.layout import LayoutService

log = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"
FRONTEND_DIR = Path(__file__).parent / "frontend"
TEMPLATE_PATH = STATIC_DIR / "layout-editor.hbs"


# ---------------------------------------------------------------------------
# Template rendering
# ---------------------------------------------------------------------------


def _render_layout_template(
    *,
    api_url: str,
    api_prefix: str,
    ws_path: str,
    editor_uri: str,
    nonce: str = "",
    csp: str,
) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    values = {
        "apiUrl": api_url,
        "apiPrefix": api_prefix,
        "wsPath": ws_path,
        "editorUri": editor_uri,
        "nonce": nonce,
        "csp": csp,
    }
    for key, value in values.items():
        template = template.replace(f"{{{{{key}}}}}", value)
    return template


# ---------------------------------------------------------------------------
# FastAPI application factory
# ---------------------------------------------------------------------------


def create_app(pcb_path: Path) -> FastAPI:
    service = LayoutService()
    service.load(pcb_path)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        await service.start_watcher()
        yield

    app = FastAPI(title="PCB Layout Editor", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Shared layout routes at /api/* and /ws
    app.include_router(create_layout_router(service, api_prefix="/api", ws_path="/ws"))

    # --- Static files & index page ---

    @app.get("/")
    async def index():
        html = _render_layout_template(
            api_url="",
            api_prefix="/api",
            ws_path="/ws",
            editor_uri="/static/editor.js",
            csp=(
                "default-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "script-src 'self' 'unsafe-inline'; "
                "connect-src 'self' ws: wss:;"
            ),
        )
        return HTMLResponse(html)

    app.mount(
        "/static",
        StaticFiles(directory=str(STATIC_DIR)),
        name="static",
    )

    return app


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _ensure_editor_bundle() -> None:
    editor_js = STATIC_DIR / "editor.js"
    if editor_js.is_file():
        return

    npm = shutil.which("npm")
    if not npm:
        raise RuntimeError(
            "Layout editor bundle is missing and npm is not installed. "
            "Run `npm --prefix src/atopile/layout_server/frontend run build`."
        )
    if not FRONTEND_DIR.is_dir():
        raise RuntimeError(
            f"Layout frontend source directory not found: {FRONTEND_DIR}"
        )

    typer.echo("Layout editor bundle missing; building frontend assets...", err=True)
    result = subprocess.run([npm, "run", "build"], cwd=str(FRONTEND_DIR), check=False)
    if result.returncode != 0:
        raise RuntimeError(
            "Failed to build layout editor bundle. "
            "Run `npm --prefix src/atopile/layout_server/frontend run build`."
        )
    if not editor_js.is_file():
        raise RuntimeError(
            "Layout editor build reported success but `editor.js` is still missing."
        )


def main(
    pcb_path: Path = typer.Argument(..., help="Path to .kicad_pcb file"),
    port: int = typer.Option(8100, help="Server port"),
    host: str = typer.Option("127.0.0.1", help="Server host"),
) -> None:
    if not pcb_path.is_file():
        raise typer.BadParameter(f"File not found: {pcb_path}", param_hint="pcb_path")
    try:
        _ensure_editor_bundle()
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    import uvicorn

    uvicorn.run(create_app(pcb_path), host=host, port=port)


if __name__ == "__main__":
    typer.run(main)
