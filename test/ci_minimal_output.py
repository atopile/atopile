"""
Pytest plugin for minimal CI output.

Only prints start/result timestamps per test:
  <timestamp>: <test_name>: Start
  <timestamp>: <test_name>: PASSED/FAILED/SKIPPED/ERROR

All other output is suppressed (captured in junit.xml instead).
"""

import atexit
import datetime
import os
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

# Capture original stderr to write our output there (avoid pytest capture)
_original_stderr = sys.stderr

LOG_OUTPUT_INTERVAL_SECONDS = int(os.getenv("FBRK_TEST_LOG_OUTPUT_INTERVAL_SECONDS", 5))
LOG_WARNING_THRESHOLD = datetime.timedelta(
    seconds=int(os.getenv("FBRK_TEST_LOG_WARNING_THRESHOLD_SECONDS", 10))
)


@dataclass
class TestState:
    nodeid: str
    start_time: datetime.datetime
    outcome: str | None = None
    finish_time: datetime.datetime | None = None


def _print(msg: str, ts: datetime.datetime | None = None, flush: bool = True):
    if ts is None:
        ts = datetime.datetime.now()
    tsstr = ts.strftime("%Y-%m-%d %H:%M:%S")
    _original_stderr.write(f"{tsstr}: {msg}\n")
    if flush:
        _original_stderr.flush()


class ClockTimer:
    """
    Timer that fires at HH:MM:n*<seconds> and calls f()
    e.g seconds=5 => 12:00:00, 12:00:05, 12:00:10, 12:00:15, ...
    """

    def __init__(self, f: Callable[[], Any], seconds: float):
        self._f = f
        self._seconds = seconds
        self._start_time: datetime.datetime | None = None
        self._running = False
        self._thread: threading.Thread | None = None
        # for simplicity, only support seconds < 60
        assert self._seconds > 0 and self._seconds < 60

    def _next_fire_time(self, now: datetime.datetime) -> datetime.datetime:
        """Calculate the next clock-aligned fire time after 'now'."""
        current_second = now.second + now.microsecond / 1_000_000
        # Find next multiple of self._seconds
        next_multiple = (int(current_second / self._seconds) + 1) * self._seconds

        if next_multiple >= 60:
            # Roll over to next minute
            next_minute = now.replace(second=0, microsecond=0) + datetime.timedelta(
                minutes=1
            )
            return next_minute
        else:
            return now.replace(second=int(next_multiple), microsecond=0)

    def _run(self):
        """Background thread loop that fires callback at aligned intervals."""
        while self._running:
            now = datetime.datetime.now()
            next_fire = self._next_fire_time(now)
            sleep_time = (next_fire - now).total_seconds()

            if sleep_time > 0:
                # Sleep in small increments to allow clean shutdown
                time.sleep(min(sleep_time, 0.1))
                if not self._running:
                    break
                # Check if we haven't reached the fire time yet
                if datetime.datetime.now() < next_fire:
                    continue

            self._f()

    def start(self):
        self._start_time = datetime.datetime.now()
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the timer and wait for the thread to finish."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)


class TestStateManager:
    def __init__(self):
        self._running_tests: dict[str, TestState] = {}
        self._pid = os.getpid()
        self._timer = ClockTimer(
            f=self.handle_timer, seconds=LOG_OUTPUT_INTERVAL_SECONDS
        )
        self._timer.start()
        self._print("Started test runner")
        atexit.register(self.handle_exit)

    def get_test_report(self) -> str:
        """
        Return count of Passed, Failed, Errored, In Progress tests
        List tests that are running for more than LOG_WARNING_THRESHOLD_SECONDS
        """

        now = datetime.datetime.now()
        long_tests = [
            test
            for test in self._running_tests.values()
            if test.start_time < now - LOG_WARNING_THRESHOLD and test.outcome is None
        ]

        def _count_tests(outcome: str | None) -> int:
            return sum(
                1 for test in self._running_tests.values() if test.outcome == outcome
            )

        passed = _count_tests("PASSED")
        failed = _count_tests("FAILED")
        errored = _count_tests("ERROR")
        in_progress = _count_tests(None)
        out = (
            f"Passed: {passed:4}"
            f" Failed: {failed:4}"
            f" Errored: {errored:4}"
            f" In Progress: {in_progress:4}"
        )

        if long_tests:
            out += " Long running tests:"
            for test in long_tests:
                durations = (now - test.start_time).total_seconds()
                out += f"\n * {durations:3.0f}s| {test.nodeid}"
        return out

    def _print(self, msg: str):
        _print(f"{self._pid:4X}: {msg}")

    def handle_timer(self):
        self._print(self.get_test_report())

    def handle_exit(self):
        self._print("Shutting down test runner:" + self.get_test_report())

    def register_start(self, nodeid: str):
        now = datetime.datetime.now()
        self._running_tests[nodeid] = TestState(nodeid=nodeid, start_time=now)

    def register_finish(self, nodeid: str, outcome: str):
        now = datetime.datetime.now()
        self._running_tests[nodeid].finish_time = now
        self._running_tests[nodeid].outcome = outcome


test_state_manager = TestStateManager()


def pytest_configure(config):
    # Disable default terminal reporter to suppress all other output
    terminal = config.pluginmanager.get_plugin("terminalreporter")
    if terminal:
        config.pluginmanager.unregister(terminal)


def pytest_runtest_logstart(nodeid, location):
    test_state_manager.register_start(nodeid)


def pytest_runtest_logreport(report):
    if report.when == "call":
        test_state_manager.register_finish(report.nodeid, report.outcome.upper())
    elif report.when == "setup" and report.failed:
        test_state_manager.register_finish(report.nodeid, "ERROR")


def main_test():
    pass


if __name__ == "__main__":
    import typer

    typer.run(main_test)
