"""
Serve commands for the core server and hub.

Both commands read their port assignments from environment variables
set by the VS Code extension:
  ATOPILE_HUB_PORT         — port the hub listens on
  ATOPILE_CORE_SERVER_PORT — port the core server listens on
"""

from __future__ import annotations

import os
from typing import Optional

import typer

HUB_PORT_ENV = "ATOPILE_HUB_PORT"
CORE_SERVER_PORT_ENV = "ATOPILE_CORE_SERVER_PORT"

serve_app = typer.Typer(no_args_is_help=True)


def _require_env_port(name: str) -> int:
    """Read a required port from an environment variable."""
    raw = os.environ.get(name)
    if not raw:
        raise typer.BadParameter(f"Environment variable {name} is required")
    try:
        return int(raw)
    except ValueError:
        raise typer.BadParameter(f"{name}={raw!r} is not a valid port number")


@serve_app.command()
def hub() -> None:
    """Start the WebSocket hub (relays between webviews and core server)."""
    from ui.hub import run_hub

    port = _require_env_port(HUB_PORT_ENV)
    run_hub(port=port)


@serve_app.command()
def core(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Kill existing server on the port and start fresh",
    ),
    ato_source: Optional[str] = typer.Option(
        None,
        "--ato-source",
        help="Source of the atopile binary (e.g., 'settings', 'local-uv')",
    ),
    ato_binary_path: Optional[str] = typer.Option(
        None,
        "--ato-binary-path",
        help="Actual resolved path to the ato binary being used",
    ),
    ato_local_path: Optional[str] = typer.Option(
        None,
        "--ato-local-path",
        help="Local path to display in the UI (when in local mode)",
    ),
    ato_from_branch: Optional[str] = typer.Option(
        None,
        "--ato-from-branch",
        help="Git branch name when installed from git via uv",
    ),
    ato_from_spec: Optional[str] = typer.Option(
        None,
        "--ato-from-spec",
        help="The pip/uv spec used to install atopile"
        " (e.g., 'atopile==0.14.0' or git URL)",
    ),
) -> None:
    """Start the core server in the current terminal."""
    from atopile.dataclasses import AppContext
    from atopile.server.server import CoreServer

    port = _require_env_port(CORE_SERVER_PORT_ENV)
    ctx = AppContext(
        ato_source=ato_source,
        ato_local_path=ato_local_path,
        ato_binary_path=ato_binary_path,
        ato_from_branch=ato_from_branch,
        ato_from_spec=ato_from_spec,
    )

    CoreServer(port=port, force=force, ctx=ctx).run()
