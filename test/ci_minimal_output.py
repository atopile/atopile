"""
Pytest plugin that sends test events to a Unix socket.

Workers connect to the socket specified by FBRK_TEST_SOCKET env var
and send JSON events for test start/finish.

Use runcitest.py to run pytest - it creates the socket server.
"""

import atexit
import json
import os
import socket
from enum import StrEnum, auto

import pytest

SOCKET_PATH_ENV = "FBRK_TEST_SOCKET"


class Outcome(StrEnum):
    PASSED = auto()
    FAILED = auto()
    ERROR = auto()
    SKIPPED = auto()


class EventType(StrEnum):
    START = auto()
    FINISH = auto()
    EXIT = auto()


def _make_event(
    event_type: EventType, nodeid: str | None = None, outcome: Outcome | None = None
) -> bytes:
    """Create a newline-terminated JSON event."""
    data = {
        "type": event_type,
        "pid": os.getpid(),
    }
    if outcome is not None:
        data["outcome"] = outcome
    if nodeid is not None:
        data["nodeid"] = nodeid
    return (json.dumps(data) + "\n").encode()


class SocketClient:
    """Sends events to the Unix socket server."""

    def __init__(self, socket_path: str):
        self._socket_path = socket_path
        self._sock: socket.socket | None = None
        self._connect()

        atexit.register(self.close)

    def _connect(self):
        try:
            self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._sock.connect(self._socket_path)
        except (OSError, ConnectionRefusedError):
            self._sock = None

    def send(self, data: bytes):
        if self._sock is None:
            return
        try:
            self._sock.sendall(data)
        except (BrokenPipeError, OSError):
            # Connection lost, try to reconnect once
            self._connect()
            if self._sock:
                try:
                    self._sock.sendall(data)
                except (BrokenPipeError, OSError):
                    pass

    def close(self):
        if self._sock:
            try:
                self.send(_make_event(EventType.EXIT, ""))
            except Exception:
                pass
            try:
                self._sock.close()
            except OSError:
                pass


# Global client - initialized lazily
_client: SocketClient | None = None


def _get_client() -> SocketClient | None:
    global _client
    if _client is None:
        socket_path = os.environ.get(SOCKET_PATH_ENV)
        if socket_path:
            _client = SocketClient(socket_path)
            atexit.register(_client.close)
    return _client


def pytest_configure(config):
    # Disable default terminal reporter to suppress all output
    terminal = config.pluginmanager.get_plugin("terminalreporter")
    if terminal:
        config.pluginmanager.unregister(terminal)


def pytest_runtest_logstart(nodeid, location):
    client = _get_client()
    if client:
        client.send(_make_event(EventType.START, nodeid))


def pytest_runtest_logreport(report: pytest.TestReport):
    client = _get_client()
    if not client:
        return

    if report.when == "call":
        # Map pytest outcome to our Outcome enum
        outcome_map = {
            "passed": Outcome.PASSED,
            "failed": Outcome.FAILED,
            "skipped": Outcome.SKIPPED,
        }
        outcome = outcome_map.get(report.outcome, Outcome.ERROR)
        client.send(_make_event(EventType.FINISH, report.nodeid, outcome))
    elif report.when == "setup" and report.failed:
        client.send(_make_event(EventType.FINISH, report.nodeid, Outcome.ERROR))
    elif report.when == "setup" and report.skipped:
        client.send(_make_event(EventType.FINISH, report.nodeid, Outcome.SKIPPED))
