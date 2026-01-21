"""
CLI command to start the atopile dashboard server.

The server provides API endpoints for build execution and status monitoring.
"""

import logging
import socket
import subprocess
import sys
from typing import Annotated

import typer

from atopile.dashboard.server import DEFAULT_PORT, start_dashboard_server

logger = logging.getLogger(__name__)

serve_app = typer.Typer()


def _is_port_in_use(port: int) -> bool:
    """Check if a port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def _find_process_on_port(port: int) -> list[int]:
    """Find process IDs listening on the given port."""
    pids = []
    try:
        # Use lsof to find processes on the port (works on macOS and Linux)
        result = subprocess.run(
            ["lsof", "-t", "-i", f":{port}"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if line:
                    pids.append(int(line))
    except (subprocess.SubprocessError, FileNotFoundError, ValueError):
        pass
    return pids


def _kill_process(pid: int) -> bool:
    """Kill a process by PID."""
    import os
    import signal

    try:
        os.kill(pid, signal.SIGTERM)
        return True
    except OSError:
        return False


@serve_app.command()
def start(
    port: Annotated[
        int,
        typer.Option("--port", "-p", help="Port to run the server on"),
    ] = DEFAULT_PORT,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Kill any existing server on the port"),
    ] = False,
):
    """Start the atopile dashboard server."""
    import signal
    import time

    # Check if port is already in use
    if _is_port_in_use(port):
        if force:
            print(f"Port {port} is in use, stopping existing server...")
            pids = _find_process_on_port(port)
            for pid in pids:
                _kill_process(pid)
            # Wait for port to be released
            for _ in range(20):  # Wait up to 2 seconds
                if not _is_port_in_use(port):
                    break
                time.sleep(0.1)
            else:
                print(f"Error: Could not stop existing server on port {port}")
                sys.exit(1)
        else:
            print(f"Error: Port {port} is already in use.")
            print("Use --force to stop the existing server, or 'ato serve stop' first.")
            sys.exit(1)

    logger.info(f"Starting dashboard server on port {port}")

    server, url = start_dashboard_server(port=port)
    logger.info(f"Dashboard server running at {url}")
    print(f"Dashboard server running at {url}")
    print("Press Ctrl+C to stop")

    # Handle graceful shutdown
    def signal_handler(signum, frame):
        print("\nShutting down...")
        server.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.shutdown()


@serve_app.command()
def stop(
    port: Annotated[
        int,
        typer.Option("--port", "-p", help="Port the server is running on"),
    ] = DEFAULT_PORT,
):
    """Stop the atopile dashboard server."""
    if not _is_port_in_use(port):
        print(f"No server running on port {port}")
        return

    pids = _find_process_on_port(port)
    if not pids:
        print(f"Could not find server process on port {port}")
        sys.exit(1)

    for pid in pids:
        if _kill_process(pid):
            print(f"Stopped server process {pid}")
        else:
            print(f"Failed to stop process {pid}")
            sys.exit(1)


@serve_app.command()
def status(
    port: Annotated[
        int,
        typer.Option("--port", "-p", help="Port to check"),
    ] = DEFAULT_PORT,
):
    """Check if the dashboard server is running."""
    if _is_port_in_use(port):
        pids = _find_process_on_port(port)
        print(f"Server running on port {port} (PID: {', '.join(map(str, pids))})")
    else:
        print(f"No server running on port {port}")
