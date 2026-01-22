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

from atopile.server.server import DASHBOARD_PORT

serve_app = typer.Typer(no_args_is_help=True)


def read_port_file(workspace: Path | None = None) -> int | None:
    """Read the backend port from the port file if it exists."""
    search_paths = []
    if workspace:
        search_paths.append(workspace / ".atopile" / ".server_port")
    search_paths.append(Path.cwd() / ".atopile" / ".server_port")

    for port_file in search_paths:
        if port_file.exists():
            try:
                return int(port_file.read_text().strip())
            except (ValueError, OSError):
                continue
    return None


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
    port: int = typer.Option(DASHBOARD_PORT, help="Port to run the backend server on"),
    workspace: Optional[list[Path]] = typer.Option(
        None,
        "--workspace",
        "-w",
        help="Workspace path to scan for projects (can be specified multiple times)",
    ),
    logs_dir: Optional[Path] = typer.Option(
        None, help="Directory for build logs (default: ./build/logs)"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Kill existing server on the port and start fresh",
    ),
    auto_port: bool = typer.Option(
        False,
        "--auto-port",
        help="Automatically find a free port if the default is in use",
    ),
) -> None:
    """Start the backend server in the current terminal."""
    cmd = [sys.executable, "-m", "atopile.server", "--port", str(port)]
    for path in workspace or []:
        cmd.extend(["--workspace", str(path)])
    if logs_dir:
        cmd.extend(["--logs-dir", str(logs_dir)])
    if force:
        cmd.append("--force")
    if auto_port:
        cmd.append("--auto-port")

    raise typer.Exit(subprocess.run(cmd).returncode)


@serve_app.command()
def frontend(
    port: int = typer.Option(5173, help="Port to run the UI server on"),
    host: str = typer.Option("127.0.0.1", help="Host to bind the UI server to"),
    backend: Optional[str] = typer.Option(
        None,
        "--backend",
        "-b",
        help="Backend host:port (e.g. localhost:{DASHBOARD_PORT}). Auto-detected from port file if not specified.",  # noqa: E501
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

    # Auto-detect backend port from port file if not specified
    backend_port = DASHBOARD_PORT
    if backend:
        # Use explicitly specified backend
        backend_host = backend if "://" in backend else f"http://{backend}"
    else:
        # Try to read port from port file
        discovered_port = read_port_file()
        if discovered_port:
            backend_port = discovered_port
            print(f"Auto-detected backend on port {backend_port} from port file")
        backend_host = f"http://localhost:{backend_port}"

    ws_host = backend_host.replace("http://", "ws://").replace("https://", "wss://")
    env = os.environ.copy()
    env["VITE_API_URL"] = backend_host
    env["VITE_WS_URL"] = f"{ws_host}/ws/state"

    print(f"Frontend connecting to backend at {backend_host}")

    cmd = ["npm", "run", "dev", "--", "--host", host, "--port", str(port)]
    raise typer.Exit(subprocess.run(cmd, cwd=str(ui_server_dir), env=env).returncode)
