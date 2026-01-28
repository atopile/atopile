"""
Serve commands for local backend/frontend development.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer

DEFAULT_DASHBOARD_PORT = 8501

serve_app = typer.Typer(no_args_is_help=True)


def _install_nodejs() -> Optional[int]:
    if sys.platform == "darwin":
        if shutil.which("brew"):
            return subprocess.run(["brew", "install", "node"]).returncode
        return None
    if sys.platform.startswith("linux"):
        if shutil.which("apt-get"):
            return subprocess.run(
                ["sudo", "apt-get", "install", "-y", "nodejs", "npm"]
            ).returncode
        if shutil.which("dnf"):
            return subprocess.run(
                ["sudo", "dnf", "install", "-y", "nodejs", "npm"]
            ).returncode
        if shutil.which("yum"):
            return subprocess.run(
                ["sudo", "yum", "install", "-y", "nodejs", "npm"]
            ).returncode
        if shutil.which("pacman"):
            return subprocess.run(
                ["sudo", "pacman", "-S", "--noconfirm", "nodejs", "npm"]
            ).returncode
        return None
    if sys.platform == "win32":
        if shutil.which("choco"):
            return subprocess.run(["choco", "install", "-y", "nodejs"]).returncode
        if shutil.which("winget"):
            return subprocess.run(
                ["winget", "install", "-e", "--id", "OpenJS.NodeJS"]
            ).returncode
        return None
    return None


@serve_app.command()
def backend(
    port: int = typer.Option(
        DEFAULT_DASHBOARD_PORT,
        help="Port to run the backend server on",
    ),
    workspace: Optional[list[Path]] = typer.Option(
        None,
        "--workspace",
        "-w",
        help="Workspace path to scan for projects (can be specified multiple times)",
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
    ato_ui_source: Optional[str] = typer.Option(
        None,
        "--ato-ui-source",
        help="UI source type (e.g., 'release', 'branch', 'local')",
    ),
    ato_binary_path: Optional[str] = typer.Option(
        None,
        "--ato-binary-path",
        help="Actual resolved path to the ato binary being used",
    ),
) -> None:
    """Start the backend server in the current terminal."""
    from atopile.server.server import run_server

    workspace_paths = list(workspace) if workspace else None
    run_server(port=port, workspace_paths=workspace_paths, force=force)


@serve_app.command()
def frontend(
    port: int = typer.Option(5173, help="Port to run the UI server on"),
    host: str = typer.Option("127.0.0.1", help="Host to bind the UI server to"),
    backend: Optional[str] = typer.Option(
        None,
        "--backend",
        "-b",
        help=f"Backend host:port (e.g. localhost:{DEFAULT_DASHBOARD_PORT}).",
    ),
) -> None:
    """Start the UI server (Vite) in the current terminal."""
    repo_root = Path(__file__).resolve().parents[3]
    ui_server_dir = repo_root / "src" / "ui-server"

    if not ui_server_dir.exists():
        raise typer.BadParameter(f"UI server not found at {ui_server_dir}")

    if not shutil.which("npm"):
        if not typer.confirm(
            "npm not found. Attempt to install Node.js now?", default=False
        ):
            raise typer.BadParameter("npm is required to serve the frontend.")
        result = _install_nodejs()
        if result is None:
            raise typer.BadParameter(
                "No supported package manager found. Install Node.js from https://nodejs.org/"
            )
        if result != 0:
            raise typer.Exit(result)
        if not shutil.which("npm"):
            raise typer.BadParameter(
                "npm is still missing after installation attempt. Install Node.js from https://nodejs.org/"
            )

    node_modules_dir = ui_server_dir / "node_modules"
    vite_bin = node_modules_dir / ".bin" / ("vite.cmd" if os.name == "nt" else "vite")
    if not node_modules_dir.exists() or not vite_bin.exists():
        install_cmd = ["npm", "install"]
        result = subprocess.run(install_cmd, cwd=str(ui_server_dir))
        if result.returncode != 0:
            raise typer.Exit(result.returncode)

    dist_dir = ui_server_dir / "dist"
    if not dist_dir.exists():
        build_cmd = ["npm", "run", "build"]
        result = subprocess.run(build_cmd, cwd=str(ui_server_dir))
        if result.returncode != 0:
            raise typer.Exit(result.returncode)

    if backend:
        backend_host = backend if "://" in backend else f"http://{backend}"
    else:
        backend_host = f"http://localhost:{DEFAULT_DASHBOARD_PORT}"

    ws_host = backend_host.replace("http://", "ws://").replace("https://", "wss://")
    env = os.environ.copy()
    env["VITE_API_URL"] = backend_host
    env["VITE_WS_URL"] = f"{ws_host}/ws/state"

    print(f"Frontend connecting to backend at {backend_host}")

    cmd = ["npm", "run", "dev", "--", "--host", host, "--port", str(port)]
    raise typer.Exit(subprocess.run(cmd, cwd=str(ui_server_dir), env=env).returncode)
