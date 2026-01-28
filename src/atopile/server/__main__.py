"""
CLI entry point for the dashboard server.

Usage:
    python -m atopile.server --port PORT [--workspace PATH]

Starts the dashboard server for the atopile extension.
"""

import argparse
import signal
import subprocess
import sys
import time
from pathlib import Path

import requests

from atopile.server.server import DashboardServer, is_port_in_use, kill_process_on_port


def is_atopile_server_running(port: int) -> bool:
    """Check if an atopile server is already running on the given port."""
    try:
        response = requests.get(f"http://127.0.0.1:{port}/health", timeout=2)
        return response.status_code == 200 and response.json().get("status") == "ok"
    except (requests.RequestException, ValueError):
        return False


def main():
    parser = argparse.ArgumentParser(description="Start the atopile dashboard server")
    parser.add_argument(
        "--port",
        type=int,
        required=True,
        help="Port to run the server on (required)",
    )
    parser.add_argument(
        "--workspace",
        type=str,
        action="append",
        default=[],
        help="Workspace path to scan for projects (can be specified multiple times)",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Kill existing server on the port and start fresh",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[3]
    gen_script = repo_root / "scripts" / "generate_types.py"
    ui_server_dir = repo_root / "src" / "ui-server"
    if gen_script.exists() and ui_server_dir.exists():
        result = subprocess.run([sys.executable, str(gen_script)], cwd=str(repo_root))
        if result.returncode != 0:
            sys.exit(result.returncode)

    # Convert workspace paths (use all provided or cwd)
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
        elif is_atopile_server_running(port):
            print(f"atopile server already running on port {port}")
            print(f"Dashboard available at http://localhost:{port}")
            print("Use --force to restart, or --port to use a different port")
            sys.exit(0)
        else:
            print(f"Port {port} is already in use by another application")
            print("Options:")
            print("  1. Use --force to kill the process: ato serve backend --force")
            print("  2. Use a specific port: ato serve backend --port <PORT>")
            sys.exit(1)

    # Output port early for programmatic discovery (before logging starts)
    # This line is parsed by the VS Code extension and other tools
    print(f"ATOPILE_SERVER_PORT={port}", flush=True)

    # Create and start server
    server = DashboardServer(
        port=port,
        workspace_paths=workspace_paths,
    )

    print(f"Starting dashboard server on http://localhost:{port}")
    print(f"Workspace paths: {', '.join(str(p) for p in workspace_paths)}")
    print("Press Ctrl+C to stop")

    server.start()

    # Handle shutdown gracefully
    def shutdown_handler(signum, frame):
        print("\nShutting down...")
        server.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
