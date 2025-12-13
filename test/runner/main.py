#!/usr/bin/env python3
"""
CI test orchestrator using FastAPI and custom workers.

Replaces pytest-xdist with a central orchestrator that distributes tests
to persistent worker processes via HTTP.
"""

import bisect
import datetime
import json
import os
import queue
import shutil
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, cast

import uvicorn
from fastapi import FastAPI

# Ensure we can import from test package
sys.path.insert(0, os.getcwd())

from test.runner.common import (
    ClaimRequest,
    ClaimResponse,
    EventRequest,
    EventType,
    Outcome,
)


@dataclass
class CommitInfo:
    """Git commit information."""

    hash: Optional[str] = None
    short_hash: Optional[str] = None
    author: Optional[str] = None
    message: Optional[str] = None
    time: Optional[str] = None


@dataclass
class CIInfo:
    """GitHub CI information."""

    is_ci: bool = False
    run_id: Optional[str] = None
    run_number: Optional[str] = None
    workflow: Optional[str] = None
    job: Optional[str] = None
    runner_name: Optional[str] = None
    runner_os: Optional[str] = None
    actor: Optional[str] = None
    repository: Optional[str] = None
    ref: Optional[str] = None


def _load_github_event() -> Optional[dict[str, Any]]:
    """
    Load the GitHub Actions event payload if available.

    In GitHub Actions, `GITHUB_EVENT_PATH` points to a JSON file describing the
    triggering event (push, pull_request, etc.).
    """

    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        return None

    try:
        raw = Path(event_path).read_text(encoding="utf-8")
        return cast(dict[str, Any], json.loads(raw))
    except Exception:
        # Robustness: malformed JSON / file missing / permissions / etc.
        return None


def _commit_info_from_github_event_for_merge_ref(
    event: Optional[dict[str, Any]], ref: str
) -> Optional[CommitInfo]:
    """
    GitHub Actions quirk:
    - For `pull_request` workflows, the default checkout ref is often
      `refs/pull/<id>/merge` (a synthetic merge commit created by GitHub).
    - `git log -1` on that ref yields a merge commit subject like
      "Merge <head> into <base>", which is not useful in our report.

    When we detect this, prefer the PR head SHA. If the head commit object is
    present locally (our workflow does `git fetch --unshallow`), we can then
    `git log -1 <sha>` to get the real commit subject/author/time.

    If the commit object is *not* present, we still return a useful message
    (PR title) from the event payload.
    """

    if not (ref.startswith("refs/pull/") and ref.endswith("/merge")):
        return None

    if not event:
        return None

    pr = event.get("pull_request")
    if not isinstance(pr, dict):
        return None

    head = pr.get("head")
    if not isinstance(head, dict):
        return None

    sha = head.get("sha")
    if not isinstance(sha, str) or not sha:
        return None

    info = CommitInfo(hash=sha, short_hash=sha[:8])

    # Best-effort fallback values if we can't resolve the commit via git.
    title = pr.get("title")
    if isinstance(title, str) and title:
        info.message = title

    user = pr.get("user")
    if isinstance(user, dict):
        login = user.get("login")
        if isinstance(login, str) and login:
            info.author = login

    # Note: this is PR metadata time, not the commit time, but better than nothing.
    updated_at = pr.get("updated_at") or pr.get("created_at")
    if isinstance(updated_at, str) and updated_at:
        info.time = updated_at

    return info


def get_commit_info() -> CommitInfo:
    """
    Get git commit information. Returns CommitInfo with None fields if not in a git repo
    or if git commands fail.
    """
    info = CommitInfo()

    try:
        # If we're in CI on a PR merge ref, prefer the PR's head SHA from the event
        # payload. This avoids reporting the synthetic merge commit subject.
        event = (
            _load_github_event() if os.environ.get("GITHUB_ACTIONS") == "true" else None
        )
        ref = os.environ.get("GITHUB_REF") or ""
        event_commit = _commit_info_from_github_event_for_merge_ref(
            event=event, ref=ref
        )
        if event_commit is not None:
            info = event_commit

        # Check if we're in a git repository
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"], capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return info  # Not a git repo

        # Choose which commit we want to report.
        #
        # - If we already found a preferred commit hash from the GitHub event, use it,
        #   but only if it exists in this checkout (best-effort verify).
        # - Otherwise:
        #   - In CI, fall back to GITHUB_SHA (push events)
        #   - Finally fall back to HEAD
        sha: Optional[str] = info.hash
        if sha:
            verify = subprocess.run(
                ["git", "rev-parse", "--verify", f"{sha}^{{commit}}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if verify.returncode != 0:
                # Can't resolve the commit object; keep fallback event info but don't
                # attempt git log on this sha.
                sha = None

        if not sha:
            sha = (
                os.environ.get("GITHUB_SHA")
                if os.environ.get("GITHUB_ACTIONS") == "true"
                else None
            )

        if not sha:
            sha = "HEAD"

        # Normalize/resolve to full hash.
        result = subprocess.run(
            ["git", "rev-parse", sha], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            info.hash = result.stdout.strip()
            info.short_hash = info.hash[:8] if info.hash else None

        # Get author
        result = subprocess.run(
            ["git", "log", "-1", "--format=%an <%ae>", sha],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            info.author = result.stdout.strip()

        # Get commit message (first line only)
        result = subprocess.run(
            ["git", "log", "-1", "--format=%s", sha],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            info.message = result.stdout.strip()

        # Get commit time
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ci", sha],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            info.time = result.stdout.strip()

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        # git not installed, timeout, or other OS error
        pass
    except Exception:
        # Catch any unexpected errors to ensure robustness
        pass

    return info


def get_ci_info() -> CIInfo:
    """
    Get GitHub CI information from environment variables.
    Returns CIInfo with is_ci=False if not running in GitHub Actions.
    """
    info = CIInfo()

    # Check if we're running in GitHub Actions
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return info

    info.is_ci = True
    info.run_id = os.environ.get("GITHUB_RUN_ID")
    info.run_number = os.environ.get("GITHUB_RUN_NUMBER")
    info.workflow = os.environ.get("GITHUB_WORKFLOW")
    info.job = os.environ.get("GITHUB_JOB")
    info.runner_name = os.environ.get("RUNNER_NAME")
    info.runner_os = os.environ.get("RUNNER_OS")
    info.actor = os.environ.get("GITHUB_ACTOR")
    info.repository = os.environ.get("GITHUB_REPOSITORY")
    info.ref = os.environ.get("GITHUB_REF")

    return info


# Global commit and CI info (populated once at startup)
commit_info: CommitInfo = CommitInfo()
ci_info: CIInfo = CIInfo()

# Configuration
REPORT_INTERVAL_SECONDS = int(os.getenv("FBRK_TEST_REPORT_INTERVAL", 5))
LONG_TEST_THRESHOLD = datetime.timedelta(
    seconds=int(os.getenv("FBRK_TEST_LONG_THRESHOLD", 10))
)
# Default to CPU count
WORKER_COUNT = int(os.getenv("FBRK_TEST_WORKERS", 0))
if WORKER_COUNT == 0:
    WORKER_COUNT = os.cpu_count()*2 or 1
elif WORKER_COUNT < 0:
    WORKER_COUNT = max(((os.cpu_count() or 1) * -WORKER_COUNT) // 2, 1)
# Generate HTML report
GENERATE_HTML = os.getenv("FBRK_TEST_GENERATE_HTML", "1") == "1"
GENERATE_PERIODIC_HTML = os.getenv("FBRK_TEST_PERIODIC_HTML", "1") == "1"

# Global state
test_queue = queue.Queue()
tests_total = 0
workers: dict[int, subprocess.Popen[bytes]] = {}

# Read HTML template from file
HTML_TEMPLATE = (Path(__file__).parent / "report.html").read_text(encoding="utf-8")


@dataclass
class TestState:
    nodeid: str
    pid: int | None
    start_time: datetime.datetime | None
    outcome: Outcome | None = None
    finish_time: datetime.datetime | None = None
    output: dict | None = None
    error_message: str | None = None
    memory_usage_mb: float = 0.0
    memory_peak_mb: float = 0.0


def _ts() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S")


def _print(msg: str):
    print(f"[{_ts()}] {msg}", flush=True)


def format_duration(seconds: float) -> str:
    if seconds < 1.0:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60.0:
        return f"{seconds:.2f}s"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.0f}s"


class TestAggregator:
    """Aggregates test events from multiple workers."""

    def __init__(self, all_tests: list[str]):
        self._tests: dict[str, TestState] = {
            t: TestState(nodeid=t, pid=None, start_time=None) for t in all_tests
        }
        self._lock = threading.Lock()
        self._active_pids: set[int] = set()
        self._exited_pids: set[int] = set()
        self.start_time = datetime.datetime.now()

    def handle_event(self, data: EventRequest):
        event_type = data.type
        pid = data.pid

        with self._lock:
            self._active_pids.add(pid)

            if event_type == EventType.EXIT:
                self._active_pids.remove(pid)
                self._exited_pids.add(pid)
                return

            elif event_type == EventType.START:
                nodeid = data.nodeid
                if nodeid and nodeid in self._tests:
                    self._tests[nodeid].pid = pid
                    self._tests[nodeid].start_time = datetime.datetime.now()

            elif event_type == EventType.FINISH:
                nodeid = data.nodeid
                outcome_str = data.outcome
                output = data.output
                error_message = data.error_message
                memory_usage_mb = data.memory_usage_mb
                memory_peak_mb = data.memory_peak_mb
                if nodeid and nodeid in self._tests and outcome_str:
                    try:
                        self._tests[nodeid].outcome = outcome_str
                        self._tests[nodeid].finish_time = datetime.datetime.now()
                        if output:
                            self._tests[nodeid].output = output
                        if error_message:
                            self._tests[nodeid].error_message = error_message
                        if memory_usage_mb is not None:
                            self._tests[nodeid].memory_usage_mb = memory_usage_mb
                        if memory_peak_mb is not None:
                            self._tests[nodeid].memory_peak_mb = memory_peak_mb
                    except ValueError:
                        pass

    def handle_worker_crash(self, pid: int):
        with self._lock:
            # Find any test running on this pid
            for t in self._tests.values():
                if t.pid == pid and t.outcome is None and t.start_time is not None:
                    worker_id = [w for w in workers.keys() if workers[w].pid == pid][0]
                    log_file = get_log_file(worker_id)
                    output = log_file.read_text(encoding="utf-8")
                    t.outcome = Outcome.CRASHED
                    t.finish_time = datetime.datetime.now()
                    t.output = {
                        "error": f"Worker process {pid} crashed while running this test.\n\n{output}"  # noqa: E501
                    }
                    self._exited_pids.add(pid)
                    if pid in self._active_pids:
                        self._active_pids.remove(pid)

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
        queued = sum(1 for t in tests if t.start_time is None)

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

    def generate_html_report(self, output_path: str = "artifacts/test-report.html"):
        if not GENERATE_HTML:
            return

        with self._lock:
            # Create a copy of the values to avoid modification during iteration if any
            tests = list(self._tests.values())
            workers_active = len(self._active_pids)

        passed = sum(1 for t in tests if t.outcome == Outcome.PASSED)
        failed = sum(1 for t in tests if t.outcome == Outcome.FAILED)
        errors = sum(1 for t in tests if t.outcome == Outcome.ERROR)
        crashed = sum(1 for t in tests if t.outcome == Outcome.CRASHED)
        skipped = sum(1 for t in tests if t.outcome == Outcome.SKIPPED)
        running = sum(
            1 for t in tests if t.start_time is not None and t.outcome is None
        )
        queued = sum(1 for t in tests if t.start_time is None)

        tests_count = len(tests)
        total_finished = passed + failed + errors + crashed + skipped
        progress_percent = (
            int((total_finished / tests_count) * 100) if tests_count > 0 else 0
        )

        # Calculate percentiles
        durations = []
        memories = []
        peaks = []
        sum_test_durations = 0.0
        for t in tests:
            if t.finish_time and t.start_time:
                d = (t.finish_time - t.start_time).total_seconds()
                durations.append(d)
                sum_test_durations += d
            if t.memory_usage_mb > 0:
                memories.append(t.memory_usage_mb)
            if t.memory_peak_mb > 0:
                peaks.append(t.memory_peak_mb)
        durations.sort()
        memories.sort()
        peaks.sort()

        total_memory_mb = sum(t.memory_usage_mb for t in tests)

        rows = []

        # Sort by nodeid (name) as requested for default view
        def sort_key(t):
            return t.nodeid

        for t in sorted(tests, key=sort_key):
            duration = ""
            duration_val = 0.0
            duration_style = ""
            if t.finish_time and t.start_time:
                d = (t.finish_time - t.start_time).total_seconds()
                duration_val = d
                duration = format_duration(d)
                if durations:
                    rank = bisect.bisect_left(durations, d)
                    pct = rank / (len(durations) - 1) if len(durations) > 1 else 0
                    # 120 (green) -> 0 (red)
                    hue = 120 * (1 - pct)
                    duration_style = f"background-color: hsl({hue:.0f}, 90%, 85%)"
            elif t.start_time:
                duration_val = (datetime.datetime.now() - t.start_time).total_seconds()
                duration = f"{format_duration(duration_val)} (running)"
            else:
                duration = "-"
                duration_val = -1.0  # For sorting purposes, or handle separately

            outcome_class = (
                str(t.outcome).lower()
                if t.outcome
                else ("running" if t.start_time else "queued")
            )
            outcome_text = (
                str(t.outcome)
                if t.outcome
                else ("RUNNING" if t.start_time else "QUEUED")
            )

            # Logs
            log_button = ""
            log_modal = ""
            if t.output:
                log_content = ""
                if "stdout" in t.output and t.output["stdout"]:
                    log_content += f"<h3>STDOUT</h3><pre>{t.output['stdout']}</pre>"
                if "stderr" in t.output and t.output["stderr"]:
                    log_content += f"<h3>STDERR</h3><pre>{t.output['stderr']}</pre>"
                if "error" in t.output and t.output["error"]:
                    log_content += f"<h3>ERROR</h3><pre>{t.output['error']}</pre>"

                if log_content:
                    safe_nodeid = (
                        t.nodeid.replace("/", "_")
                        .replace(".", "_")
                        .replace(":", "_")
                        .replace("[", "_")
                        .replace("]", "_")
                    )
                    modal_id = f"modal_{safe_nodeid}"
                    log_button = f"<button onclick=\"openModal('{modal_id}')\">View Logs</button>"  # noqa: E501
                    log_modal = f"""
                    <div id="{modal_id}" class="modal">
                      <div class="modal-content">
                        <span class="close" onclick="closeModal(\'{modal_id}\')">&times;</span>
                        <h2>Logs for {t.nodeid}</h2>
                        {log_content}
                      </div>
                    </div>
                    """  # noqa: E501

            # Split nodeid
            # Format: path/to/file.py::test_name[param] or path/to/file.py::TestClass::test_method[param]  # noqa: E501
            parts = t.nodeid.split("::")
            file_path = parts[0]

            # Extract parametrization from the last part if present
            params = ""

            # Reconstruct the rest
            rest = parts[1:]

            # Helper to extract params from a string
            def extract_params(s):
                if s.endswith("]") and "[" in s:
                    # Find the last '['
                    idx = s.rfind("[")
                    return s[:idx], s[idx + 1 : -1]
                return s, ""

            class_name = ""
            function_name = ""

            if len(rest) > 0:
                # If there are 2+ parts (Class::Method), the last one is function
                if len(rest) > 1:
                    class_name = "::".join(rest[:-1])
                    function_name, params = extract_params(rest[-1])
                else:
                    # Just function (no class)
                    class_name = ""
                    function_name, params = extract_params(rest[0])

            worker_info = f"Worker PID: {t.pid}" if t.pid else ""
            # We add a data-value attribute for sorting
            duration_cell = f'<td style="{duration_style}" title="{worker_info}" data-value="{duration_val}">{duration}</td>'  # noqa: E501

            # Memory
            memory_val = t.memory_usage_mb
            memory_str = f"{memory_val:.2f} MB" if memory_val > 0 else "-"
            memory_style = ""
            if memories and memory_val > 0:
                rank = bisect.bisect_left(memories, memory_val)
                pct = rank / (len(memories) - 1) if len(memories) > 1 else 0
                hue = 120 * (1 - pct)
                memory_style = f"background-color: hsl({hue:.0f}, 90%, 85%)"

            memory_cell = f'<td style="{memory_style}" data-value="{memory_val}">{memory_str}</td>'

            # Peak Memory
            peak_val = t.memory_peak_mb
            peak_str = f"{peak_val:.2f} MB" if peak_val > 0 else "-"
            peak_style = ""
            if peaks and peak_val > 0:
                rank = bisect.bisect_left(peaks, peak_val)
                pct = rank / (len(peaks) - 1) if len(peaks) > 1 else 0
                hue = 120 * (1 - pct)
                peak_style = f"background-color: hsl({hue:.0f}, 90%, 85%)"

            peak_cell = (
                f'<td style="{peak_style}" data-value="{peak_val}">{peak_str}</td>'
            )

            # Error message cell
            error_msg = t.error_message or ""
            if error_msg:
                # Escape HTML in error message
                error_msg_escaped = (
                    error_msg.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                )
                # Truncate for display if too long
                error_msg_display = (
                    error_msg_escaped[:100] + "..."
                    if len(error_msg_escaped) > 100
                    else error_msg_escaped
                )
                error_cell = f'<td class="error-cell" title="{error_msg_escaped}">{error_msg_display}</td>'
            else:
                error_cell = "<td>-</td>"

            row_class = f"row-{outcome_class}"

            rows.append(f"""
            <tr class="{row_class}">
                <td>{file_path}</td>
                <td>{class_name}</td>
                <td>{function_name}</td>
                <td>{params}</td>
                <td class="{outcome_class}">{outcome_text}</td>
                {duration_cell}
                {memory_cell}
                {peak_cell}
                {error_cell}
                <td>{log_button} {log_modal}</td>
            </tr>
            """)

        try:
            total_duration_sec = (
                datetime.datetime.now() - self.start_time
            ).total_seconds()
            total_duration_str = format_duration(total_duration_sec)

            # Build commit info HTML
            commit_info_html = ""
            if commit_info.hash:
                commit_parts = []
                if commit_info.short_hash:
                    commit_parts.append(
                        f"<strong>Commit:</strong> <code>{commit_info.short_hash}</code>"  # noqa: E501
                    )
                if commit_info.author:
                    commit_parts.append(
                        f"<strong>Author:</strong> {commit_info.author}"
                    )
                if commit_info.time:
                    commit_parts.append(f"<strong>Time:</strong> {commit_info.time}")
                if commit_parts:
                    commit_info_html = "<br>" + " | ".join(commit_parts)
                if commit_info.message:
                    # Escape HTML in message
                    escaped_msg = (
                        commit_info.message.replace("&", "&amp;")
                        .replace("<", "&lt;")
                        .replace(">", "&gt;")
                        .replace('"', "&quot;")
                    )
                    commit_info_html += (
                        f'<br><strong>Message:</strong> <em>"{escaped_msg}"</em>'
                    )

            # Build CI info HTML
            ci_info_html = ""
            if ci_info.is_ci:
                ci_parts = []
                if ci_info.workflow:
                    ci_parts.append(f"Workflow: {ci_info.workflow}")
                if ci_info.job:
                    ci_parts.append(f"Job: {ci_info.job}")
                if ci_info.run_id:
                    ci_parts.append(f"Run ID: {ci_info.run_id}")
                if ci_info.runner_name:
                    ci_parts.append(f"Runner: {ci_info.runner_name}")
                if ci_info.runner_os:
                    ci_parts.append(f"({ci_info.runner_os})")
                if ci_parts:
                    ci_info_html = "<strong>CI:</strong> " + " | ".join(ci_parts)

            html = HTML_TEMPLATE.format(
                status="Running" if running > 0 or queued > 0 else "Finished",
                workers_active=workers_active,
                workers_total=WORKER_COUNT,
                passed=passed,
                failed=failed,
                errors=errors,
                crashed=crashed,
                skipped=skipped,
                running=running,
                remaining=queued,
                progress_percent=progress_percent,
                rows="\n".join(rows),
                timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                total_duration=total_duration_str,
                total_summed_duration=format_duration(sum_test_durations),
                total_memory=f"{total_memory_mb:.2f} MB",
                refresh_meta="",
                commit_info_html=commit_info_html,
                ci_info_html=ci_info_html,
            )
        except Exception as e:
            print(f"Failed to format HTML report: {e}")
            return

        try:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                f.write(html)
        except Exception as e:
            print(f"Failed to write HTML report: {e}")

    def generate_json_report(self, output_path: str = "artifacts/test-report.json"):
        with self._lock:
            tests = list(self._tests.values())
            # For workers, we might want the total unique workers seen
            workers_used = len(self._active_pids) + len(self._exited_pids)
            # Actually, `_active_pids` are current, `_exited_pids` are gone.
            # But we might want the set of ALL pids seen.
            # We don't strictly track "all seen pids" separately, but we can infer it
            # or just use active + exited.
            # Let's count unique PIDs assigned to tests if we want accuracy or just
            # use current active + exited.

            # Count outcomes
            passed = sum(1 for t in tests if t.outcome == Outcome.PASSED)
            failed = sum(1 for t in tests if t.outcome == Outcome.FAILED)
            errors = sum(1 for t in tests if t.outcome == Outcome.ERROR)
            crashed = sum(1 for t in tests if t.outcome == Outcome.CRASHED)
            skipped = sum(1 for t in tests if t.outcome == Outcome.SKIPPED)

            total_duration = (datetime.datetime.now() - self.start_time).total_seconds()

            test_results = []

            sum_test_durations = 0.0

            def extract_params(s):
                if s.endswith("]") and "[" in s:
                    idx = s.rfind("[")
                    return s[:idx], s[idx + 1 : -1]
                return s, ""

            for t in tests:
                # Calculate duration
                duration = 0.0
                if t.finish_time and t.start_time:
                    duration = (t.finish_time - t.start_time).total_seconds()
                sum_test_durations += duration

                # Split nodeid logic (reused from HTML)
                parts = t.nodeid.split("::")
                file_path = parts[0]
                rest = parts[1:]

                class_name = ""
                function_name = ""

                if len(rest) > 0:
                    if len(rest) > 1:
                        class_name = "::".join(rest[:-1])
                        function_name, _ = extract_params(rest[-1])
                    else:
                        class_name = ""
                        function_name, _ = extract_params(rest[0])

                test_results.append(
                    {
                        "file": file_path,
                        "class": class_name,
                        "function": function_name,
                        "outcome": str(t.outcome) if t.outcome else "QUEUED",
                        "duration": duration,
                        "error_message": t.error_message,
                        "memory_usage_mb": t.memory_usage_mb,
                        "memory_peak_mb": t.memory_peak_mb,
                        "worker_pid": t.pid,
                    }
                )

            # Build commit info dict (only include non-None values)
            commit_dict = {}
            if commit_info.hash:
                commit_dict["hash"] = commit_info.hash
            if commit_info.short_hash:
                commit_dict["short_hash"] = commit_info.short_hash
            if commit_info.author:
                commit_dict["author"] = commit_info.author
            if commit_info.message:
                commit_dict["message"] = commit_info.message
            if commit_info.time:
                commit_dict["time"] = commit_info.time

            # Build CI info dict (only include if running in CI)
            ci_dict = {}
            if ci_info.is_ci:
                ci_dict["is_ci"] = True
                if ci_info.run_id:
                    ci_dict["run_id"] = ci_info.run_id
                if ci_info.run_number:
                    ci_dict["run_number"] = ci_info.run_number
                if ci_info.workflow:
                    ci_dict["workflow"] = ci_info.workflow
                if ci_info.job:
                    ci_dict["job"] = ci_info.job
                if ci_info.runner_name:
                    ci_dict["runner_name"] = ci_info.runner_name
                if ci_info.runner_os:
                    ci_dict["runner_os"] = ci_info.runner_os
                if ci_info.actor:
                    ci_dict["actor"] = ci_info.actor
                if ci_info.repository:
                    ci_dict["repository"] = ci_info.repository
                if ci_info.ref:
                    ci_dict["ref"] = ci_info.ref

            report = {
                "summary": {
                    "passed": passed,
                    "failed": failed,
                    "errors": errors,
                    "crashed": crashed,
                    "skipped": skipped,
                    "total": len(tests),
                    "total_duration": total_duration,
                    "total_summed_duration": sum_test_durations,
                    "total_memory_mb": sum(t.memory_usage_mb for t in tests),
                    "workers_used": workers_used,
                },
                "commit": commit_dict if commit_dict else None,
                "ci": ci_dict if ci_dict else None,
                "tests": test_results,
            }

            try:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "w") as f:
                    json.dump(report, f, indent=2)
            except Exception as e:
                print(f"Failed to write JSON report: {e}")


# IMPORTANT: TestAggregator instantiation moved to main()
# # Global aggregator instance (initialized in main)
aggregator: TestAggregator | None = None
app = FastAPI()


@app.post("/claim")
async def claim(request: ClaimRequest):
    try:
        nodeid = test_queue.get_nowait()
        return ClaimResponse(nodeid=nodeid)
    except queue.Empty:
        return ClaimResponse(nodeid=None)


@app.post("/event")
async def event(request: EventRequest):
    if aggregator:
        aggregator.handle_event(request)
    return {"status": "ok"}


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
            if GENERATE_PERIODIC_HTML:
                self._aggregator.generate_html_report()
            time.sleep(self._interval)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)


def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def collect_tests(pytest_args):
    """Collects tests using pytest --collect-only"""
    # Filter out empty strings if any
    pytest_args = [arg for arg in pytest_args if arg]

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "--collect-only",
        "-q",
        "--no-header",
        "--no-summary",
    ] + pytest_args
    _print(f"Collecting tests: {' '.join(cmd)}")

    # Capture output
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        _print("Error collecting tests:")
        print(result.stderr)
        sys.exit(1)

    tests = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if line and not line.startswith("no tests ran") and not line.startswith("="):
            # Check if it looks like a nodeid (simple heuristic)
            if "::" in line or line.endswith(".py"):
                tests.append(line)

    return tests


def start_server(port):
    config = uvicorn.Config(
        app, host="127.0.0.1", port=port, log_level="error", access_log=False
    )
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()

    # Wait for server to start? Uvicorn doesn't have a simple event.
    # We'll just wait a bit.
    time.sleep(1.0)
    return t


def get_log_file(worker_id: int) -> Path:
    return LOG_DIR / f"worker-{worker_id}.log"


LOG_DIR = Path("artifacts/logs")


def main():
    global tests_total, commit_info, ci_info, workers

    # Gather commit and CI info at startup (robust to failures)
    commit_info = get_commit_info()
    ci_info = get_ci_info()

    if commit_info.short_hash:
        _print(f"Commit: {commit_info.short_hash} by {commit_info.author or 'unknown'}")
    if ci_info.is_ci:
        _print(f"CI: Run {ci_info.run_id} on {ci_info.runner_name or 'unknown runner'}")

    pytest_args = sys.argv[1:]

    # 1. Collect tests
    tests = collect_tests(pytest_args)
    tests_total = len(tests)
    _print(f"Collected {tests_total} tests")

    if tests_total == 0:
        _print("No tests found.")
        sys.exit(0)

    # Initialize aggregator with all tests (so we know what's queued)
    global aggregator
    aggregator = TestAggregator(tests)

    for t in tests:
        test_queue.put(t)

    # 2. Start Orchestrator
    port = get_free_port()
    url = f"http://127.0.0.1:{port}"
    _print(f"Starting orchestrator at {url}")
    start_server(port)

    # 3. Start Workers
    worker_script = Path(__file__).parent / "worker.py"

    env = os.environ.copy()
    env["FBRK_TEST_ORCHESTRATOR_URL"] = url
    # Ensure workers can find test modules
    env["PYTHONPATH"] = os.getcwd()

    worker_count = min(WORKER_COUNT, tests_total)

    _print(f"Spawning {worker_count} workers...")

    # Create logs directory
    try:
        shutil.rmtree(LOG_DIR, ignore_errors=True)
    except Exception:
        pass
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    worker_files = []

    def start_worker():
        i = max(workers.keys()) + 1 if workers else 0
        log_path = get_log_file(i)
        f = open(log_path, "w")
        worker_files.append(f)
        p = subprocess.Popen(
            [sys.executable, str(worker_script)], env=env, stdout=f, stderr=f
        )
        workers[i] = p

    for _ in range(worker_count):
        start_worker()

    # 4. Monitor
    timer = ReportTimer(aggregator, REPORT_INTERVAL_SECONDS)
    timer.start()

    try:
        while True:
            # Check if workers are alive
            for i, p in list(workers.items()):
                if p.poll() is None:
                    continue
                # Worker died.
                # Handle crash in aggregator
                aggregator.handle_worker_crash(p.pid)

                # If queue is not empty, restart it.
                if test_queue.empty():
                    continue

                # Close old file
                try:
                    worker_files[i].close()
                except Exception:
                    pass
                del workers[i]

                # respawn worker
                start_worker()

            all_workers_exited = all(p.poll() is not None for p in workers.values())
            if all_workers_exited and test_queue.empty():
                _print("All workers exited and queue is empty.")
                break

            # If queue is empty, ensure workers are told to exit if they are stuck?
            # They should exit naturally when they get None from claim.
            # But let's check if they are idle for too long?
            # Actually, workers exit when they receive nodeid=None from /claim.
            # /claim returns None when queue is empty.
            # So they should exit naturally.

            time.sleep(1)

    except KeyboardInterrupt:
        _print("Interrupted. Stopping workers...")
        for p in workers.values():
            p.terminate()

    finally:
        timer.stop()
        # Kill remaining workers
        for p in workers.values():
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    p.kill()

        # Close files
        for f in worker_files:
            try:
                f.close()
            except Exception:
                pass

    _print("-" * 80)
    _print(f"Final: {aggregator.get_report()}")

    total_duration = (datetime.datetime.now() - aggregator.start_time).total_seconds()
    _print(f"Total time: {format_duration(total_duration)}")

    aggregator.generate_html_report()
    aggregator.generate_json_report()

    if aggregator.has_failures():
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
