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

from atopile.logging import _extract_traceback_frames
from test.runner.common import ORCHESTRATOR_URL_ENV, EventRequest, EventType, Outcome

# Use atopile prefix so logs pass through the _atopile_log_filter
logger = logging.getLogger("atopile.test.plugin")

FBRK_TEST_TEST_TIMEOUT = int(os.environ.get("FBRK_TEST_TEST_TIMEOUT", -1))

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
    is captured separately via _extract_traceback_frames.
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
                structured_tb = _extract_traceback_frames(
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


class ExceptionTestTimeout(BaseException): ...


def _get_thread_stack(thread_id: int) -> str:
    """Capture the current stack trace of a thread by its ID."""
    import sys
    import traceback

    frames = sys._current_frames()
    if thread_id not in frames:
        return "<thread not found>"
    return "".join(traceback.format_stack(frames[thread_id]))


if FBRK_TEST_TEST_TIMEOUT > 0:
    # TODO
    # probably need to manually call teardown and setup
    raise NotImplementedError(
        "This breaks a bunch of tests for some reason, even without timeout"
    )

    @pytest.hookimpl(trylast=True)
    def pytest_runtest_call(item: pytest.Item):
        import ctypes
        import threading

        timeout = FBRK_TEST_TEST_TIMEOUT

        main_thread_id = threading.current_thread().ident
        assert main_thread_id is not None  # Always valid for a running thread
        stop_watchdog = threading.Event()

        def _watchdog():
            """
            Thread-based watchdog that injects TestTimeout into the main thread.
            Unlike signal handlers, this cannot be overridden by test code.
            """
            failures = 0
            last_printed_stack: str | None = None
            # Wait for initial timeout
            if stop_watchdog.wait(timeout):
                return  # Test completed normally

            # Test timed out - repeatedly inject exception until it sticks
            # (in case exceptions are caught/suppressed)
            while not stop_watchdog.is_set():
                if failures > 10:
                    print("Test timed out too many times - exiting")
                    sys.exit(0x59)  # random exit code
                wait_time = max(5 / (2**failures), 0.05)
                failures += 1
                # Format current time with milliseconds for higher precision
                t = time.time()
                time_s = (
                    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))
                    + f".{int((t % 1) * 1000):03d}"
                )
                print(
                    f"{time_s}: Test {item.nodeid} timed out - injecting exception"
                    f" (waiting {wait_time:.2f}s)"
                )
                # Capture stack before injecting exception to see what's blocking
                stack_before = _get_thread_stack(main_thread_id)
                # one last extra check
                # Inject TestTimeout exception into the main thread
                ctypes.pythonapi.PyThreadState_SetAsyncExc(
                    ctypes.c_ulong(main_thread_id),
                    ctypes.py_object(ExceptionTestTimeout),
                )
                # Retry if the exception doesn't take
                if stop_watchdog.wait(timeout=wait_time):
                    break

                # Exception didn't work - print where the thread was stuck
                stack_after = _get_thread_stack(main_thread_id)
                # Only print full stacks if they differ from the last printed one
                if stack_before != last_printed_stack:
                    print(f"Stack when timeout was injected:\n{stack_before}")
                    last_printed_stack = stack_before
                if stack_after != last_printed_stack:
                    print(f"Stack after waiting (still blocked):\n{stack_after}")
                    last_printed_stack = stack_after

        watchdog_thread = threading.Thread(target=_watchdog, daemon=True)
        watchdog_thread.start()

        try:
            item.runtest()  # run the actual test function
            stop_watchdog.set()
        except ExceptionTestTimeout:
            stop_watchdog.set()
            pytest.fail(f"Test timed out after {timeout:.2f}s", pytrace=False)
        finally:
            stop_watchdog.set()
            watchdog_thread.join(timeout=0.1)
