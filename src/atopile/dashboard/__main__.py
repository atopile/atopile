"""
CLI entry point for the dashboard server.

Usage:
    python -m atopile.dashboard [--port PORT] [--workspace PATH]

Starts the dashboard server for the atopile extension.
"""

import argparse
import signal
import sys
import time
from pathlib import Path

from atopile.dashboard.server import DashboardServer


def main():
    parser = argparse.ArgumentParser(description="Start the atopile dashboard server")
    parser.add_argument(
        "--port",
        type=int,
        default=8501,
        help="Port to run the server on (default: 8501)",
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

    # Create and start server
    server = DashboardServer(
        summary_file=summary_file,
        logs_base=logs_base,
        port=args.port,
        workspace_paths=workspace_paths,
    )

    print(f"Starting dashboard server on http://localhost:{args.port}")
    print(f"Logs directory: {logs_base}")
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
