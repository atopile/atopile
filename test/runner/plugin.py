"""
Pytest plugin that sends test events to the Orchestrator via HTTP.

Workers use the URL specified by FBRK_TEST_ORCHESTRATOR_URL env var
and send JSON events for test start/finish.
"""

import os
import time

import httpx
import pytest

from test.runner.common import ORCHESTRATOR_URL_ENV, EventRequest, EventType, Outcome


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
    ):
        event = EventRequest(
            type=event_type,
            pid=self.pid,
            timestamp=time.time(),
            nodeid=nodeid,
            outcome=outcome,
            output=output,
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
    if outcome:
        # Capture output
        if hasattr(report, "capstdout"):
            output["stdout"] = report.capstdout
        if hasattr(report, "capstderr"):
            output["stderr"] = report.capstderr
        if hasattr(report, "longreprtext"):
            output["error"] = report.longreprtext

        client.send_event(
            EventType.FINISH, nodeid=report.nodeid, outcome=outcome, output=output
        )
