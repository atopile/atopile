"""
Serve commands for the backend server.
"""

from __future__ import annotations

from typing import Optional

import typer

DEFAULT_DASHBOARD_PORT = 8501

serve_app = typer.Typer(no_args_is_help=True)


@serve_app.command()
def backend(
    port: int = typer.Option(
        DEFAULT_DASHBOARD_PORT,
        help="Port to run the backend server on",
    ),
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
    """Start the backend server in the current terminal."""
    from atopile.server.server import run_server

    run_server(
        port=port,
        force=force,
        ato_source=ato_source,
        ato_binary_path=ato_binary_path,
        ato_local_path=ato_local_path,
        ato_from_branch=ato_from_branch,
        ato_from_spec=ato_from_spec,
    )
