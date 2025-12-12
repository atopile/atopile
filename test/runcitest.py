#!/usr/bin/env python3
"""
CI test runner that wraps pytest and aggregates output from workers.

Creates a Unix socket server that receives test events from pytest workers
(via the ci_minimal_output plugin) and prints periodic status reports.

Usage:
    python test/runcitest.py [pytest args...]
    python test/runcitest.py -x test/core/
    python test/runcitest.py -n auto test/
"""

import datetime
import json
import os
import selectors
import socket
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path

# Import shared types from the plugin
try:
    from test.ci_minimal_output import SOCKET_PATH_ENV, EventType, Outcome
except ImportError:
    from ci_minimal_output import SOCKET_PATH_ENV, EventType, Outcome

REPORT_INTERVAL_SECONDS = int(os.getenv("FBRK_TEST_REPORT_INTERVAL", 5))
LONG_TEST_THRESHOLD = datetime.timedelta(
    seconds=int(os.getenv("FBRK_TEST_LONG_THRESHOLD", 10))
)
# Set to "1" to show pytest's output, default is suppressed
SHOW_PYTEST_OUTPUT = os.getenv("FBRK_TEST_SHOW_PYTEST_OUTPUT", "0") == "1"


@dataclass
class TestState:
    nodeid: str
    pid: int
    start_time: datetime.datetime
    outcome: Outcome | None = None
    finish_time: datetime.datetime | None = None


def _ts() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S")


def _print(msg: str):
    print(f"[{_ts()}] {msg}", flush=True)


class TestAggregator:
    """Aggregates test events from multiple workers."""

    def __init__(self):
        self._tests: dict[str, TestState] = {}
        self._lock = threading.Lock()
        self._active_pids: set[int] = set()
        self._exited_pids: set[int] = set()

    def handle_event(self, data: dict):
        event_type = EventType(data["type"])
        pid = data["pid"]

        with self._lock:
            self._active_pids.add(pid)

            if event_type == EventType.EXIT:
                self._active_pids.remove(pid)
                self._exited_pids.add(pid)
                return

            elif event_type == EventType.START:
                nodeid = data["nodeid"]
                self._tests[nodeid] = TestState(
                    nodeid=nodeid,
                    pid=pid,
                    start_time=datetime.datetime.now(),
                )
            elif event_type == EventType.FINISH:
                nodeid = data["nodeid"]
                if nodeid in self._tests:
                    self._tests[nodeid].outcome = Outcome(data["outcome"])
                    self._tests[nodeid].finish_time = datetime.datetime.now()

    def get_report(self) -> str:
        now = datetime.datetime.now()

        with self._lock:
            tests = list(self._tests.values())
            workers = len(self._active_pids)
            exited_workers = len(self._exited_pids)

        def _count(outcome: Outcome | None) -> int:
            return sum(1 for t in tests if t.outcome == outcome)

        passed = _count(Outcome.PASSED)
        failed = _count(Outcome.FAILED)
        errored = _count(Outcome.ERROR)
        skipped = _count(Outcome.SKIPPED)
        running = _count(None)  # No outcome yet = still running

        out = (
            f"WA:{workers:2} WE:{exited_workers:2}|"
            f" ✓{passed:4} ✗{failed:4} E{errored:4} S{skipped:4} R{running:4}"
        )

        # Long-running tests
        long_tests = [
            t
            for t in tests
            if t.outcome is None
            and t.start_time < now - LONG_TEST_THRESHOLD
            and t.outcome is None
        ]
        if long_tests:
            for t in sorted(long_tests, key=lambda x: x.start_time)[:3]:
                dur = int((now - t.start_time).total_seconds())
                # Truncate nodeid for readability
                short_id = t.nodeid.split("::")[-1][:40]
                out += f"\n * {dur:04}s:{short_id}"

        return out


class SocketServer:
    """Unix socket server that receives events from pytest workers."""

    def __init__(self, socket_path: str, aggregator: TestAggregator):
        self._socket_path = socket_path
        self._aggregator = aggregator
        self._server: socket.socket | None = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._selector = selectors.DefaultSelector()
        self._buffers: dict[socket.socket, bytes] = {}

    def start(self):
        # Remove existing socket file if present
        try:
            os.unlink(self._socket_path)
        except FileNotFoundError:
            pass

        self._server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(self._socket_path)
        self._server.listen(100)
        self._server.setblocking(False)
        self._selector.register(self._server, selectors.EVENT_READ, data=None)

        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        while self._running:
            events = self._selector.select(timeout=0.1)
            for key, _ in events:
                sock = key.fileobj
                assert isinstance(sock, socket.socket)
                if key.data is None:
                    # New connection on server socket
                    self._accept(sock)
                else:
                    # Data from client
                    self._read(sock)

    def _accept(self, sock: socket.socket):
        conn, _ = sock.accept()
        conn.setblocking(False)
        self._selector.register(conn, selectors.EVENT_READ, data="client")
        self._buffers[conn] = b""

    def _read(self, sock: socket.socket):
        try:
            data = sock.recv(4096)
            if not data:
                self._close_client(sock)
                return

            self._buffers[sock] += data

            # Process complete lines (newline-delimited JSON)
            while b"\n" in self._buffers[sock]:
                line, self._buffers[sock] = self._buffers[sock].split(b"\n", 1)
                if line:
                    try:
                        event = json.loads(line.decode())
                        self._aggregator.handle_event(event)
                    except (json.JSONDecodeError, KeyError):
                        pass  # Skip malformed events

        except (ConnectionResetError, BrokenPipeError, OSError):
            self._close_client(sock)

    def _close_client(self, sock: socket.socket):
        try:
            self._selector.unregister(sock)
        except (KeyError, ValueError):
            pass
        try:
            sock.close()
        except OSError:
            pass
        self._buffers.pop(sock, None)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        if self._server:
            try:
                self._selector.unregister(self._server)
            except (KeyError, ValueError):
                pass
            self._server.close()
        self._selector.close()
        try:
            os.unlink(self._socket_path)
        except FileNotFoundError:
            pass


class ReportTimer:
    """Periodically prints status reports."""

    def __init__(self, aggregator: TestAggregator, interval: int):
        self._aggregator = aggregator
        self._interval = interval
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        # Align to clock boundary
        now = time.time()
        next_tick = ((int(now) // self._interval) + 1) * self._interval
        time.sleep(next_tick - now)

        while self._running:
            _print(self._aggregator.get_report())
            time.sleep(self._interval)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)


def main():
    # Create socket in temp directory
    socket_path = str(Path(tempfile.gettempdir()) / f"pytest-{os.getpid()}.sock")

    aggregator = TestAggregator()
    server = SocketServer(socket_path, aggregator)
    timer = ReportTimer(aggregator, REPORT_INTERVAL_SECONDS)

    server.start()
    timer.start()

    _print(f"Started test server on {socket_path}")

    # Build pytest command
    pytest_args = sys.argv[1:] if len(sys.argv) > 1 else []
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-p",
        "test.ci_minimal_output",
        *pytest_args,
    ]

    # Set up environment with socket path
    env = os.environ.copy()
    env[SOCKET_PATH_ENV] = socket_path

    _print(f"Running: {' '.join(cmd)}")

    try:
        # Run pytest, optionally suppressing its output
        if SHOW_PYTEST_OUTPUT:
            result = subprocess.run(cmd, env=env)
        else:
            result = subprocess.run(
                cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        exit_code = result.returncode
    except KeyboardInterrupt:
        _print("Interrupted")
        exit_code = 130
    finally:
        # Give a moment for final events
        time.sleep(0.2)
        timer.stop()
        server.stop()

    # Final report
    _print("-" * 80)
    _print(f"Final: {aggregator.get_report()}")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
