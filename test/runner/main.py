#!/usr/bin/env python3
"""
CI test orchestrator using FastAPI and custom workers.

Replaces pytest-xdist with a central orchestrator that distributes tests
to persistent worker processes via HTTP.
"""

import bisect
import datetime
import html
import json
import os
import queue
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from enum import StrEnum, auto
from pathlib import Path
from typing import Any, Optional, cast

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from jinja2 import Template

# Ensure we can import from test package
sys.path.insert(0, os.getcwd())

from test.runner.common import (
    ClaimRequest,
    ClaimResponse,
    EventRequest,
    EventType,
    Outcome,
    Report,
)


class CompareStatus(StrEnum):
    """Status comparing local test to remote baseline."""

    SAME = auto()  # Outcome unchanged
    REGRESSION = auto()  # Was passing, now failing
    FIXED = auto()  # Was failing, now passing
    NEW = auto()  # Test didn't exist in baseline
    REMOVED = auto()  # Test was removed (only in baseline)


@dataclass
class RemoteBaseline:
    """Holds remote test results for comparison."""

    tests: dict[str, str] = field(default_factory=dict)  # nodeid -> outcome
    commit_hash: Optional[str] = None
    branch: Optional[str] = None
    loaded: bool = False
    error: Optional[str] = None


def get_current_branch() -> Optional[str]:
    """Get the current git branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def get_remote_tracking_branch() -> Optional[str]:
    """Get the remote tracking branch (e.g., origin/main)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def fetch_remote_report(commit_hash: Optional[str] = None) -> RemoteBaseline:
    """
    Fetch a test report from GitHub Actions.

    If commit_hash is provided, fetches the report for that specific commit.
    Otherwise, fetches the most recent completed run for the current branch
    (falling back to 'main' if no runs exist for the current branch).

    Uses the `gh` CLI to download artifacts from workflow runs.
    """
    baseline = RemoteBaseline()

    # Check gh CLI is available and we're in a valid repo
    try:
        result = subprocess.run(
            ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            baseline.error = "Failed to get repository info (is gh CLI installed?)"
            return baseline
        # Successfully got repo info, gh CLI is working
    except FileNotFoundError:
        baseline.error = "gh CLI not found - install with: brew install gh"
        return baseline
    except Exception as e:
        baseline.error = f"Error getting repo info: {e}"
        return baseline

    run_id = None

    # If a specific commit hash is provided, find the workflow run for it
    if commit_hash:
        # Resolve short hash to full hash using git
        try:
            result = subprocess.run(
                ["git", "rev-parse", commit_hash],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                full_hash = result.stdout.strip()
            else:
                full_hash = commit_hash  # Use as-is if git can't resolve
        except Exception:
            full_hash = commit_hash

        try:
            result = subprocess.run(
                [
                    "gh",
                    "run",
                    "list",
                    "--commit",
                    full_hash,
                    "--workflow",
                    "pytest.yml",
                    "--status",
                    "completed",
                    "--limit",
                    "1",
                    "--json",
                    "databaseId,headSha,headBranch",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                runs = json.loads(result.stdout)
                if runs:
                    run_id = runs[0]["databaseId"]
                    baseline.commit_hash = runs[0]["headSha"][:8]
                    baseline.branch = runs[0].get("headBranch", "unknown")
                else:
                    baseline.error = f"No workflow run found for commit '{commit_hash}'"
                    return baseline
            else:
                baseline.error = f"Failed to find run for commit: {result.stderr}"
                return baseline
        except Exception as e:
            baseline.error = f"Error finding workflow run for commit: {e}"
            return baseline
    else:
        # Auto-detect: find the most recent completed workflow run for this branch
        # Fall back to 'main' if current branch has no runs.
        branch = get_current_branch()
        if not branch:
            baseline.error = "Could not determine current branch"
            return baseline
        baseline.branch = branch

        branches_to_try = [branch]
        if branch != "main":
            branches_to_try.append("main")

        for try_branch in branches_to_try:
            try:
                result = subprocess.run(
                    [
                        "gh",
                        "run",
                        "list",
                        "--branch",
                        try_branch,
                        "--workflow",
                        "pytest.yml",
                        "--status",
                        "completed",
                        "--limit",
                        "1",
                        "--json",
                        "databaseId,headSha,conclusion",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode != 0:
                    continue

                runs = json.loads(result.stdout)
                if runs:
                    run_id = runs[0]["databaseId"]
                    baseline.commit_hash = runs[0]["headSha"][:8]
                    baseline.branch = try_branch
                    break
            except Exception:
                continue

        if run_id is None:
            baseline.error = (
                f"No completed workflow runs found for '{branch}' or 'main'"
            )
            return baseline

    # Download the test-report.json artifact
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            result = subprocess.run(
                [
                    "gh",
                    "run",
                    "download",
                    str(run_id),
                    "--name",
                    "test-report.json",
                    "--dir",
                    tmpdir,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                baseline.error = f"Failed to download artifact: {result.stderr}"
                return baseline

            # Look for test-report.json in the downloaded files
            report_path = Path(tmpdir) / "test-report.json"
            if not report_path.exists():
                # Check if it's in a subdirectory
                for p in Path(tmpdir).rglob("test-report.json"):
                    report_path = p
                    break

            if not report_path.exists():
                baseline.error = "test-report.json not found in artifact"
                return baseline

            # Parse the report
            report = Report.from_json(report_path.read_text())
            baseline.tests = {t.fullnodeid: t.outcome for t in report.tests}
            baseline.loaded = True

        except Exception as e:
            baseline.error = f"Error downloading/parsing artifact: {e}"
            return baseline

    return baseline


# Global baseline (fetched once at startup)
remote_baseline: RemoteBaseline = RemoteBaseline()


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
    WORKER_COUNT = os.cpu_count() or 1
elif WORKER_COUNT < 0:
    WORKER_COUNT = max(((os.cpu_count() or 1) * -WORKER_COUNT) // 2, 1)
# Generate HTML report
GENERATE_HTML = os.getenv("FBRK_TEST_GENERATE_HTML", "1") == "1"
GENERATE_PERIODIC_HTML = os.getenv("FBRK_TEST_PERIODIC_HTML", "1") == "1"

# Global state
test_queue = queue.Queue[str]()
tests_total = 0
workers: dict[int, subprocess.Popen[bytes]] = {}

# Read HTML template from file
HTML_TEMPLATE: Template = Template(
    (Path(__file__).parent / "report.html").read_text(encoding="utf-8"),
    variable_start_string="[[",
    variable_end_string="]]",
)


# Helper to extract params from a string
def extract_params(s: str) -> tuple[str, str]:
    if s.endswith("]") and "[" in s:
        # Find the last '['
        idx = s.rfind("[")
        return s[:idx], s[idx + 1 : -1]
    return s, ""


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

    __test__ = False

    def __init__(self, all_tests: list[str], baseline: RemoteBaseline):
        self._baseline = baseline
        self._tests: dict[str, TestState] = {}
        for t in all_tests:
            state = TestState(nodeid=t, pid=None, start_time=None)
            # Set baseline info if available
            if baseline.loaded:
                if t in baseline.tests:
                    state.baseline_outcome = baseline.tests[t]
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
        self.start_time = datetime.datetime.now()

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
                    test.baseline_outcome = baseline.tests[nodeid]
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
        queued = sum(1 for t in tests if t.start_time is None and t.outcome is None)

        # Comparison counts
        regressions = sum(
            1 for t in tests if t.compare_status == CompareStatus.REGRESSION
        )
        fixed = sum(1 for t in tests if t.compare_status == CompareStatus.FIXED)
        new_tests = sum(1 for t in tests if t.compare_status == CompareStatus.NEW)

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
                    # Catppuccin Mocha: green (#a6e3a1) -> red (#f38ba8)
                    # Interpolate RGB values
                    r = int(166 + (243 - 166) * pct)
                    g = int(227 + (139 - 227) * pct)
                    b = int(161 + (168 - 161) * pct)
                    duration_style = f"background-color: rgba({r}, {g}, {b}, 0.25)"
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
                    stdout = html.escape(t.output["stdout"])
                    log_content += (
                        f'<div class="log-section"><h3>STDOUT</h3>'
                        f"<pre>{stdout}</pre></div>"
                    )
                if "stderr" in t.output and t.output["stderr"]:
                    stderr = html.escape(t.output["stderr"])
                    log_content += (
                        f'<div class="log-section"><h3>STDERR</h3>'
                        f"<pre>{stderr}</pre></div>"
                    )
                if "error" in t.output and t.output["error"]:
                    error = html.escape(t.output["error"])
                    log_content += (
                        f'<div class="log-section"><h3>ERROR</h3>'
                        f"<pre>{error}</pre></div>"
                    )

                if log_content:
                    safe_nodeid = html.escape(t.nodeid)
                    modal_id = f"modal_{safe_nodeid}"
                    log_button = f"<button onclick=\"openModal('{modal_id}')\">View Logs</button>"  # noqa: E501
                    log_modal = f"""
                    <div id="{modal_id}" class="modal">
                      <div class="modal-content">
                        <div class="modal-header">
                          <h2>Logs for {t.nodeid}</h2>
                          <div class="modal-buttons">
                            <button class="copy-btn" onclick="copyLogs('{modal_id}')">Copy</button>
                            <button class="close-btn" onclick="closeModal('{modal_id}')">&times;</button>
                          </div>
                        </div>
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
                # Catppuccin Mocha: green (#a6e3a1) -> red (#f38ba8)
                r = int(166 + (243 - 166) * pct)
                g = int(227 + (139 - 227) * pct)
                b = int(161 + (168 - 161) * pct)
                memory_style = f"background-color: rgba({r}, {g}, {b}, 0.25)"

            memory_cell = (
                f'<td style="{memory_style}" data-value="{memory_val}">'
                f"{memory_str}</td>"
            )

            # Peak Memory
            peak_val = t.memory_peak_mb
            peak_str = f"{peak_val:.2f} MB" if peak_val > 0 else "-"
            peak_style = ""
            if peaks and peak_val > 0:
                rank = bisect.bisect_left(peaks, peak_val)
                pct = rank / (len(peaks) - 1) if len(peaks) > 1 else 0
                # Catppuccin Mocha: green (#a6e3a1) -> red (#f38ba8)
                r = int(166 + (243 - 166) * pct)
                g = int(227 + (139 - 227) * pct)
                b = int(161 + (168 - 161) * pct)
                peak_style = f"background-color: rgba({r}, {g}, {b}, 0.25)"

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
                error_cell = (
                    f'<td class="error-cell" title="{error_msg_escaped}">'
                    f"{error_msg_display}</td>"
                )
            else:
                error_cell = "<td>-</td>"

            row_class = f"row-{outcome_class}"

            # Comparison status cell
            compare_cell = ""
            if self._baseline.loaded:
                cmp = t.compare_status
                if cmp == CompareStatus.REGRESSION:
                    compare_cell = '<td class="compare-regression">regression</td>'
                    row_class += " row-regression"
                elif cmp == CompareStatus.FIXED:
                    compare_cell = '<td class="compare-fixed">fixed</td>'
                elif cmp == CompareStatus.NEW:
                    compare_cell = '<td class="compare-new">new</td>'
                elif cmp == CompareStatus.SAME:
                    compare_cell = '<td class="compare-same">-</td>'
                else:
                    compare_cell = "<td>-</td>"
            else:
                compare_cell = '<td class="compare-na">-</td>'

            rows.append(f"""
            <tr class="{row_class}">
                <td>{file_path}</td>
                <td>{class_name}</td>
                <td>{function_name}</td>
                <td>{params}</td>
                <td class="{outcome_class}">{outcome_text}</td>
                {compare_cell}
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

            # Build baseline info HTML
            baseline_info_html = ""
            if self._baseline.loaded:
                baseline_info_html = (
                    f"<br><strong>Baseline:</strong> "
                    f"<code>{self._baseline.commit_hash}</code> "
                    f"on <code>{self._baseline.branch}</code> "
                    f"({len(self._baseline.tests)} tests)"
                )
            elif self._baseline.error:
                baseline_info_html = (
                    f'<br><span class="baseline-error">'
                    f"<strong>Baseline:</strong> {self._baseline.error}</span>"
                )

            finishing_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            html_ = HTML_TEMPLATE.render(
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
                regressions=regressions,
                fixed=fixed,
                new_tests=new_tests,
                progress_percent=progress_percent,
                rows="\n".join(rows),
                timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                finishing_time=finishing_time,
                total_duration=total_duration_str,
                total_summed_duration=format_duration(sum_test_durations),
                total_memory=f"{total_memory_mb:.2f} MB",
                refresh_meta="",
                commit_info_html=commit_info_html,
                ci_info_html=ci_info_html,
                baseline_info_html=baseline_info_html,
            )
        except Exception as e:
            print(f"Failed to format HTML report: {e}")
            return

        try:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                f.write(html_)
        except Exception as e:
            print(f"Failed to write HTML report: {e}")

    def generate_json_report(self, output_path: str = "artifacts/test-report.json"):
        with self._lock:
            tests = list(self._tests.values())
            workers_used = len(self._active_pids) + len(self._exited_pids)

            # Count outcomes
            passed = sum(1 for t in tests if t.outcome == Outcome.PASSED)
            failed = sum(1 for t in tests if t.outcome == Outcome.FAILED)
            errors = sum(1 for t in tests if t.outcome == Outcome.ERROR)
            crashed = sum(1 for t in tests if t.outcome == Outcome.CRASHED)
            skipped = sum(1 for t in tests if t.outcome == Outcome.SKIPPED)

            total_duration = (datetime.datetime.now() - self.start_time).total_seconds()

            test_results: list[Report.Test] = []
            sum_test_durations = 0.0

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
                params = ""

                if len(rest) > 0:
                    if len(rest) > 1:
                        class_name = "::".join(rest[:-1])
                        function_name, params = extract_params(rest[-1])
                    else:
                        class_name = ""
                        function_name, params = extract_params(rest[0])

                test_results.append(
                    Report.Test(
                        file=file_path,
                        class_=class_name,
                        function=function_name,
                        outcome=str(t.outcome) if t.outcome else "QUEUED",
                        duration=duration,
                        error_message=t.error_message,
                        memory_usage_mb=t.memory_usage_mb,
                        memory_peak_mb=t.memory_peak_mb,
                        worker_pid=t.pid,
                        params=params,
                        fullnodeid=t.nodeid,
                    )
                )

            # Build commit info (only if we have any data)
            report_commit = None
            if commit_info.hash:
                report_commit = Report.Commit(
                    hash=commit_info.hash,
                    short_hash=commit_info.short_hash,
                    author=commit_info.author,
                    message=commit_info.message,
                    time=commit_info.time,
                )

            # Build CI info (only if running in CI)
            report_ci = None
            if ci_info.is_ci:
                report_ci = Report.Ci(
                    is_ci=True,
                    run_id=ci_info.run_id,
                    run_number=ci_info.run_number,
                    workflow=ci_info.workflow,
                    job=ci_info.job,
                    runner_name=ci_info.runner_name,
                    runner_os=ci_info.runner_os,
                    actor=ci_info.actor,
                    repository=ci_info.repository,
                    ref=ci_info.ref,
                )

            report = Report(
                summary=Report.Summary(
                    passed=passed,
                    failed=failed,
                    errors=errors,
                    crashed=crashed,
                    skipped=skipped,
                    total=len(tests),
                    total_duration=total_duration,
                    total_summed_duration=sum_test_durations,
                    total_memory_mb=sum(t.memory_usage_mb for t in tests),
                    workers_used=workers_used,
                ),
                commit=report_commit,
                ci=report_ci,
                tests=test_results,
            )

            try:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "w") as f:
                    f.write(report.to_json(indent=2))
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
        if aggregator and nodeid is not None:
            aggregator.handle_claim(request.pid, nodeid)
        return ClaimResponse(nodeid=nodeid)
    except queue.Empty:
        return ClaimResponse(nodeid=None)


@app.post("/event")
async def event(request: EventRequest):
    if aggregator:
        aggregator.handle_event(request)
    return {"status": "ok"}


@app.get("/")
async def report_redirect():
    """Redirect root to the test report."""
    return HTMLResponse(
        content='<html><head><meta http-equiv="refresh" content="0; url=/report">'
        "</head></html>"
    )


@app.get("/report")
async def serve_report():
    """Serve the test report HTML file."""
    report_path = Path("artifacts/test-report.html")
    if report_path.exists():
        # Read file into memory to avoid race condition with regeneration
        try:
            content = report_path.read_text(encoding="utf-8")
            return HTMLResponse(content=content)
        except Exception:
            pass
    return HTMLResponse(
        content="<html><body><h1>Report not yet generated...</h1>"
        "<p>Refresh in a few seconds.</p>"
        "<script>setTimeout(() => location.reload(), 2000);</script>"
        "</body></html>"
    )


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


def collect_tests(pytest_args: list[str]) -> tuple[list[str], dict[str, str]]:
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
        # "--no-summary",
        # Ensure co-located tests in `src/` are imported by package name, not by path.
        "-p",
        "atopile.pytest_import_by_name",
    ] + pytest_args
    _print(f"Collecting tests: {' '.join(cmd)}")

    # Capture output
    env = os.environ.copy()
    # Ensure our in-repo pytest plugins (`test.runner.*`) are importable in the process.
    # (Workers already set PYTHONPATH similarly.)
    env["PYTHONPATH"] = os.getcwd()
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    split = result.stdout.split("\n\n", maxsplit=1)
    stdout, summary = split if len(split) == 2 else (split[0], "")
    errors_clean = dict[str, str]()
    if result.returncode != 0:
        _print("Error collecting tests:")
        if "ERRORS " not in summary:
            if "ERRORS " in stdout:
                summary = stdout
            else:
                _print(stdout)
                _print(summary)
                sys.exit(1)
        errors = [
            e.strip().strip("_").strip().split("____\n")
            for e in (
                summary.split("ERRORS ")[1]
                .strip()
                .lstrip("=")
                .split(" short test summary info")[0]
                .rstrip("=")
            ).split(" ERROR collecting ")[1:]
        ]
        errors_clean = {e[0].strip("_").strip(): e[1] for e in errors}

    tests = list[str]()
    for line in stdout.splitlines():
        line = line.strip()
        if line and not line.startswith("no tests ran") and not line.startswith("="):
            # Check if it looks like a nodeid (simple heuristic)
            if "::" in line or line.endswith(".py"):
                tests.append(line)

    return tests, errors_clean


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


def main(
    args: list[str] | None = None,
    baseline_commit: str | None = None,
    open_browser: bool = False,
):
    global tests_total, commit_info, ci_info, workers

    # Gather commit and CI info at startup (robust to failures)
    commit_info = get_commit_info()
    ci_info = get_ci_info()

    if commit_info.short_hash:
        _print(f"Commit: {commit_info.short_hash} by {commit_info.author or 'unknown'}")
    if ci_info.is_ci:
        _print(f"CI: Run {ci_info.run_id} on {ci_info.runner_name or 'unknown runner'}")

    pytest_args = args if args is not None else sys.argv[1:]

    # 1. Collect tests
    tests, errors = collect_tests(pytest_args)
    tests_total = len(tests)
    _print(f"Collected {tests_total} tests")

    if tests_total == 0 and not errors:
        _print("No tests found.")
        sys.exit(0)

    # Start fetching baseline from GitHub in background (non-blocking)
    global remote_baseline
    baseline_fetch_complete = threading.Event()

    def fetch_baseline_background():
        global remote_baseline
        try:
            remote_baseline = fetch_remote_report(commit_hash=baseline_commit)
            if remote_baseline.loaded:
                _print(
                    f"Baseline loaded: {remote_baseline.commit_hash} on "
                    f"{remote_baseline.branch} ({len(remote_baseline.tests)} tests)"
                )
                # Update aggregator with loaded baseline
                if aggregator:
                    aggregator.set_baseline(remote_baseline)
            elif remote_baseline.error:
                _print(f"Baseline: {remote_baseline.error}")
        except Exception as e:
            _print(f"Baseline fetch failed: {e}")
            remote_baseline = RemoteBaseline(error=str(e))
        finally:
            baseline_fetch_complete.set()

    baseline_thread = threading.Thread(target=fetch_baseline_background, daemon=True)
    baseline_thread.start()
    if baseline_commit:
        _print(f"Fetching baseline for commit {baseline_commit} (background)...")
    else:
        _print("Fetching baseline from GitHub (background)...")

    # Initialize aggregator with empty baseline (will be updated when fetch completes)
    global aggregator
    aggregator = TestAggregator(tests, RemoteBaseline())

    for error_key, error_value in errors.items():
        aggregator._tests[error_key] = TestState(
            nodeid=error_key,
            pid=None,
            start_time=None,
            output={"stderr": error_value},
            outcome=Outcome.ERROR,
            error_message=error_value.splitlines()[-1].strip(),
        )

    for t in tests:
        test_queue.put(t)

    # 2. Start Orchestrator
    port = get_free_port()
    url = f"http://127.0.0.1:{port}"
    _print(f"Starting orchestrator at {url}")
    start_server(port)

    # Print clickable link to the report (ANSI hyperlink format for terminals)
    report_url = f"{url}/report"
    # Use OSC 8 hyperlink escape sequence for clickable links in modern terminals
    clickable_link = f"\033]8;;{report_url}\033\\📊 {report_url}\033]8;;\033\\"
    _print(f"Live report: {clickable_link}")

    # Open browser if requested
    if open_browser:
        import webbrowser

        webbrowser.open(report_url)

    # 3. Start Workers
    worker_script = Path(__file__).parent / "worker.py"

    env = os.environ.copy()
    env["FBRK_TEST_ORCHESTRATOR_URL"] = url
    # Ensure workers can find test modules
    env["PYTHONPATH"] = os.getcwd()
    # no need to keep on recompiling zig
    # already done during discovery latest
    env["FBRK_ZIG_NORECOMPILE"] = "1"

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

                # Close old file
                try:
                    worker_files[i].close()
                except Exception:
                    pass
                del workers[i]

                # respawn worker if there's still work to do
                if not test_queue.empty() or (aggregator.pending_count() > 0):
                    start_worker()

            # If the queue is empty but we still have pending tests, it means
            # some tests were claimed but we never received START/FINISH for them
            # (or a worker died before we noticed). Requeue them and keep going.
            if test_queue.empty():
                pending_unstarted = aggregator.unstarted_pending_nodeids()
                if pending_unstarted and aggregator.pending_count() > 0:
                    _print(
                        f"WARNING: Found {len(pending_unstarted)} pending unstarted tests with empty queue; requeueing."  # noqa: E501
                    )
                    for nodeid in pending_unstarted:
                        test_queue.put(nodeid)

            # Ensure we keep enough workers around while work remains.
            pending = aggregator.pending_count()
            desired_workers = min(worker_count, pending) if pending > 0 else 0
            while len(workers) < desired_workers and not test_queue.empty():
                start_worker()

            if aggregator.pending_count() == 0 and test_queue.empty():
                _print("All tests finished and queue is empty.")
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

    # Print link to the static report file
    report_path = Path("artifacts/test-report.html").resolve()
    file_url = f"file://{report_path}"
    clickable_file = f"\033]8;;{file_url}\033\\📄 {report_path}\033]8;;\033\\"
    _print(f"Report saved: {clickable_file}")

    if aggregator.has_failures():
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
