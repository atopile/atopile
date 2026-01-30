"""
Test report building and aggregation.

Contains TestState, TestAggregator, and report generation logic.
"""

import bisect
import datetime
import html
import json
import os
import platform
import socket
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from urllib.parse import quote as url_quote

from jinja2 import Template

from test.runner.baselines import (
    CompareStatus,
    RemoteBaseline,
    fetch_remote_report,
    list_local_baselines,
    remote_commits,
    remote_commits_lock,
)
from test.runner.common import (
    EventRequest,
    EventType,
    Outcome,
)
from test.runner.git_info import (
    collect_env_subset,
    get_git_info,
)
from test.runner.report_utils import (
    ansi_to_html,
    apply_output_limits,
    baseline_record,
    format_duration,
    outcome_to_str,
    percentiles,
    perf_change,
    safe_iso,
    split_error_message,
    split_nodeid,
)
from test.runner.report_utils import (
    compare_status as get_compare_status,
)

# Configuration (imported from main or set here)
PERF_THRESHOLD_PERCENT = float(os.getenv("FBRK_TEST_PERF_THRESHOLD_PERCENT", "0.30"))
PERF_MIN_TIME_DIFF_S = float(os.getenv("FBRK_TEST_PERF_MIN_TIME_DIFF_S", "1.0"))
PERF_MIN_MEMORY_DIFF_MB = float(os.getenv("FBRK_TEST_PERF_MIN_MEMORY_DIFF_MB", "50.0"))
REPORT_SCHEMA_VERSION = "4"
REPORT_JSON_PATH = Path("artifacts/test-report.json")
REPORT_HTML_PATH = Path("artifacts/test-report.html")
GENERATE_HTML = os.getenv("FBRK_TEST_GENERATE_HTML", "1") == "1"
GENERATE_PERIODIC_HTML = os.getenv("FBRK_TEST_PERIODIC_HTML", "1") == "1"
OUTPUT_MAX_BYTES = int(os.getenv("FBRK_TEST_OUTPUT_MAX_BYTES", "0"))
OUTPUT_TRUNCATE_MODE = os.getenv("FBRK_TEST_OUTPUT_TRUNCATE_MODE", "tail")
REPORT_INTERVAL_SECONDS = int(os.getenv("FBRK_TEST_REPORT_INTERVAL", 5))
LONG_TEST_THRESHOLD = datetime.timedelta(
    seconds=int(os.getenv("FBRK_TEST_LONG_THRESHOLD", 10))
)
WORKER_COUNT = int(os.getenv("FBRK_TEST_WORKERS", 0))
if WORKER_COUNT == 0:
    WORKER_COUNT = os.cpu_count() or 1
elif WORKER_COUNT < 0:
    WORKER_COUNT = max(((os.cpu_count() or 1) * -WORKER_COUNT) // 2, 1)
ORCHESTRATOR_BIND_HOST = os.getenv("FBRK_TEST_BIND_HOST", "0.0.0.0")
LOG_DIR = Path("artifacts/logs")

# Read HTML template from file
HTML_TEMPLATE: Template = Template(
    (Path(__file__).parent / "report.html").read_text(encoding="utf-8"),
    variable_start_string="[[",
    variable_end_string="]]",
)

# These will be set by main.py
test_queue = None  # type: ignore
workers = None  # type: ignore
commit_info = None  # type: ignore
ci_info = None  # type: ignore


def set_globals(queue, workers_dict, commit, ci):
    """Set global references from main module."""
    global test_queue, workers, commit_info, ci_info
    test_queue = queue
    workers = workers_dict
    commit_info = commit
    ci_info = ci


def get_log_file(worker_id: int) -> Path:
    """Get the log file path for a worker."""
    return LOG_DIR / f"worker-{worker_id}.log"


@dataclass
class TestState:
    __test__ = False

    nodeid: str
    pid: int | None
    start_time: datetime.datetime | None
    outcome: Outcome | None = None
    finish_time: datetime.datetime | None = None
    claim_attempts: int = 0
    requeues: int = 0
    output: dict | None = None
    error_message: str | None = None
    memory_usage_mb: float = 0.0
    memory_peak_mb: float = 0.0
    compare_status: CompareStatus | None = None
    baseline_outcome: str | None = None
    collection_error: bool = False


def _ts() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S")


def _print(msg: str):
    print(f"[{_ts()}] {msg}", flush=True)


class TestAggregator:
    """Aggregates test events from multiple workers."""

    __test__ = False

    def __init__(
        self,
        all_tests: list[str],
        baseline: RemoteBaseline,
        pytest_args: list[str] | None = None,
        baseline_requested: str | None = None,
        collection_errors: dict[str, str] | None = None,
        test_run_id: str | None = None,
    ):
        self._baseline = baseline
        self._tests: dict[str, TestState] = {}
        self._test_run_id = test_run_id
        self._pytest_args = list(pytest_args or [])
        self._baseline_requested = baseline_requested
        self._collection_errors = collection_errors or {}
        self._orchestrator_url: str | None = None
        self._orchestrator_report_url: str | None = None
        for t in all_tests:
            state = TestState(nodeid=t, pid=None, start_time=None)
            # Set baseline info if available
            if baseline.loaded:
                if t in baseline.tests:
                    state.baseline_outcome = baseline.tests[t].get("outcome")
                else:
                    # Test is new (not in baseline)
                    state.compare_status = CompareStatus.NEW
            self._tests[t] = state
        self._lock = threading.Lock()
        self._active_pids: set[int] = set()
        self._exited_pids: set[int] = set()
        # Tracks tests that have been handed out via /claim but for which we
        # haven't yet received START/FINISH. If a worker dies in that window,
        # the test is otherwise "lost" (not in the queue and never started).
        self._claimed_by_pid: dict[int, str] = {}
        # Maps worker PID to worker ID (for log file access)
        self._pid_to_worker_id: dict[int, int] = {}
        self.start_time = datetime.datetime.now()

    def set_orchestrator_url(self, url: str) -> None:
        self._orchestrator_url = url

    def set_orchestrator_report_url(self, url: str) -> None:
        self._orchestrator_report_url = url

    def set_test_run_id(self, test_run_id: str) -> None:
        self._test_run_id = test_run_id

    def register_worker(self, worker_id: int, pid: int) -> None:
        """Register a worker's PID to worker_id mapping for log file access."""
        with self._lock:
            self._pid_to_worker_id[pid] = worker_id

    def get_worker_log(self, pid: int) -> str | None:
        """Get the log file content for a worker by PID."""
        with self._lock:
            worker_id = self._pid_to_worker_id.get(pid)
        if worker_id is None:
            return None
        log_file = get_log_file(worker_id)
        if log_file.exists():
            try:
                return log_file.read_text(encoding="utf-8", errors="replace")
            except Exception:
                return None
        return None

    def handle_claim(self, pid: int, nodeid: str) -> None:
        with self._lock:
            self._active_pids.add(pid)

            # Defensive: if the worker somehow claims twice without finishing,
            # treat the previous claim as orphaned and requeue if unstarted.
            prev = self._claimed_by_pid.get(pid)
            if prev and prev != nodeid:
                prev_state = self._tests.get(prev)
                if (
                    prev_state
                    and prev_state.outcome is None
                    and prev_state.start_time is None
                ):
                    prev_state.pid = None
                    prev_state.requeues += 1
                    test_queue.put(prev)

            self._claimed_by_pid[pid] = nodeid
            state = self._tests.get(nodeid)
            if state:
                state.pid = pid
                state.claim_attempts += 1

    def set_baseline(self, baseline: RemoteBaseline) -> None:
        """
        Update the baseline after initialization called when background fetch completes
        Recomputes comparison status for any tests that have already finished.
        """
        with self._lock:
            self._baseline = baseline
            if not baseline.loaded:
                return

            # Update all tests with baseline info and recompute comparisons
            for nodeid, test in self._tests.items():
                if nodeid in baseline.tests:
                    test.baseline_outcome = baseline.tests[nodeid].get("outcome")
                    # Reset compare_status so it can be recomputed
                    test.compare_status = None
                else:
                    test.compare_status = CompareStatus.NEW

                # Recompute comparison for tests that have already finished
                if test.outcome is not None:
                    self._compute_compare_status(test)

    def _compute_compare_status(self, test: TestState) -> None:
        """Compute comparison status based on outcome vs baseline."""
        if not self._baseline.loaded or test.outcome is None:
            return

        if test.compare_status == CompareStatus.NEW:
            # Already marked as new
            return

        current = str(test.outcome).lower()
        baseline = test.baseline_outcome.lower() if test.baseline_outcome else None

        if baseline is None:
            test.compare_status = CompareStatus.NEW
        elif current == baseline:
            test.compare_status = CompareStatus.SAME
        elif baseline == "passed" and current in ("failed", "error", "crashed"):
            test.compare_status = CompareStatus.REGRESSION
        elif baseline in ("failed", "error", "crashed") and current == "passed":
            test.compare_status = CompareStatus.FIXED
        else:
            # Other changes (e.g., skipped <-> failed)
            test.compare_status = CompareStatus.SAME

    def handle_event(self, data: EventRequest):
        event_type = data.type
        pid = data.pid

        with self._lock:
            self._active_pids.add(pid)

            if event_type == EventType.EXIT:
                # If the worker exits while still holding a claim, requeue the
                # test (it was dequeued but never started/finished).
                claimed = self._claimed_by_pid.pop(pid, None)
                if claimed:
                    test = self._tests.get(claimed)
                    if test and test.outcome is None and test.start_time is None:
                        test.pid = None
                        test.requeues += 1
                        test_queue.put(claimed)
                self._active_pids.remove(pid)
                self._exited_pids.add(pid)
                return

            elif event_type == EventType.START:
                nodeid = data.nodeid
                if nodeid and nodeid in self._tests:
                    self._tests[nodeid].pid = pid
                    self._tests[nodeid].start_time = datetime.datetime.now()
                # START implies the claim is no longer "in limbo"
                if self._claimed_by_pid.get(pid) == nodeid:
                    self._claimed_by_pid.pop(pid, None)

            elif event_type == EventType.FINISH:
                nodeid = data.nodeid
                outcome_str = data.outcome
                output = data.output
                error_message = data.error_message
                memory_usage_mb = data.memory_usage_mb
                memory_peak_mb = data.memory_peak_mb
                if nodeid and nodeid in self._tests and outcome_str:
                    try:
                        test = self._tests[nodeid]
                        test.outcome = outcome_str
                        test.finish_time = datetime.datetime.now()
                        # If START was missed (e.g. transient HTTP issue), ensure
                        if test.start_time is None:
                            test.start_time = test.finish_time
                        if output:
                            test.output = output
                        if error_message:
                            test.error_message = error_message
                        if memory_usage_mb is not None:
                            test.memory_usage_mb = memory_usage_mb
                        if memory_peak_mb is not None:
                            test.memory_peak_mb = memory_peak_mb
                        # Compute comparison status
                        self._compute_compare_status(test)
                    except ValueError:
                        pass
                if self._claimed_by_pid.get(pid) == nodeid:
                    self._claimed_by_pid.pop(pid, None)

    def handle_worker_crash(self, pid: int):
        with self._lock:
            # If this worker had a claimed test that never started, put it back
            # into the queue. This avoids the rare "finished with queued tests"
            # state when a worker dies between /claim and START.
            claimed = self._claimed_by_pid.pop(pid, None)
            if claimed:
                test = self._tests.get(claimed)
                if test and test.outcome is None and test.start_time is None:
                    test.pid = None
                    test.requeues += 1
                    test_queue.put(claimed)

            # Find any test running on this pid
            for t in self._tests.values():
                if t.pid == pid and t.outcome is None and t.start_time is not None:
                    output = ""
                    try:
                        worker_id = next(
                            w for w, proc in workers.items() if proc.pid == pid
                        )
                        log_file = get_log_file(worker_id)
                        if log_file.exists():
                            output = log_file.read_text(encoding="utf-8")
                    except Exception:
                        pass
                    t.outcome = Outcome.CRASHED
                    t.finish_time = datetime.datetime.now()
                    t.output = {
                        "error": f"Worker process {pid} crashed while running this test.\n\n{output}"  # noqa: E501
                    }
                    self._exited_pids.add(pid)
                    if pid in self._active_pids:
                        self._active_pids.remove(pid)

    def pending_count(self) -> int:
        with self._lock:
            return sum(1 for t in self._tests.values() if t.outcome is None)

    def unstarted_pending_nodeids(self) -> list[str]:
        with self._lock:
            return [
                t.nodeid
                for t in self._tests.values()
                if t.outcome is None and t.start_time is None
            ]

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
        crashed = _count(Outcome.CRASHED)
        skipped = _count(Outcome.SKIPPED)
        running = sum(
            1 for t in tests if t.start_time is not None and t.outcome is None
        )
        queued = sum(1 for t in tests if t.start_time is None and t.outcome is None)

        # Calculate remaining based on total enqueued
        remaining = queued

        out = (
            f"WA:{workers:2} WE:{exited_workers:2}|"
            f" ✓{passed:4} ✗{failed:4} E{errored:4} C{crashed:4} S{skipped:4} R{running:4} Q{remaining:4}"  # noqa: E501
        )

        # Long-running tests
        long_tests = [
            t
            for t in tests
            if t.outcome is None
            and t.start_time is not None
            and t.start_time < now - LONG_TEST_THRESHOLD
        ]
        if long_tests:
            for t in sorted(
                long_tests, key=lambda x: cast(datetime.datetime, x.start_time)
            )[:3]:
                dur = int((now - cast(datetime.datetime, t.start_time)).total_seconds())
                # Truncate nodeid for readability
                short_id = t.nodeid.split("::")[-1][:40]
                out += f"\n * {dur:4}s:{short_id}"

        return out

    def has_failures(self) -> bool:
        with self._lock:
            return any(
                t.outcome in (Outcome.FAILED, Outcome.ERROR, Outcome.CRASHED)
                for t in self._tests.values()
            )

    def build_report_data(self) -> dict[str, Any]:
        now = datetime.datetime.now()
        with self._lock:
            tests_snapshot = [
                {
                    "nodeid": t.nodeid,
                    "pid": t.pid,
                    "start_time": t.start_time,
                    "finish_time": t.finish_time,
                    "outcome": t.outcome,
                    "output": t.output,
                    "error_message": t.error_message,
                    "memory_usage_mb": t.memory_usage_mb,
                    "memory_peak_mb": t.memory_peak_mb,
                    "compare_status": t.compare_status,
                    "baseline_outcome": t.baseline_outcome,
                    "claim_attempts": t.claim_attempts,
                    "requeues": t.requeues,
                    "collection_error": t.collection_error,
                }
                for t in self._tests.values()
            ]
            workers_active = len(self._active_pids)
            workers_exited = len(self._exited_pids)
            pid_to_worker_id = dict(self._pid_to_worker_id)
            baseline = self._baseline
            pytest_args = list(self._pytest_args)
            baseline_requested = self._baseline_requested
            collection_errors = dict(self._collection_errors)
            start_time = self.start_time

        passed = failed = errors = crashed = skipped = 0
        running = queued = 0
        regressions = fixed = new_tests = 0
        perf_regressions = 0
        perf_improvements = 0
        memory_regressions = 0
        sum_test_durations = 0.0
        durations: list[float] = []
        memory_usage_values: list[float] = []
        memory_peak_values: list[float] = []
        truncated_tests = 0
        truncated_bytes = 0

        test_entries: list[dict[str, Any]] = []

        def _build_status(t: dict[str, Any]) -> tuple[str, str | None]:
            outcome = outcome_to_str(t["outcome"])
            if t["collection_error"]:
                return "collection_error", outcome or "error"
            if outcome is None:
                return ("running", None) if t["start_time"] else ("queued", None)
            return "finished", outcome

        for t in tests_snapshot:
            state, outcome = _build_status(t)
            status = outcome or state

            if outcome == "passed":
                passed += 1
            elif outcome == "failed":
                failed += 1
            elif outcome == "error":
                errors += 1
            elif outcome == "crashed":
                crashed += 1
            elif outcome == "skipped":
                skipped += 1
            elif state == "running":
                running += 1
            elif state == "queued":
                queued += 1

            duration_s = 0.0
            if t["start_time"] and t["finish_time"]:
                duration_s = (t["finish_time"] - t["start_time"]).total_seconds()
                durations.append(duration_s)
                sum_test_durations += duration_s
            elif t["start_time"] and t["finish_time"] is None:
                duration_s = (now - t["start_time"]).total_seconds()

            if t["memory_usage_mb"] > 0:
                memory_usage_values.append(t["memory_usage_mb"])
            if t["memory_peak_mb"] > 0:
                memory_peak_values.append(t["memory_peak_mb"])

            output_full = cast(dict[str, str] | None, t["output"])
            output, output_meta = apply_output_limits(output_full)

            if state == "running" and t["pid"]:
                worker_log = self.get_worker_log(t["pid"])
                if worker_log:
                    live_output, live_meta = apply_output_limits({"live": worker_log})
                    if live_output:
                        if output is None:
                            output = {}
                            output_meta = {}
                        output["live"] = live_output["live"]
                        output_meta["live"] = live_meta["live"]

            if output_meta:
                test_truncated = False
                for meta in output_meta.values():
                    if meta.get("truncated"):
                        test_truncated = True
                        truncated_bytes += int(
                            meta.get("bytes_total", 0) - meta.get("bytes_kept", 0)
                        )
                if test_truncated:
                    truncated_tests += 1

            worker_id = pid_to_worker_id.get(t["pid"]) if t["pid"] else None
            worker_log_path = None
            if worker_id is not None:
                worker_log_path = str(get_log_file(worker_id))

            file_path, class_name, function_name, params = split_nodeid(t["nodeid"])
            error_type, error_summary = split_error_message(t["error_message"])
            baseline_rec = baseline_record(baseline.tests, t["nodeid"])
            baseline_outcome = (
                baseline_rec.get("outcome") if baseline_rec else t["baseline_outcome"]
            )
            baseline_duration_s = (
                baseline_rec.get("duration_s") if baseline_rec else None
            )
            baseline_memory_usage_mb = (
                baseline_rec.get("memory_usage_mb") if baseline_rec else None
            )
            baseline_memory_peak_mb = (
                baseline_rec.get("memory_peak_mb") if baseline_rec else None
            )

            if baseline_outcome and not t["baseline_outcome"]:
                t["baseline_outcome"] = baseline_outcome
            compare_status = get_compare_status(status, baseline_outcome)
            if compare_status == "regression":
                regressions += 1
            elif compare_status == "fixed":
                fixed += 1
            elif compare_status == "new":
                new_tests += 1

            duration_delta_s, duration_delta_pct, duration_sig = perf_change(
                duration_s,
                baseline_duration_s,
                PERF_MIN_TIME_DIFF_S,
                PERF_THRESHOLD_PERCENT,
            )
            speedup_ratio = None
            speedup_pct = None
            if baseline_duration_s and duration_s > 0:
                speedup_ratio = baseline_duration_s / duration_s
                speedup_pct = (
                    (baseline_duration_s - duration_s) / baseline_duration_s
                ) * 100

            memory_delta_mb, memory_delta_pct, memory_sig = perf_change(
                t["memory_peak_mb"],
                baseline_memory_peak_mb,
                PERF_MIN_MEMORY_DIFF_MB,
                PERF_THRESHOLD_PERCENT,
            )

            perf_status = None
            if duration_delta_pct is not None:
                if duration_delta_pct > 0:
                    perf_status = "slower"
                elif duration_delta_pct < 0:
                    perf_status = "faster"
                else:
                    perf_status = "same"

            if duration_sig and duration_delta_pct:
                if duration_delta_pct > 0:
                    perf_regressions += 1
                elif duration_delta_pct < 0:
                    perf_improvements += 1
            if memory_sig and memory_delta_pct and memory_delta_pct > 0:
                memory_regressions += 1

            test_entries.append(
                {
                    "nodeid": t["nodeid"],
                    "file": file_path,
                    "class": class_name,
                    "function": function_name,
                    "params": params,
                    "state": state,
                    "status": status,
                    "outcome": outcome,
                    "duration_s": duration_s,
                    "duration_human": format_duration(duration_s)
                    if duration_s > 0
                    else ("-" if state == "queued" else "0ms"),
                    "start_time": safe_iso(t["start_time"]),
                    "finish_time": safe_iso(t["finish_time"]),
                    "error_message": t["error_message"],
                    "error_type": error_type,
                    "error_summary": error_summary,
                    "output": output,
                    "output_full": output_full,
                    "output_meta": output_meta,
                    "memory_usage_mb": t["memory_usage_mb"],
                    "memory_peak_mb": t["memory_peak_mb"],
                    "worker_pid": t["pid"],
                    "worker_id": worker_id,
                    "worker_log": worker_log_path,
                    "compare_status": compare_status,
                    "baseline_outcome": baseline_outcome or t["baseline_outcome"],
                    "baseline_duration_s": baseline_duration_s,
                    "baseline_memory_usage_mb": baseline_memory_usage_mb,
                    "baseline_memory_peak_mb": baseline_memory_peak_mb,
                    "duration_delta_s": duration_delta_s,
                    "duration_delta_pct": duration_delta_pct,
                    "speedup_ratio": speedup_ratio,
                    "speedup_pct": speedup_pct,
                    "memory_delta_mb": memory_delta_mb,
                    "memory_delta_pct": memory_delta_pct,
                    "perf_status": perf_status,
                    "perf_regression": bool(
                        duration_sig and duration_delta_pct and duration_delta_pct > 0
                    ),
                    "perf_improvement": bool(
                        duration_sig and duration_delta_pct and duration_delta_pct < 0
                    ),
                    "memory_regression": bool(
                        memory_sig and memory_delta_pct and memory_delta_pct > 0
                    ),
                    "claim_attempts": t["claim_attempts"],
                    "requeues": t["requeues"],
                    "collection_error": t["collection_error"],
                }
            )

        test_entries.sort(key=lambda x: x["nodeid"])

        total_tests = len(test_entries)
        total_duration = (now - start_time).total_seconds()
        total_memory_mb = sum(t["memory_usage_mb"] for t in test_entries)
        workers_used = workers_active + workers_exited

        total_finished = passed + failed + errors + crashed + skipped
        progress_percent = (
            int((total_finished / total_tests) * 100) if total_tests > 0 else 0
        )

        removed_tests = 0
        removed_total = 0
        selection_applied = bool(pytest_args)
        if baseline.loaded:
            removed_total = len(
                set(baseline.tests) - {t["nodeid"] for t in test_entries}
            )
            removed_tests = 0 if selection_applied else removed_total

        duration_percentiles = percentiles(durations, [50, 90, 95, 99])
        memory_usage_percentiles = percentiles(memory_usage_values, [50, 90, 95, 99])
        memory_peak_percentiles = percentiles(memory_peak_values, [50, 90, 95, 99])

        collection_error_entries = [
            {
                "nodeid": nodeid,
                "error": error,
                "error_message": error.splitlines()[-1].strip() if error else None,
            }
            for nodeid, error in collection_errors.items()
        ]

        derived = {
            "failures": [
                {
                    "nodeid": t["nodeid"],
                    "file": t["file"],
                    "class": t["class"],
                    "function": t["function"],
                    "params": t["params"],
                    "status": t["status"],
                    "error_message": t["error_message"],
                    "error_type": t["error_type"],
                    "error_summary": t["error_summary"],
                    "duration_s": t["duration_s"],
                    "compare_status": t["compare_status"],
                    "baseline_outcome": t["baseline_outcome"],
                }
                for t in test_entries
                if t["status"] in {"failed", "error", "crashed"}
            ],
            "regressions": [
                {
                    "nodeid": t["nodeid"],
                    "file": t["file"],
                    "class": t["class"],
                    "function": t["function"],
                    "params": t["params"],
                    "status": t["status"],
                    "error_message": t["error_message"],
                    "error_type": t["error_type"],
                    "error_summary": t["error_summary"],
                    "duration_s": t["duration_s"],
                }
                for t in test_entries
                if t["compare_status"] == "regression"
            ],
            "fixed": [
                {"nodeid": t["nodeid"], "status": t["status"]}
                for t in test_entries
                if t["compare_status"] == "fixed"
            ],
            "new_tests": [
                {"nodeid": t["nodeid"], "status": t["status"]}
                for t in test_entries
                if t["compare_status"] == "new"
            ],
            "perf_regressions": [
                {
                    "nodeid": t["nodeid"],
                    "duration_delta_s": t["duration_delta_s"],
                    "duration_delta_pct": t["duration_delta_pct"],
                    "speedup_pct": t["speedup_pct"],
                    "baseline_duration_s": t["baseline_duration_s"],
                    "duration_s": t["duration_s"],
                }
                for t in test_entries
                if t["perf_regression"]
            ],
            "perf_improvements": [
                {
                    "nodeid": t["nodeid"],
                    "duration_delta_s": t["duration_delta_s"],
                    "duration_delta_pct": t["duration_delta_pct"],
                    "speedup_pct": t["speedup_pct"],
                    "baseline_duration_s": t["baseline_duration_s"],
                    "duration_s": t["duration_s"],
                }
                for t in test_entries
                if t["perf_improvement"]
            ],
            "memory_regressions": [
                {
                    "nodeid": t["nodeid"],
                    "memory_delta_mb": t["memory_delta_mb"],
                    "memory_delta_pct": t["memory_delta_pct"],
                    "baseline_memory_peak_mb": t["baseline_memory_peak_mb"],
                    "memory_peak_mb": t["memory_peak_mb"],
                }
                for t in test_entries
                if t["memory_regression"]
            ],
            "slowest": [
                {"nodeid": t["nodeid"], "duration_s": t["duration_s"]}
                for t in sorted(
                    [t for t in test_entries if t["duration_s"] > 0],
                    key=lambda x: x["duration_s"],
                    reverse=True,
                )[:10]
            ],
            "memory_heaviest": [
                {
                    "nodeid": t["nodeid"],
                    "memory_peak_mb": t["memory_peak_mb"],
                    "memory_usage_mb": t["memory_usage_mb"],
                }
                for t in sorted(
                    [t for t in test_entries if t["memory_peak_mb"] > 0],
                    key=lambda x: x["memory_peak_mb"],
                    reverse=True,
                )[:10]
            ],
            "flaky": [
                {
                    "nodeid": t["nodeid"],
                    "claim_attempts": t["claim_attempts"],
                    "requeues": t["requeues"],
                }
                for t in test_entries
                if t["claim_attempts"] > 1 or t["requeues"] > 0
            ],
            "collection_errors": collection_error_entries,
        }

        try:
            import pytest as _pytest

            pytest_version = _pytest.__version__
        except Exception:
            pytest_version = None

        report = {
            "schema_version": REPORT_SCHEMA_VERSION,
            "generated_at": safe_iso(now),
            "run": {
                "start_time": safe_iso(start_time),
                "end_time": safe_iso(now if running == 0 and queued == 0 else None),
                "duration_s": total_duration,
                "runner_argv": list(sys.argv),
                "pytest_args": pytest_args,
                "selection_applied": selection_applied,
                "collected_tests": total_tests,
                "cwd": os.getcwd(),
                "hostname": socket.gethostname(),
                "python_executable": sys.executable,
                "python_version": platform.python_version(),
                "platform": platform.platform(),
                "pytest_version": pytest_version,
                "report_interval_s": REPORT_INTERVAL_SECONDS,
                "long_test_threshold_s": int(LONG_TEST_THRESHOLD.total_seconds()),
                "workers_requested": WORKER_COUNT,
                "workers_active": workers_active,
                "workers_exited": workers_exited,
                "generate_html": GENERATE_HTML,
                "periodic_html": GENERATE_PERIODIC_HTML,
                "baseline_requested": baseline_requested,
                "env": collect_env_subset(),
                "git": get_git_info(),
                "orchestrator_bind": ORCHESTRATOR_BIND_HOST,
                "orchestrator_url": self._orchestrator_url,
                "orchestrator_report_url": self._orchestrator_report_url,
                "output_limits": {
                    "max_bytes": OUTPUT_MAX_BYTES,
                    "truncate_mode": OUTPUT_TRUNCATE_MODE,
                },
                "perf": {
                    "threshold_percent": PERF_THRESHOLD_PERCENT,
                    "min_time_diff_s": PERF_MIN_TIME_DIFF_S,
                    "min_memory_diff_mb": PERF_MIN_MEMORY_DIFF_MB,
                },
            },
            "summary": {
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "crashed": crashed,
                "skipped": skipped,
                "running": running,
                "queued": queued,
                "total": total_tests,
                "collection_errors": len(collection_error_entries),
                "regressions": regressions,
                "fixed": fixed,
                "new_tests": new_tests,
                "removed": removed_tests,
                "removed_total": removed_total,
                "baseline_scope": "partial" if selection_applied else "full",
                "perf_regressions": perf_regressions,
                "perf_improvements": perf_improvements,
                "memory_regressions": memory_regressions,
                "output_truncated_tests": truncated_tests,
                "output_truncated_bytes": truncated_bytes,
                "progress_percent": progress_percent,
                "total_duration_s": total_duration,
                "total_summed_duration_s": sum_test_durations,
                "total_memory_mb": total_memory_mb,
                "workers_used": workers_used,
                "duration_percentiles_s": duration_percentiles,
                "memory_usage_percentiles_mb": memory_usage_percentiles,
                "memory_peak_percentiles_mb": memory_peak_percentiles,
            },
            "commit": {
                "hash": commit_info.hash,
                "short_hash": commit_info.short_hash,
                "author": commit_info.author,
                "message": commit_info.message,
                "time": commit_info.time,
            }
            if commit_info.hash
            else None,
            "ci": {
                "is_ci": ci_info.is_ci,
                "run_id": ci_info.run_id,
                "run_number": ci_info.run_number,
                "workflow": ci_info.workflow,
                "job": ci_info.job,
                "runner_name": ci_info.runner_name,
                "runner_os": ci_info.runner_os,
                "actor": ci_info.actor,
                "repository": ci_info.repository,
                "ref": ci_info.ref,
            }
            if ci_info.is_ci
            else None,
            "baseline": {
                "loaded": baseline.loaded,
                "commit_hash": baseline.commit_hash,
                "commit_hash_full": baseline.commit_hash_full,
                "commit_author": baseline.commit_author,
                "commit_message": baseline.commit_message,
                "commit_time": baseline.commit_time,
                "branch": baseline.branch,
                "tests_total": len(baseline.tests) if baseline.tests else 0,
                "error": baseline.error,
            },
            "artifacts": {
                "json": str(REPORT_JSON_PATH),
                "html": str(REPORT_HTML_PATH),
                "logs_dir": str(LOG_DIR),
            },
            "collection_errors": collection_error_entries,
            "tests": test_entries,
            "derived": derived,
        }

        return report

    def write_json_report(self, report: dict[str, Any], output_path: Path):
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"Failed to write JSON report: {e}")

    def generate_html_report(
        self, report: dict[str, Any], output_path: Path = REPORT_HTML_PATH
    ):
        if not GENERATE_HTML:
            return

        tests = report["tests"]
        summary = report["summary"]

        durations = [t["duration_s"] for t in tests if t["duration_s"] > 0]
        memories = [t["memory_usage_mb"] for t in tests if t["memory_usage_mb"] > 0]
        peaks = [t["memory_peak_mb"] for t in tests if t["memory_peak_mb"] > 0]
        durations.sort()
        memories.sort()
        peaks.sort()

        rows = []

        def sort_key(t):
            return t["nodeid"]

        for t in sorted(tests, key=sort_key):
            duration_val = t["duration_s"]
            if t["state"] == "queued":
                duration_val = -1.0
            duration_style = ""
            if duration_val > 0:
                duration = format_duration(duration_val)
                if durations:
                    rank = bisect.bisect_left(durations, duration_val)
                    pct = rank / (len(durations) - 1) if len(durations) > 1 else 0
                    r = int(166 + (243 - 166) * pct)
                    g = int(227 + (139 - 227) * pct)
                    b = int(161 + (168 - 161) * pct)
                    duration_style = f"background-color: rgba({r}, {g}, {b}, 0.25)"
            else:
                duration = t["duration_human"]
                if t["state"] == "running":
                    duration = f"{duration} (running)"

            outcome_class = t["status"]
            outcome_text = t["status"].upper()

            log_button = ""
            log_modal = ""
            log_content = ""

            output = t.get("output") or {}
            output_meta = t.get("output_meta") or {}

            def _append_log_section(title: str, content: str, key: str):
                nonlocal log_content
                meta = output_meta.get(key, {})
                note = ""
                if meta.get("truncated"):
                    note = (
                        f'<div class="log-note">truncated: kept '
                        f"{meta.get('bytes_kept')} of {meta.get('bytes_total')} bytes"
                        f"</div>"
                    )
                log_content += (
                    f'<div class="log-section"><h3>{title}</h3>'
                    f"{note}<pre>{content}</pre></div>"
                )

            if output:
                if output.get("stdout"):
                    _append_log_section(
                        "STDOUT", ansi_to_html(output["stdout"]), "stdout"
                    )
                if output.get("stderr"):
                    _append_log_section(
                        "STDERR", ansi_to_html(output["stderr"]), "stderr"
                    )
                if output.get("log"):
                    _append_log_section("LOG", ansi_to_html(output["log"]), "log")
                if output.get("error"):
                    _append_log_section("ERROR", ansi_to_html(output["error"]), "error")
                if output.get("live"):
                    _append_log_section(
                        "LIVE OUTPUT", ansi_to_html(output["live"]), "live"
                    )

            # Always show stream link to database logs
            safe_nodeid = html.escape(t["nodeid"])
            url_nodeid = url_quote(t["nodeid"], safe="")
            test_run_id = self._test_run_id or ""
            stream_link = (
                f'<a href="/logs?test_run_id={test_run_id}&test_name={url_nodeid}" '
                f'target="_blank" class="stream-link" title="Stream logs">&#128203;</a>'
            )
            log_button = stream_link

            # Add modal button and content only if there's embedded output
            if log_content:
                modal_id = f"modal_{safe_nodeid}"
                log_button += (
                    f"<button onclick=\"openModal('{modal_id}')\">View</button>"
                )
                log_modal = f"""
                <div id="{modal_id}" class="modal">
                  <div class="modal-content">
                    <div class="modal-header">
                      <h2>Logs for {t["nodeid"]}</h2>
                      <div class="modal-buttons">
                        <button class="copy-btn" onclick="copyLogs('{modal_id}')">Copy</button>
                        <button class="close-btn" onclick="closeModal('{modal_id}')">&times;</button>
                      </div>
                    </div>
                    {log_content}
                  </div>
                </div>
                """  # noqa: E501

            worker_info = (
                f"Worker PID: {t['worker_pid']}" if t.get("worker_pid") else ""
            )
            duration_cell = (
                f'<td style="{duration_style}" title="{worker_info}" '
                f'data-value="{duration_val}">{duration}</td>'
            )

            speedup_pct = t.get("speedup_pct")
            speedup_ratio = t.get("speedup_ratio")
            speedup_cell = "<td>-</td>"
            if speedup_pct is not None and speedup_ratio is not None:
                speedup_style = ""
                if speedup_pct > 0:
                    speedup_style = "color: var(--ctp-green); font-weight: bold;"
                elif speedup_pct < 0:
                    speedup_style = "color: var(--ctp-red); font-weight: bold;"

                if speedup_ratio >= 1:
                    speedup_text = f"{speedup_ratio:.1f}x"
                    speedup_title = f"{speedup_pct:+.1f}% ({speedup_ratio:.2f}x)"
                else:
                    slowdown = 1 / speedup_ratio if speedup_ratio else 0.0
                    speedup_text = f"-{slowdown:.1f}x"
                    speedup_title = f"{speedup_pct:+.1f}% (-{slowdown:.2f}x)"

                speedup_title += (
                    f" baseline {t.get('baseline_duration_s')},"
                    f" current {t.get('duration_s')}"
                )

                speedup_cell = (
                    f'<td style="{speedup_style}" data-value="{speedup_pct}" '
                    f'title="{speedup_title}">{speedup_text}</td>'
                )

            memory_val = t["memory_usage_mb"]
            memory_str = f"{memory_val:.2f} MB" if memory_val > 0 else "-"
            memory_style = ""
            if memories and memory_val > 0:
                rank = bisect.bisect_left(memories, memory_val)
                pct = rank / (len(memories) - 1) if len(memories) > 1 else 0
                r = int(166 + (243 - 166) * pct)
                g = int(227 + (139 - 227) * pct)
                b = int(161 + (168 - 161) * pct)
                memory_style = f"background-color: rgba({r}, {g}, {b}, 0.25)"

            memory_cell = (
                f'<td style="{memory_style}" data-value="{memory_val}"'
                f">{memory_str}</td>"
            )

            peak_val = t["memory_peak_mb"]
            peak_str = f"{peak_val:.2f} MB" if peak_val > 0 else "-"
            peak_style = ""
            if peaks and peak_val > 0:
                rank = bisect.bisect_left(peaks, peak_val)
                pct = rank / (len(peaks) - 1) if len(peaks) > 1 else 0
                r = int(166 + (243 - 166) * pct)
                g = int(227 + (139 - 227) * pct)
                b = int(161 + (168 - 161) * pct)
                peak_style = f"background-color: rgba({r}, {g}, {b}, 0.25)"

            peak_cell = (
                f'<td style="{peak_style}" data-value="{peak_val}">{peak_str}</td>'
            )

            error_msg = t.get("error_message") or ""
            if error_msg:
                error_msg_escaped = (
                    error_msg.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                )
                error_msg_display = (
                    error_msg_escaped[:100] + "..."
                    if len(error_msg_escaped) > 100
                    else error_msg_escaped
                )
                # Use different class for skip reasons (yellow) vs errors (red)
                cell_class = "skip-cell" if outcome_class == "skipped" else "error-cell"
                error_cell = (
                    f'<td class="{cell_class}" title="{error_msg_escaped}">'
                    f"{error_msg_display}</td>"
                )
            else:
                error_cell = "<td>-</td>"

            row_class = f"row-{outcome_class}"

            compare_cell = ""
            baseline = report.get("baseline") or {}
            if baseline.get("loaded"):
                cmp = t.get("compare_status")
                if cmp == "regression":
                    compare_cell = '<td class="compare-regression">regression</td>'
                    row_class += " row-regression"
                elif cmp == "fixed":
                    compare_cell = '<td class="compare-fixed">fixed</td>'
                    row_class += " row-fixed"
                elif cmp == "new":
                    compare_cell = '<td class="compare-new">new</td>'
                    row_class += " row-new"
                elif cmp == "same":
                    compare_cell = '<td class="compare-same">-</td>'
                else:
                    compare_cell = "<td>-</td>"
            else:
                compare_cell = '<td class="compare-na">-</td>'

            rows.append(
                f"""
            <tr class="{row_class}">
                <td>{t["file"]}</td>
                <td>{t["class"]}</td>
                <td>{t["function"]}</td>
                <td>{t["params"]}</td>
                <td class="{outcome_class}">{outcome_text}</td>
                {compare_cell}
                {duration_cell}
                {speedup_cell}
                {memory_cell}
                {peak_cell}
                {error_cell}
                <td>{log_button} {log_modal}</td>
            </tr>
            """
            )

        try:
            total_duration_str = format_duration(summary["total_duration_s"])

            commit_info_html = ""
            commit = report.get("commit") or {}
            if commit.get("hash"):
                short_hash = html.escape(str(commit.get("short_hash") or ""))
                full_hash = html.escape(str(commit.get("hash") or ""))
                author = html.escape(str(commit.get("author") or ""))
                time_str = html.escape(str(commit.get("time") or ""))
                message = html.escape(str(commit.get("message") or ""), quote=True)
                parts = [f"<code>{short_hash}</code>"]
                if full_hash and full_hash != short_hash:
                    parts.append(f"full {full_hash}")
                if author:
                    parts.append(f"author {author}")
                if time_str:
                    parts.append(f"date {time_str}")
                if message:
                    parts.append(f'msg <em>"{message}"</em>')
                commit_info_html = "<br><strong>HEAD:</strong> " + " | ".join(parts)

            ci_info_html = ""
            ci = report.get("ci") or {}
            if ci.get("is_ci"):
                ci_parts = []
                if ci.get("workflow"):
                    ci_parts.append(f"Workflow: {ci.get('workflow')}")
                if ci.get("job"):
                    ci_parts.append(f"Job: {ci.get('job')}")
                if ci.get("run_id"):
                    ci_parts.append(f"Run ID: {ci.get('run_id')}")
                if ci.get("runner_name"):
                    ci_parts.append(f"Runner: {ci.get('runner_name')}")
                if ci.get("runner_os"):
                    ci_parts.append(f"({ci.get('runner_os')})")
                if ci_parts:
                    ci_info_html = "<strong>CI:</strong> " + " | ".join(ci_parts)

            baseline_info_html = ""
            if baseline.get("loaded"):
                baseline_short = html.escape(str(baseline.get("commit_hash") or ""))
                baseline_full = html.escape(str(baseline.get("commit_hash_full") or ""))
                baseline_author = html.escape(str(baseline.get("commit_author") or ""))
                baseline_time = html.escape(str(baseline.get("commit_time") or ""))
                baseline_message = html.escape(
                    str(baseline.get("commit_message") or ""), quote=True
                )
                baseline_branch = html.escape(str(baseline.get("branch") or ""))
                tests_total = baseline.get("tests_total", 0)
                parts = [f"<code>{baseline_short}</code>"]
                if baseline_full and baseline_full != baseline_short:
                    parts.append(f"full {baseline_full}")
                if baseline_branch:
                    parts.append(f"branch <code>{baseline_branch}</code>")
                if baseline_author:
                    parts.append(f"author {baseline_author}")
                if baseline_time:
                    parts.append(f"date {baseline_time}")
                if baseline_message:
                    parts.append(f'msg <em>"{baseline_message}"</em>')
                parts.append(f"{tests_total} tests")
                baseline_info_html = "<br><strong>Baseline:</strong> " + " | ".join(
                    parts
                )
            elif baseline.get("error"):
                baseline_info_html = (
                    f'<br><span class="baseline-error">'
                    f"<strong>Baseline:</strong> {baseline.get('error')}</span>"
                )

            # Get available local baselines for dropdown
            local_baselines = list_local_baselines()
            baselines_json = json.dumps(local_baselines)

            # Get remote commits for dropdown
            with remote_commits_lock:
                remote_commits_list = list(remote_commits)
            remote_commits_json = json.dumps(remote_commits_list)

            # Determine current baseline identifier and info for dropdown
            current_baseline = ""
            current_baseline_info = "-- No baseline --"
            if baseline.get("loaded"):
                baseline_requested = report.get("run", {}).get("baseline_requested")
                # Check if this is a local baseline
                if baseline_requested and any(
                    b.get("name") == baseline_requested for b in local_baselines
                ):
                    current_baseline = f"local:{baseline_requested}"
                    current_baseline_info = f"Local: {baseline_requested}"
                elif baseline.get("commit_hash"):
                    # Remote baseline from GitHub
                    commit = baseline.get("commit_hash") or "unknown"
                    branch = baseline.get("branch") or ""
                    current_baseline = f"remote:{commit}"
                    if branch:
                        current_baseline_info = f"Remote: {commit} ({branch})"
                    else:
                        current_baseline_info = f"Remote: {commit}"
            elif baseline.get("error"):
                current_baseline_info = "-- Baseline error --"

            html_ = HTML_TEMPLATE.render(
                status="Running"
                if summary["running"] > 0 or summary["queued"] > 0
                else "Finished",
                workers_active=report["run"]["workers_active"],
                workers_total=report["run"].get("workers_requested", WORKER_COUNT),
                passed=summary["passed"],
                failed=summary["failed"],
                errors=summary["errors"],
                crashed=summary["crashed"],
                skipped=summary["skipped"],
                running=summary["running"],
                remaining=summary["queued"],
                regressions=summary["regressions"],
                fixed=summary["fixed"],
                new_tests=summary["new_tests"],
                progress_percent=summary["progress_percent"],
                rows="\n".join(rows),
                timestamp=report["generated_at"],
                finishing_time=report["run"]["end_time"] or report["generated_at"],
                total_duration=total_duration_str,
                total_summed_duration=format_duration(
                    summary["total_summed_duration_s"]
                ),
                total_memory=f"{summary['total_memory_mb']:.2f} MB",
                refresh_meta="",
                commit_info_html=commit_info_html,
                ci_info_html=ci_info_html,
                baseline_info_html=baseline_info_html,
                baselines_json=baselines_json,
                remote_commits_json=remote_commits_json,
                current_baseline=current_baseline,
                current_baseline_info=current_baseline_info,
                test_run_id=self._test_run_id or "",
            )
        except Exception as e:
            print(f"Failed to format HTML report: {e}")
            return

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(html_, encoding="utf-8")
        except Exception as e:
            print(f"Failed to write HTML report: {e}")

    def generate_reports(
        self,
        periodic: bool = False,
    ) -> dict[str, Any]:
        report = self.build_report_data()
        self.write_json_report(report, REPORT_JSON_PATH)
        if not periodic or GENERATE_PERIODIC_HTML:
            self.generate_html_report(report, REPORT_HTML_PATH)
        return report


def _rebuild_report_with_baseline(
    report: dict[str, Any], baseline: RemoteBaseline, baseline_commit: str | None
) -> dict[str, Any]:
    now = datetime.datetime.now()
    tests = report.get("tests", [])
    summary = report.get("summary", {}) or {}
    run = report.get("run", {}) or {}

    selection_applied = run.get("selection_applied")
    if selection_applied is None:
        selection_applied = bool(run.get("pytest_args"))
        run["selection_applied"] = selection_applied

    passed = failed = errors = crashed = skipped = 0
    running = queued = 0
    regressions = fixed = new_tests = 0
    perf_regressions = 0
    perf_improvements = 0
    memory_regressions = 0
    sum_test_durations = 0.0
    durations: list[float] = []
    memory_usage_values: list[float] = []
    memory_peak_values: list[float] = []

    for t in tests:
        nodeid = t.get("nodeid")
        outcome = outcome_to_str(t.get("outcome") or t.get("status"))
        status = t.get("status") or outcome or "queued"

        if status == "passed":
            passed += 1
        elif status == "failed":
            failed += 1
        elif status == "error":
            errors += 1
        elif status == "crashed":
            crashed += 1
        elif status == "skipped":
            skipped += 1
        elif status == "running":
            running += 1
        elif status == "queued":
            queued += 1

        duration_s = t.get("duration_s") or 0.0
        if duration_s:
            durations.append(duration_s)
            sum_test_durations += duration_s

        mem_usage = t.get("memory_usage_mb") or 0.0
        mem_peak = t.get("memory_peak_mb") or 0.0
        if mem_usage:
            memory_usage_values.append(mem_usage)
        if mem_peak:
            memory_peak_values.append(mem_peak)

        baseline_rec = baseline_record(baseline.tests, nodeid) if nodeid else None
        baseline_outcome = baseline_rec.get("outcome") if baseline_rec else None
        cmp_status = (
            get_compare_status(status, baseline_outcome) if baseline.loaded else None
        )
        t["compare_status"] = cmp_status
        t["baseline_outcome"] = baseline_outcome

        if cmp_status == "regression":
            regressions += 1
        elif cmp_status == "fixed":
            fixed += 1
        elif cmp_status == "new":
            new_tests += 1

        baseline_duration_s = baseline_rec.get("duration_s") if baseline_rec else None
        baseline_memory_usage_mb = (
            baseline_rec.get("memory_usage_mb") if baseline_rec else None
        )
        baseline_memory_peak_mb = (
            baseline_rec.get("memory_peak_mb") if baseline_rec else None
        )

        t["baseline_duration_s"] = baseline_duration_s
        t["baseline_memory_usage_mb"] = baseline_memory_usage_mb
        t["baseline_memory_peak_mb"] = baseline_memory_peak_mb

        duration_delta_s, duration_delta_pct, duration_sig = perf_change(
            duration_s,
            baseline_duration_s,
            PERF_MIN_TIME_DIFF_S,
            PERF_THRESHOLD_PERCENT,
        )
        speedup_ratio = None
        speedup_pct = None
        if baseline_duration_s and duration_s:
            speedup_ratio = baseline_duration_s / duration_s
            speedup_pct = (
                (baseline_duration_s - duration_s) / baseline_duration_s
            ) * 100

        memory_delta_mb, memory_delta_pct, memory_sig = perf_change(
            mem_peak,
            baseline_memory_peak_mb,
            PERF_MIN_MEMORY_DIFF_MB,
            PERF_THRESHOLD_PERCENT,
        )

        t["duration_delta_s"] = duration_delta_s
        t["duration_delta_pct"] = duration_delta_pct
        t["speedup_ratio"] = speedup_ratio
        t["speedup_pct"] = speedup_pct
        t["memory_delta_mb"] = memory_delta_mb
        t["memory_delta_pct"] = memory_delta_pct
        t["perf_status"] = None
        if duration_delta_pct is not None:
            if duration_delta_pct > 0:
                t["perf_status"] = "slower"
            elif duration_delta_pct < 0:
                t["perf_status"] = "faster"
            else:
                t["perf_status"] = "same"

        t["perf_regression"] = bool(
            duration_sig and duration_delta_pct and duration_delta_pct > 0
        )
        t["perf_improvement"] = bool(
            duration_sig and duration_delta_pct and duration_delta_pct < 0
        )
        t["memory_regression"] = bool(
            memory_sig and memory_delta_pct and memory_delta_pct > 0
        )

        if t["perf_regression"]:
            perf_regressions += 1
        if t["perf_improvement"]:
            perf_improvements += 1
        if t["memory_regression"]:
            memory_regressions += 1

    removed_total = 0
    removed_tests = 0
    if baseline.loaded:
        removed_total = len(set(baseline.tests) - {t.get("nodeid") for t in tests})
        removed_tests = 0 if selection_applied else removed_total

    duration_percentiles = percentiles(durations, [50, 90, 95, 99])
    memory_usage_percentiles = percentiles(memory_usage_values, [50, 90, 95, 99])
    memory_peak_percentiles = percentiles(memory_peak_values, [50, 90, 95, 99])

    total_duration = summary.get("total_duration_s")
    if total_duration is None:
        total_duration = run.get("duration_s", 0.0)
    total_memory_mb = sum(t.get("memory_usage_mb", 0.0) for t in tests)

    total_tests = len(tests)
    total_finished = passed + failed + errors + crashed + skipped
    progress_percent = int((total_finished / total_tests) * 100) if total_tests else 0

    report["generated_at"] = safe_iso(now)
    report["summary"] = {
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "crashed": crashed,
        "skipped": skipped,
        "running": running,
        "queued": queued,
        "total": total_tests,
        "collection_errors": len(report.get("collection_errors", [])),
        "regressions": regressions,
        "fixed": fixed,
        "new_tests": new_tests,
        "removed": removed_tests,
        "removed_total": removed_total,
        "baseline_scope": "partial" if selection_applied else "full",
        "perf_regressions": perf_regressions,
        "perf_improvements": perf_improvements,
        "memory_regressions": memory_regressions,
        "output_truncated_tests": summary.get("output_truncated_tests", 0),
        "output_truncated_bytes": summary.get("output_truncated_bytes", 0),
        "progress_percent": progress_percent,
        "total_duration_s": total_duration,
        "total_summed_duration_s": sum_test_durations,
        "total_memory_mb": total_memory_mb,
        "workers_used": summary.get("workers_used", 0),
        "duration_percentiles_s": duration_percentiles,
        "memory_usage_percentiles_mb": memory_usage_percentiles,
        "memory_peak_percentiles_mb": memory_peak_percentiles,
    }

    report["baseline"] = {
        "loaded": baseline.loaded,
        "commit_hash": baseline.commit_hash,
        "commit_hash_full": baseline.commit_hash_full,
        "commit_author": baseline.commit_author,
        "commit_message": baseline.commit_message,
        "commit_time": baseline.commit_time,
        "branch": baseline.branch,
        "tests_total": len(baseline.tests) if baseline.tests else 0,
        "error": baseline.error,
    }

    run["baseline_requested"] = baseline_commit
    run["perf"] = {
        "threshold_percent": PERF_THRESHOLD_PERCENT,
        "min_time_diff_s": PERF_MIN_TIME_DIFF_S,
        "min_memory_diff_mb": PERF_MIN_MEMORY_DIFF_MB,
    }
    report["run"] = run

    report["derived"] = {
        "failures": [
            {
                "nodeid": t.get("nodeid"),
                "file": t.get("file"),
                "class": t.get("class"),
                "function": t.get("function"),
                "params": t.get("params"),
                "status": t.get("status"),
                "error_message": t.get("error_message"),
                "error_type": t.get("error_type"),
                "error_summary": t.get("error_summary"),
                "duration_s": t.get("duration_s"),
                "compare_status": t.get("compare_status"),
                "baseline_outcome": t.get("baseline_outcome"),
            }
            for t in tests
            if t.get("status") in {"failed", "error", "crashed"}
        ],
        "regressions": [
            {
                "nodeid": t.get("nodeid"),
                "file": t.get("file"),
                "class": t.get("class"),
                "function": t.get("function"),
                "params": t.get("params"),
                "status": t.get("status"),
                "error_message": t.get("error_message"),
                "error_type": t.get("error_type"),
                "error_summary": t.get("error_summary"),
                "duration_s": t.get("duration_s"),
            }
            for t in tests
            if t.get("compare_status") == "regression"
        ],
        "fixed": [
            {"nodeid": t.get("nodeid"), "status": t.get("status")}
            for t in tests
            if t.get("compare_status") == "fixed"
        ],
        "new_tests": [
            {"nodeid": t.get("nodeid"), "status": t.get("status")}
            for t in tests
            if t.get("compare_status") == "new"
        ],
        "perf_regressions": [
            {
                "nodeid": t.get("nodeid"),
                "duration_delta_s": t.get("duration_delta_s"),
                "duration_delta_pct": t.get("duration_delta_pct"),
                "speedup_pct": t.get("speedup_pct"),
                "baseline_duration_s": t.get("baseline_duration_s"),
                "duration_s": t.get("duration_s"),
            }
            for t in tests
            if t.get("perf_regression")
        ],
        "perf_improvements": [
            {
                "nodeid": t.get("nodeid"),
                "duration_delta_s": t.get("duration_delta_s"),
                "duration_delta_pct": t.get("duration_delta_pct"),
                "speedup_pct": t.get("speedup_pct"),
                "baseline_duration_s": t.get("baseline_duration_s"),
                "duration_s": t.get("duration_s"),
            }
            for t in tests
            if t.get("perf_improvement")
        ],
        "memory_regressions": [
            {
                "nodeid": t.get("nodeid"),
                "memory_delta_mb": t.get("memory_delta_mb"),
                "memory_delta_pct": t.get("memory_delta_pct"),
                "baseline_memory_peak_mb": t.get("baseline_memory_peak_mb"),
                "memory_peak_mb": t.get("memory_peak_mb"),
            }
            for t in tests
            if t.get("memory_regression")
        ],
        "slowest": [
            {"nodeid": t.get("nodeid"), "duration_s": t.get("duration_s")}
            for t in sorted(
                [t for t in tests if t.get("duration_s", 0) > 0],
                key=lambda x: x.get("duration_s", 0),
                reverse=True,
            )[:10]
        ],
        "memory_heaviest": [
            {
                "nodeid": t.get("nodeid"),
                "memory_peak_mb": t.get("memory_peak_mb"),
                "memory_usage_mb": t.get("memory_usage_mb"),
            }
            for t in sorted(
                [t for t in tests if t.get("memory_peak_mb", 0) > 0],
                key=lambda x: x.get("memory_peak_mb", 0),
                reverse=True,
            )[:10]
        ],
        "flaky": [
            {
                "nodeid": t.get("nodeid"),
                "claim_attempts": t.get("claim_attempts", 0),
                "requeues": t.get("requeues", 0),
            }
            for t in tests
            if t.get("claim_attempts", 0) > 1 or t.get("requeues", 0) > 0
        ],
        "collection_errors": report.get("collection_errors", []),
    }

    return report


def rebuild_reports_from_existing(
    report_path: Path,
    baseline_commit: str | None = None,
):
    if not report_path.exists():
        raise FileNotFoundError(f"Report not found: {report_path}")
    report = json.loads(report_path.read_text())
    baseline = fetch_remote_report(commit_hash=baseline_commit)
    if not baseline.loaded:
        raise RuntimeError(baseline.error or "Failed to load baseline")
    updated = _rebuild_report_with_baseline(report, baseline, baseline_commit)
    TestAggregator([], RemoteBaseline()).write_json_report(updated, REPORT_JSON_PATH)
    TestAggregator([], RemoteBaseline()).generate_html_report(updated, REPORT_HTML_PATH)
    return updated


# IMPORTANT: TestAggregator instantiation moved to main()
# # Global aggregator instance (initialized in main)
aggregator: TestAggregator | None = None
