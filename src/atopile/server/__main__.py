"""
CLI entry point for the dashboard server.

Usage:
    python -m atopile.server [--port PORT] [--workspace PATH]

Starts the dashboard server for the atopile extension.
"""

import argparse
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import requests

from atopile.server.server import DASHBOARD_PORT, DashboardServer, find_free_port


def is_port_in_use(port: int) -> bool:
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def is_atopile_server_running(port: int) -> bool:
    """Check if an atopile server is already running on the given port."""
    try:
        response = requests.get(f"http://127.0.0.1:{port}/health", timeout=2)
        return response.status_code == 200 and response.json().get("status") == "ok"
    except (requests.RequestException, ValueError):
        return False


def kill_process_on_port(port: int) -> bool:
    """Kill the process using the specified port. Returns True if successful."""
    try:
        # Use lsof to find the PID using the port (works on macOS and Linux)
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return False

        pids = result.stdout.strip().split("\n")
        for pid in pids:
            try:
                subprocess.run(["kill", "-TERM", pid], check=True)
            except subprocess.CalledProcessError:
                # Try SIGKILL if SIGTERM fails
                subprocess.run(["kill", "-KILL", pid], check=False)

        # Wait for port to become available
        for _ in range(30):  # Wait up to 3 seconds
            if not is_port_in_use(port):
                return True
            time.sleep(0.1)

        return not is_port_in_use(port)
    except FileNotFoundError:
        # lsof not available, try netstat on Linux
        return False


def write_port_file(workspace_path: Path, port: int) -> Path | None:
    """Write the server port to a file for discovery by clients."""
    try:
        port_file = workspace_path / ".atopile" / ".server_port"
        port_file.parent.mkdir(parents=True, exist_ok=True)
        port_file.write_text(str(port))
        return port_file
    except OSError:
        return None


def remove_port_file(port_file: Path | None) -> None:
    """Remove the port file on shutdown."""
    if port_file and port_file.exists():
        try:
            port_file.unlink()
        except OSError:
            pass


def main():
    parser = argparse.ArgumentParser(description="Start the atopile dashboard server")
    parser.add_argument(
        "--port",
        type=int,
        default=DASHBOARD_PORT,
        help=f"Port to run the server on (default: {DASHBOARD_PORT})",
    )
    parser.add_argument(
        "--workspace",
        type=str,
        action="append",
        default=[],
        help="Workspace path to scan for projects (can be specified multiple times)",
    )
    parser.add_argument(
        "--logs-dir",
        type=str,
        default=None,
        help="Directory for build logs (default: current directory)",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Kill existing server on the port and start fresh",
    )
    parser.add_argument(
        "--auto-port",
        action="store_true",
        help="Automatically find a free port if the default is in use",
    )

    args = parser.parse_args()

    # Determine logs directory
    if args.logs_dir:
        logs_base = Path(args.logs_dir)
    else:
        logs_base = Path.cwd() / "build" / "logs"

    logs_base.mkdir(parents=True, exist_ok=True)

    # Create a default summary file location
    summary_file = logs_base / "latest" / "summary.json"
    summary_file.parent.mkdir(parents=True, exist_ok=True)

    # Initialize empty summary if it doesn't exist
    if not summary_file.exists():
        summary_file.write_text('{"builds": [], "totals": {}}')

    # Convert workspace paths
    workspace_paths = (
        [Path(p) for p in args.workspace] if args.workspace else [Path.cwd()]
    )

    # Check if port is already in use
    port = args.port
    if is_port_in_use(port):
        if args.force:
            print(f"Stopping existing server on port {port}...")
            if kill_process_on_port(port):
                print("Existing server stopped")
            else:
                print(f"Failed to stop process on port {port}")
                sys.exit(1)
        elif args.auto_port:
            old_port = port  # noqa: F841
            port = find_free_port()
            print("Port {old_port} in use, using port {port} instead")
        elif is_atopile_server_running(port):
            print("Atopile server already running on port {port}")
            print("Dashboard available at http://localhost:{port}")
            print("Use --force to restart, or --auto-port to use a different port")
            sys.exit(0)
        else:
            print(f"Port {port} is already in use by another application")
            print("Options:")
            print("  1. Use --force to kill the process: ato serve backend --force")
            print(
                "  2. Use --auto-port to find a free port: ato serve backend --auto-port"  # noqa: E501
            )
            print("  3. Use a specific port: ato serve backend --port <PORT>")
            sys.exit(1)

    # Output port early for programmatic discovery (before logging starts)
    # This line is parsed by the VS Code extension and other tools
    print(f"ATOPILE_SERVER_PORT={port}", flush=True)

    # Write port file for client discovery
    port_file = write_port_file(workspace_paths[0], port) if workspace_paths else None
    if port_file:
        print(f"Port file: {port_file}")

    # Create and start server
    server = DashboardServer(
        summary_file=summary_file,
        logs_base=logs_base,
        port=port,
        workspace_paths=workspace_paths,
    )

    print(f"Starting dashboard server on http://localhost:{port}")
    print(f"Logs directory: {logs_base}")
    print(f"Workspace paths: {', '.join(str(p) for p in workspace_paths)}")
    print("Press Ctrl+C to stop")

    server.start()

    # Handle shutdown gracefully
    def shutdown_handler(signum, frame):
        print("\nShutting down...")
        remove_port_file(port_file)
        server.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        remove_port_file(port_file)
        server.shutdown()


if __name__ == "__main__":
    main()
