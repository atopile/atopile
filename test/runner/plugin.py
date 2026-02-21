"""
Pytest plugin that sends test events to the Orchestrator via HTTP.

Workers use the URL specified by FBRK_TEST_ORCHESTRATOR_URL env var
and send JSON events for test start/finish.
"""

import json
import logging
import os
import sys
import time
import tracemalloc

import httpx
import psutil
import pytest

from atopile.errors import extract_traceback_frames
from test.runner.common import ORCHESTRATOR_URL_ENV, EventRequest, EventType, Outcome

# Use atopile prefix so logs pass through the _atopile_log_filter
logger = logging.getLogger("atopile.test.plugin")

# Storage for captured exception info per test nodeid
_captured_exc_info: dict[str, tuple] = {}


def _format_rich_traceback(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_tb,
    width: int = 120,
) -> str:
    """Format an exception as plain text traceback.

    Note: Previously used Rich's Traceback but syntax highlighting was too slow
    (~1-7 seconds). Plain traceback is ~0.001s. Structured data with locals
    is captured separately via extract_traceback_frames.
    """
    import traceback

    lines = traceback.format_exception(exc_type, exc_value, exc_tb)
    return "".join(lines)


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

        payload = event.model_dump_json()
        backoff = 0.1
        for attempt in range(4):
            try:
                self.client.post(f"{self.base_url}/event", content=payload)
                return
            except Exception:
                if attempt < 3:
                    time.sleep(backoff)
                    backoff *= 3
        # All attempts failed — log but never raise to avoid breaking tests
        logger.warning("send_event failed after 4 attempts: %s %s", event_type, nodeid)

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


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item: pytest.Item):
    """Capture exception info when a test fails for Rich traceback formatting."""
    try:
        result = yield
        return result
    except BaseException:
        # Capture the exception info for Rich formatting later
        _captured_exc_info[item.nodeid] = sys.exc_info()
        raise


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
        if hasattr(report, "caplog") and report.caplog:
            output["log"] = report.caplog

        # For skipped tests, extract the skip reason
        if outcome == Outcome.SKIPPED and report.longrepr:
            # For skips, longrepr is typically (file, lineno, reason)
            if isinstance(report.longrepr, tuple) and len(report.longrepr) >= 3:
                error_message = str(report.longrepr[2]).removeprefix("Skipped: ")
            elif hasattr(report, "longreprtext") and report.longreprtext:
                error_message = _extract_error_message(report.longreprtext)
        elif report.nodeid in _captured_exc_info:
            exc_type, exc_value, exc_tb = _captured_exc_info.pop(report.nodeid)
            if exc_type and exc_value:
                output["error"] = _format_rich_traceback(exc_type, exc_value, exc_tb)
                # Extract structured traceback with local vars for inspector.
                # Serialize to JSON string since output dict expects str values.
                structured_tb = extract_traceback_frames(
                    exc_type,
                    exc_value,
                    exc_tb,
                    suppress_paths=["pluggy", "_pytest", "pytest", "test/runner"],
                )
                output["traceback_structured"] = json.dumps(structured_tb)
                # Extract error message from the exception directly
                error_message = f"{exc_type.__name__}: {exc_value}"
                # Log the exception so it gets captured in the test_logs database
                # with python_traceback (structured frames for the UI)
                logger.error(
                    f"Test failed: {error_message}",
                    exc_info=(exc_type, exc_value, exc_tb),
                )
        elif hasattr(report, "longreprtext") and report.longreprtext:
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
