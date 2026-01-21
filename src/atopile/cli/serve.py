"""
Serve commands for local backend/frontend development.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer

serve_app = typer.Typer(no_args_is_help=True)


@serve_app.command()
def backend(
    port: int = typer.Option(8501, help="Port to run the backend server on"),
    workspace: Optional[list[Path]] = typer.Option(
        None,
        "--workspace",
        "-w",
        help="Workspace path to scan for projects (can be specified multiple times)",
    ),
    logs_dir: Optional[Path] = typer.Option(
        None, help="Directory for build logs (default: ./build/logs)"
    ),
) -> None:
    """Start the backend server in the current terminal."""
    cmd = [sys.executable, "-m", "atopile.server", "--port", str(port)]
    for path in workspace or []:
        cmd.extend(["--workspace", str(path)])
    if logs_dir:
        cmd.extend(["--logs-dir", str(logs_dir)])

    raise typer.Exit(subprocess.run(cmd).returncode)


@serve_app.command()
def frontend(
    port: int = typer.Option(5173, help="Port to run the UI server on"),
    host: str = typer.Option("127.0.0.1", help="Host to bind the UI server to"),
    backend: Optional[str] = typer.Option(
        None,
        "--backend",
        "-b",
        help="Backend host:port (e.g. localhost:8501)",
    ),
) -> None:
    """Start the UI server (Vite) in the current terminal."""
    repo_root = Path(__file__).resolve().parents[3]
    ui_server_dir = repo_root / "src" / "ui-server"

    if not ui_server_dir.exists():
        raise typer.BadParameter(f"UI server not found at {ui_server_dir}")

    env = None
    if backend:
        backend_host = backend if "://" in backend else f"http://{backend}"
        ws_host = backend_host.replace("http://", "ws://").replace("https://", "wss://")
        env = os.environ.copy()
        env["VITE_API_URL"] = backend_host
        env["VITE_WS_URL"] = f"{ws_host}/ws/state"

    cmd = ["npm", "run", "dev", "--", "--host", host, "--port", str(port)]
    raise typer.Exit(subprocess.run(cmd, cwd=str(ui_server_dir), env=env).returncode)
