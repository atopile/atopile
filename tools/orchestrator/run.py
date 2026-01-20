#!/usr/bin/env python3
"""
Orchestrator Quickstart Script

Starts both the backend server and frontend server.
Press Ctrl+C to stop both.

Usage:
    python run.py          # Dev mode (hot reload, slower on mobile)
    python run.py --prod   # Production mode (faster, no hot reload)
"""

from __future__ import annotations

import argparse
import atexit
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# Colors for terminal output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[0;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color


# Global process references for cleanup
backend_process: subprocess.Popen | None = None
frontend_process: subprocess.Popen | None = None


def cleanup():
    """Clean up both processes on exit."""
    print(f"\n{Colors.YELLOW}Shutting down...{Colors.NC}")

    if frontend_process and frontend_process.poll() is None:
        print(f"{Colors.BLUE}Stopping frontend (PID: {frontend_process.pid}){Colors.NC}")
        try:
            frontend_process.terminate()
            frontend_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            frontend_process.kill()
        except Exception:
            pass

    if backend_process and backend_process.poll() is None:
        print(f"{Colors.BLUE}Stopping backend (PID: {backend_process.pid}){Colors.NC}")
        try:
            backend_process.terminate()
            backend_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            backend_process.kill()
        except Exception:
            pass

    print(f"{Colors.GREEN}Shutdown complete{Colors.NC}")


def signal_handler(signum, frame):
    """Handle interrupt signals."""
    cleanup()
    sys.exit(0)


def main():
    global backend_process, frontend_process

    # Parse arguments
    parser = argparse.ArgumentParser(description="Start the Orchestrator servers")
    parser.add_argument(
        "--prod",
        action="store_true",
        help="Run in production mode (builds frontend, faster on mobile)"
    )
    args = parser.parse_args()

    prod_mode = args.prod

    # Register cleanup handlers
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Determine paths
    script_dir = Path(__file__).parent.resolve()
    root_dir = script_dir.parent.parent
    web_dir = script_dir / "web"

    mode_label = "Production" if prod_mode else "Development"
    print(f"{Colors.GREEN}======================================{Colors.NC}")
    print(f"{Colors.GREEN}   Orchestrator ({mode_label}){Colors.NC}")
    print(f"{Colors.GREEN}======================================{Colors.NC}")
    print()

    # Check for npm
    npm_cmd = "npm"
    try:
        subprocess.run([npm_cmd, "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"{Colors.RED}Error: npm not found. Please install Node.js{Colors.NC}")
        sys.exit(1)

    # Check if node_modules exists
    if not (web_dir / "node_modules").exists():
        print(f"{Colors.YELLOW}Installing frontend dependencies...{Colors.NC}")
        subprocess.run([npm_cmd, "install"], cwd=web_dir, check=True)

    # In prod mode, build the frontend first
    if prod_mode:
        print(f"{Colors.BLUE}Building frontend for production...{Colors.NC}")
        result = subprocess.run([npm_cmd, "run", "build"], cwd=web_dir)
        if result.returncode != 0:
            print(f"{Colors.RED}Error: Frontend build failed{Colors.NC}")
            sys.exit(1)
        print(f"{Colors.GREEN}Frontend built successfully{Colors.NC}")
        print()

    # Start backend server
    print()
    print(f"{Colors.BLUE}Starting backend server on http://localhost:8765{Colors.NC}")

    backend_process = subprocess.Popen(
        [sys.executable, "-m", "tools.orchestrator.cli.main", "serve", "--port", "8765"],
        cwd=root_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    # Wait for backend to start
    time.sleep(2)

    if backend_process.poll() is not None:
        print(f"{Colors.RED}Error: Backend failed to start{Colors.NC}")
        # Print any output
        if backend_process.stdout:
            output = backend_process.stdout.read().decode()
            if output:
                print(output)
        sys.exit(1)

    print(f"{Colors.GREEN}Backend started (PID: {backend_process.pid}){Colors.NC}")

    # Start frontend server
    print()
    if prod_mode:
        # Use vite preview for production build
        print(f"{Colors.BLUE}Starting frontend preview server on http://localhost:4173{Colors.NC}")
        frontend_process = subprocess.Popen(
            [npm_cmd, "run", "preview"],
            cwd=web_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        frontend_port = 4173
    else:
        # Use vite dev for development
        print(f"{Colors.BLUE}Starting frontend dev server on http://localhost:5173{Colors.NC}")
        frontend_process = subprocess.Popen(
            [npm_cmd, "run", "dev"],
            cwd=web_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        frontend_port = 5173

    # Wait for frontend to start
    time.sleep(3)

    if frontend_process.poll() is not None:
        print(f"{Colors.RED}Error: Frontend failed to start{Colors.NC}")
        cleanup()
        sys.exit(1)

    print(f"{Colors.GREEN}Frontend started (PID: {frontend_process.pid}){Colors.NC}")

    print()
    print(f"{Colors.GREEN}======================================{Colors.NC}")
    print(f"{Colors.GREEN}   Orchestrator is running!{Colors.NC}")
    print(f"{Colors.GREEN}======================================{Colors.NC}")
    print()
    print(f"  {Colors.BLUE}Dashboard:{Colors.NC}  http://localhost:{frontend_port}")
    print(f"  {Colors.BLUE}API Docs:{Colors.NC}   http://localhost:8765/docs")
    print(f"  {Colors.BLUE}Health:{Colors.NC}     http://localhost:8765/health")
    print()
    if prod_mode:
        print(f"  {Colors.GREEN}Running in production mode (optimized for mobile){Colors.NC}")
    else:
        print(f"  {Colors.YELLOW}Running in dev mode (use --prod for mobile){Colors.NC}")
    print()
    print(f"{Colors.YELLOW}Press Ctrl+C to stop both servers{Colors.NC}")
    print()

    # Stream output from both processes
    try:
        while True:
            # Check if processes are still running
            if backend_process.poll() is not None:
                print(f"{Colors.RED}Backend server stopped unexpectedly{Colors.NC}")
                break
            if frontend_process.poll() is not None:
                print(f"{Colors.RED}Frontend server stopped unexpectedly{Colors.NC}")
                break

            time.sleep(1)
    except KeyboardInterrupt:
        pass

    cleanup()


if __name__ == "__main__":
    main()
