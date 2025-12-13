"""
Pytest plugin that sends test events to the Orchestrator via HTTP.

Workers use the URL specified by FBRK_TEST_ORCHESTRATOR_URL env var
and send JSON events for test start/finish.
"""

import os
import time
import tracemalloc

import httpx
import psutil
import pytest

from test.runner.common import ORCHESTRATOR_URL_ENV, EventRequest, EventType, Outcome


def _extract_error_message(longreprtext: str) -> str:
    """
    Extract a concise error message from the full pytest traceback.

    For assertion errors, extract the assertion message.
    For other exceptions, extract the exception type and message.
    """
    # look from the back for first '\n'
    try:
        return longreprtext.rstrip("\n").rsplit("\n", 1)[-1].strip()
    except Exception:
        return "<Could not extract error message>"


class HttpClient:
    def __init__(self, url: str):
        self.base_url = url.rstrip("/")
        self.client = httpx.Client(timeout=5.0)
        self.pid = os.getpid()

    def send_event(
        self,
        event_type: EventType,
        nodeid: str | None = None,
        outcome: Outcome | None = None,
        output: dict | None = None,
        error_message: str | None = None,
        memory_usage_mb: float | None = None,
        memory_peak_mb: float | None = None,
    ):
        event = EventRequest(
            type=event_type,
            pid=self.pid,
            timestamp=time.time(),
            nodeid=nodeid,
            outcome=outcome,
            output=output,
            error_message=error_message,
            memory_usage_mb=memory_usage_mb,
            memory_peak_mb=memory_peak_mb,
        )

        try:
            self.client.post(f"{self.base_url}/event", content=event.model_dump_json())
        except Exception:
            # We fail silently here to avoid breaking the test execution if the
            # orchestrator is gone, but ideally we should log this.
            pass

    def close(self):
        try:
            self.client.close()
        except Exception:
            pass


_client: HttpClient | None = None
_start_memory: int = 0


def _get_client() -> HttpClient | None:
    global _client
    if _client is None:
        url = os.environ.get(ORCHESTRATOR_URL_ENV)
        if url:
            _client = HttpClient(url)
    return _client


def pytest_configure(config):
    # Disable default terminal reporter to suppress output
    terminal = config.pluginmanager.get_plugin("terminalreporter")
    if terminal:
        config.pluginmanager.unregister(terminal)


def pytest_runtest_logstart(nodeid, location):
    global _start_memory
    _start_memory = psutil.Process().memory_info().rss
    tracemalloc.start()
    client = _get_client()
    if client:
        client.send_event(EventType.START, nodeid=nodeid)


def pytest_runtest_logreport(report: pytest.TestReport):
    client = _get_client()
    if not client:
        return

    # We only report the final outcome of the test item
    # setup/call/teardown logic:

    outcome = None
    if report.when == "call":
        outcome_map = {
            "passed": Outcome.PASSED,
            "failed": Outcome.FAILED,
            "skipped": Outcome.SKIPPED,
        }
        outcome = outcome_map.get(report.outcome, Outcome.ERROR)
    elif report.when == "setup":
        if report.failed:
            outcome = Outcome.ERROR
        elif report.skipped:
            outcome = Outcome.SKIPPED

    # If teardown fails, it's usually an error too, but we might have already reported
    # 'passed' for call.
    # Pytest treats teardown failure as an error.
    # For simplicity, if we already reported a result for 'call', we might ignore
    # teardown unless it fails?
    # The original plugin logic:
    # if report.when == "call": ...
    # elif report.when == "setup" and report.failed: ...
    # elif report.when == "setup" and report.skipped: ...

    output = {}
    error_message = None
    if outcome:
        # Capture output
        if hasattr(report, "capstdout"):
            output["stdout"] = report.capstdout
        if hasattr(report, "capstderr"):
            output["stderr"] = report.capstderr
        if hasattr(report, "longreprtext"):
            output["error"] = report.longreprtext
            # Extract a concise error message from the full traceback
            # The last non-empty line typically contains the actual error
            error_message = _extract_error_message(report.longreprtext)

        # Capture peak memory usage during the test
        try:
            current_traced, peak_traced = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            memory_peak_mb = peak_traced / 1024 / 1024
        except Exception:
            memory_peak_mb = 0.0

        import gc

        gc.collect()
        try:
            import ctypes

            libc = ctypes.CDLL(None)
            trimmer = getattr(libc, "malloc_trim")
            if trimmer is not None:
                trimmer.argtypes = [ctypes.c_size_t]
                trimmer.restype = ctypes.c_int
                trimmer(0)
        except Exception as e:
            print(f"Failed to trim memory: {e}")
            pass

        current_memory = psutil.Process().memory_info().rss
        memory_usage_mb = (current_memory - _start_memory) / 1024 / 1024

        client.send_event(
            EventType.FINISH,
            nodeid=report.nodeid,
            outcome=outcome,
            output=output,
            error_message=error_message,
            memory_usage_mb=memory_usage_mb,
            memory_peak_mb=memory_peak_mb,
        )
