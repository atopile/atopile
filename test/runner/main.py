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
import platform
import queue
import re
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
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from jinja2 import Template
from rich.console import Console
from rich.text import Text

# Ensure we can import from test package
sys.path.insert(0, os.getcwd())

from test.runner.common import (
    ClaimRequest,
    ClaimResponse,
    EventRequest,
    EventType,
    Outcome,
)


def ansi_to_html(text: str) -> str:
    """Convert ANSI escape codes to HTML with inline styles."""
    import io

    # Use Rich to parse ANSI and export to HTML
    console = Console(file=io.StringIO(), force_terminal=True, record=True)
    rich_text = Text.from_ansi(text)
    console.print(rich_text, soft_wrap=True)
    # Export with inline styles, extract just the code content
    html_output = console.export_html(inline_styles=True, code_format="{code}")
    return html_output


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

    tests: dict[str, dict[str, Any]] = field(default_factory=dict)  # nodeid -> info
    commit_hash: Optional[str] = None
    commit_hash_full: Optional[str] = None
    commit_author: Optional[str] = None
    commit_message: Optional[str] = None
    commit_time: Optional[str] = None
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
            report_data = json.loads(report_path.read_text())
            tests = {}
            for t in report_data.get("tests", []):
                nodeid = t.get("nodeid") or t.get("fullnodeid")
                outcome = t.get("outcome") or t.get("status")
                if not nodeid or not outcome:
                    continue
                tests[nodeid] = {
                    "outcome": str(outcome).lower(),
                    "duration_s": t.get("duration_s") or t.get("duration"),
                    "memory_usage_mb": t.get("memory_usage_mb", 0.0),
                    "memory_peak_mb": t.get("memory_peak_mb", 0.0),
                }
            baseline.tests = tests
            baseline.loaded = True

            commit_info_data = report_data.get("commit") or {}
            if not baseline.commit_hash and commit_info_data.get("short_hash"):
                baseline.commit_hash = commit_info_data.get("short_hash")
            if commit_info_data.get("hash"):
                baseline.commit_hash_full = commit_info_data.get("hash")
            elif baseline.commit_hash:
                baseline.commit_hash_full = baseline.commit_hash
            baseline.commit_author = commit_info_data.get("author")
            baseline.commit_message = commit_info_data.get("message")
            baseline.commit_time = commit_info_data.get("time")
            if not baseline.branch and report_data.get("baseline", {}).get("branch"):
                baseline.branch = report_data.get("baseline", {}).get("branch")

        except Exception as e:
            baseline.error = f"Error downloading/parsing artifact: {e}"
            return baseline

    return baseline


def list_local_baselines() -> list[dict[str, Any]]:
    """List all available local baselines."""
    if not BASELINES_INDEX.exists():
        return []
    try:
        index_data = json.loads(BASELINES_INDEX.read_text())
        return index_data.get("baselines", [])
    except Exception:
        return []


def load_local_baseline(name: str) -> RemoteBaseline:
    """
    Load a local baseline by name.
    Returns a RemoteBaseline object for compatibility with existing comparison logic.
    """
    baseline = RemoteBaseline()

    baseline_file = BASELINES_DIR / f"{name}.json"
    if not baseline_file.exists():
        baseline.error = f"Local baseline '{name}' not found"
        return baseline

    try:
        data = json.loads(baseline_file.read_text())
        tests = {}
        for t in data.get("tests", []):
            nodeid = t.get("nodeid") or t.get("fullnodeid")
            outcome = t.get("outcome") or t.get("status")
            if not nodeid or not outcome:
                continue
            tests[nodeid] = {
                "outcome": str(outcome).lower(),
                "duration_s": t.get("duration_s") or t.get("duration"),
                "memory_usage_mb": t.get("memory_usage_mb", 0.0),
                "memory_peak_mb": t.get("memory_peak_mb", 0.0),
            }
        baseline.tests = tests
        baseline.loaded = True

        # Extract metadata from the baseline file
        commit_data = data.get("commit") or {}
        baseline.commit_hash = commit_data.get("short_hash") or name
        baseline.commit_hash_full = commit_data.get("hash")
        baseline.commit_author = commit_data.get("author")
        baseline.commit_message = commit_data.get("message")
        baseline.commit_time = commit_data.get("time")
        baseline.branch = data.get("run", {}).get("git", {}).get("branch")

    except Exception as e:
        baseline.error = f"Error loading local baseline '{name}': {e}"
        return baseline

    return baseline


def save_local_baseline(report: dict[str, Any], name: str) -> Path:
    """
    Save the current test report as a named local baseline.
    Returns the path to the saved baseline file.
    """
    # Create baselines directory if needed
    BASELINES_DIR.mkdir(parents=True, exist_ok=True)

    # Save the baseline file
    baseline_file = BASELINES_DIR / f"{name}.json"
    baseline_file.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Update the index
    index_data: dict[str, Any] = {"version": "1", "baselines": []}
    if BASELINES_INDEX.exists():
        try:
            index_data = json.loads(BASELINES_INDEX.read_text())
        except Exception:
            pass

    # Get metadata for index entry
    summary = report.get("summary", {})
    commit = report.get("commit", {}) or {}
    git_info = report.get("run", {}).get("git", {}) or {}

    entry = {
        "name": name,
        "created_at": report.get("generated_at"),
        "commit_hash": commit.get("short_hash"),
        "branch": git_info.get("branch"),
        "tests_total": summary.get("total", 0),
        "passed": summary.get("passed", 0),
        "failed": summary.get("failed", 0),
        "platform": platform.system().lower(),
    }

    # Remove existing entry with same name if present
    baselines = [b for b in index_data.get("baselines", []) if b.get("name") != name]
    baselines.insert(0, entry)  # Add new entry at the beginning
    index_data["baselines"] = baselines

    BASELINES_INDEX.write_text(json.dumps(index_data, indent=2), encoding="utf-8")

    return baseline_file


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
ORCHESTRATOR_BIND_HOST = os.getenv("FBRK_TEST_BIND_HOST", "0.0.0.0")
ORCHESTRATOR_REPORT_HOST = os.getenv("FBRK_TEST_REPORT_HOST", ORCHESTRATOR_BIND_HOST)

# Perf compare thresholds (baseline vs current)
PERF_THRESHOLD_PERCENT = float(os.getenv("FBRK_TEST_PERF_THRESHOLD_PERCENT", "0.30"))
PERF_MIN_TIME_DIFF_S = float(os.getenv("FBRK_TEST_PERF_MIN_TIME_DIFF_S", "1.0"))
PERF_MIN_MEMORY_DIFF_MB = float(os.getenv("FBRK_TEST_PERF_MIN_MEMORY_DIFF_MB", "50.0"))

# Report config
REPORT_SCHEMA_VERSION = "4"
REPORT_JSON_PATH = Path("artifacts/test-report.json")
REPORT_LLM_JSON_PATH = Path("artifacts/test-report.llm.json")
REPORT_HTML_PATH = Path("artifacts/test-report.html")

# Local baselines config
BASELINES_DIR = Path("artifacts/baselines")
BASELINES_INDEX = BASELINES_DIR / "index.json"

# Output truncation config (0 = no truncation)
OUTPUT_MAX_BYTES = int(os.getenv("FBRK_TEST_OUTPUT_MAX_BYTES", "0"))
OUTPUT_TRUNCATE_MODE = os.getenv("FBRK_TEST_OUTPUT_TRUNCATE_MODE", "tail")

# LLM summary output (only when --llm)
LLM_SUMMARY_MAX_ITEMS = int(os.getenv("FBRK_TEST_LLM_SUMMARY_MAX_ITEMS", "10"))

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


def split_nodeid(nodeid: str) -> tuple[str, str, str, str]:
    parts = nodeid.split("::")
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
            function_name, params = extract_params(rest[0])
    return file_path, class_name, function_name, params


def _safe_iso(dt: datetime.datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat(sep=" ", timespec="seconds")


def _collect_env_subset() -> dict[str, str]:
    env = {}
    keys = {
        "CI",
        "GITHUB_ACTIONS",
        "PYTEST_ADDOPTS",
        "PYTHONHASHSEED",
    }
    for k, v in os.environ.items():
        if k.startswith("FBRK_TEST_") or k in keys:
            env[k] = v
    return env


def _get_git_info() -> dict[str, Any] | None:
    branch = get_current_branch()
    if not branch:
        return None
    info: dict[str, Any] = {"branch": branch}
    info["remote_tracking"] = get_remote_tracking_branch()
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode == 0:
            info["dirty"] = bool(result.stdout.strip())
    except Exception:
        pass
    return info


_ANSI_PATTERN = re.compile(r"(?:\x1B\[[0-?]*[ -/]*[@-~])|(?:\x1B\].*?(?:\x07|\x1b\\))")


def _strip_ansi(text: str) -> str:
    if not text:
        return text
    return _ANSI_PATTERN.sub("", text)


def _sanitize_output(output: dict[str, Any] | None) -> dict[str, Any] | None:
    if not output:
        return output
    cleaned: dict[str, Any] = {}
    for key, value in output.items():
        cleaned[key] = _strip_ansi(value) if isinstance(value, str) else value
    return cleaned


def _truncate_text(text: str) -> tuple[str, dict[str, Any]]:
    raw = text.encode("utf-8", errors="replace")
    total = len(raw)
    meta = {
        "bytes_total": total,
        "bytes_kept": total,
        "truncated": False,
        "limit": OUTPUT_MAX_BYTES,
        "mode": OUTPUT_TRUNCATE_MODE,
    }
    if OUTPUT_MAX_BYTES <= 0 or total <= OUTPUT_MAX_BYTES:
        return text, meta

    kept = raw
    if OUTPUT_TRUNCATE_MODE == "head":
        kept = raw[:OUTPUT_MAX_BYTES]
        marker = f"\n...[truncated {total - OUTPUT_MAX_BYTES} bytes]...\n"
        text_out = kept.decode("utf-8", errors="replace") + marker
    else:
        kept = raw[-OUTPUT_MAX_BYTES:]
        marker = f"\n...[truncated {total - OUTPUT_MAX_BYTES} bytes]...\n"
        text_out = marker + kept.decode("utf-8", errors="replace")

    meta["bytes_kept"] = len(kept)
    meta["truncated"] = True
    return text_out, meta


def _apply_output_limits(
    output: dict[str, str] | None,
) -> tuple[dict[str, str] | None, dict[str, dict[str, Any]] | None]:
    if not output:
        return None, None
    limited = {}
    meta = {}
    for key, value in output.items():
        if value is None:
            continue
        limited_value, info = _truncate_text(value)
        limited[key] = limited_value
        meta[key] = info
    return limited, meta


def _percentiles(values: list[float], percentiles: list[int]) -> dict[str, float]:
    if not values:
        return {}
    values = sorted(values)
    out: dict[str, float] = {}
    for p in percentiles:
        if len(values) == 1:
            out[f"p{p}"] = values[0]
            continue
        k = (len(values) - 1) * (p / 100)
        f = int(k)
        c = min(f + 1, len(values) - 1)
        if f == c:
            out[f"p{p}"] = values[f]
        else:
            d = k - f
            out[f"p{p}"] = values[f] + (values[c] - values[f]) * d
    return out


def _outcome_to_str(outcome: Outcome | str | None) -> str | None:
    if outcome is None:
        return None
    if isinstance(outcome, Outcome):
        return outcome.name.lower()
    return str(outcome).lower()


def _compare_to_str(compare: CompareStatus | str | None) -> str | None:
    if compare is None:
        return None
    if isinstance(compare, CompareStatus):
        return compare.name.lower()
    return str(compare).lower()


def _baseline_record(
    baseline_map: dict[str, dict[str, Any]], nodeid: str
) -> dict[str, Any] | None:
    if not baseline_map:
        return None
    record = baseline_map.get(nodeid)
    if not record:
        return None
    if isinstance(record, str):
        return {"outcome": record}
    return record


def _compare_status(current: str | None, baseline: str | None) -> str | None:
    if baseline is None:
        return "new"
    if current is None:
        return None
    valid = {"passed", "failed", "error", "crashed", "skipped"}
    if current not in valid:
        return None
    if current == baseline:
        return "same"
    if baseline == "passed" and current in ("failed", "error", "crashed"):
        return "regression"
    if baseline in ("failed", "error", "crashed") and current == "passed":
        return "fixed"
    return "same"


def _perf_change(
    current: float | None,
    baseline: float | None,
    min_diff: float,
    threshold_percent: float,
) -> tuple[float | None, float | None, bool]:
    if not current or not baseline or baseline <= 0 or current <= 0:
        return None, None, False
    diff = current - baseline
    pct = diff / baseline
    significant = abs(diff) >= min_diff and abs(pct) >= threshold_percent
    return diff, pct, significant


def _default_llm_section() -> dict[str, Any]:
    return {
        "source_of_truth": str(REPORT_JSON_PATH),
        "note": "This JSON is the single source of truth for test results.",
        "why_use_this": [
            "Contains stdout/stderr/logs/traceback + truncation metadata.",
            "Use test.output_full for complete logs; test.output is the HTML preview.",
            "Includes baseline comparisons (regressions/fixed/new/removed).",
            "Captures memory usage and worker log paths.",
            "Includes collection errors and run metadata.",
        ],
        "jq_recipes": [
            f"jq '.summary' {REPORT_JSON_PATH}",
            "jq -r '.derived.failures[] | \"\\(.nodeid) :: \\(.error_message)\"' "
            f"{REPORT_JSON_PATH}",
            'jq -r \'.tests[] | select(.status!="passed") '
            "| {nodeid,output_full}' "
            f"{REPORT_JSON_PATH}",
            'jq -r \'.tests[] | select(.status!="passed") '
            "| {nodeid,status,error_message}' "
            f"{REPORT_JSON_PATH}",
            "jq -r '.tests | sort_by(.duration_s) | reverse | .[:10] "
            "| .[] | {nodeid,duration_s}' "
            f"{REPORT_JSON_PATH}",
            "jq -r '.derived.perf_regressions[] "
            "| {nodeid,duration_delta_s,speedup_pct}' "
            f"{REPORT_JSON_PATH}",
            "jq -r '.tests[] | select(.compare_status==\"regression\") | .nodeid' "
            f"{REPORT_JSON_PATH}",
        ],
        "recommended_commands": [],
    }


def _split_error_message(error_message: str | None) -> tuple[str | None, str | None]:
    if not error_message:
        return None, None
    msg = error_message.strip()
    if ": " in msg:
        left, right = msg.split(": ", 1)
        if left and " " not in left and len(left) < 64:
            return left, right
    return None, msg


def _print_llm_summary(report: dict[str, Any]) -> None:
    summary = report.get("summary", {})
    baseline = report.get("baseline", {})
    derived = report.get("derived", {})
    llm = report.get("llm", {})

    print("\nLLM summary (from artifacts/test-report.json)")
    print("Note: JSON is the source of truth; HTML/LLM JSON are derived.")
    print(f"LLM JSON (derived): {REPORT_LLM_JSON_PATH}")
    print(
        "Summary: "
        f"passed={summary.get('passed', 0)} "
        f"failed={summary.get('failed', 0)} "
        f"errors={summary.get('errors', 0)} "
        f"crashed={summary.get('crashed', 0)} "
        f"skipped={summary.get('skipped', 0)} "
        f"running={summary.get('running', 0)} "
        f"queued={summary.get('queued', 0)} "
        f"collection_errors={summary.get('collection_errors', 0)} "
        f"perf_regressions={summary.get('perf_regressions', 0)} "
        f"truncated_outputs={summary.get('output_truncated_tests', 0)}"
    )
    if report.get("run", {}).get("selection_applied"):
        print("Selection: filtered run (test args applied)")

    if baseline.get("loaded"):
        scope = summary.get("baseline_scope", "full")
        removed = summary.get("removed", 0)
        removed_total = summary.get("removed_total", removed)
        print(
            "Baseline: "
            f"commit={baseline.get('commit_hash')} "
            f"branch={baseline.get('branch')} "
            f"regressions={summary.get('regressions', 0)} "
            f"fixed={summary.get('fixed', 0)} "
            f"new={summary.get('new_tests', 0)} "
            f"removed={removed}"
        )
        if scope != "full" and removed_total:
            print(
                f"Baseline scope: {scope} (filtered run; removed_total={removed_total})"
            )
    elif baseline.get("error"):
        print(f"Baseline: error={baseline.get('error')}")

    why = llm.get("why_use_this", [])
    if why:
        print("\nWhy use the report JSON:")
        for line in why:
            print(f"- {line}")

    def _print_items(label: str, items: list[dict[str, Any]]):
        if not items:
            return
        print(f"\n{label} (top {min(len(items), LLM_SUMMARY_MAX_ITEMS)}):")
        for item in items[:LLM_SUMMARY_MAX_ITEMS]:
            nodeid = item.get("nodeid", "<unknown>")
            status = item.get("status") or item.get("compare_status") or ""
            error_message = item.get("error_summary") or item.get("error_message") or ""
            if error_message:
                print(f"- {nodeid} [{status}] :: {error_message}")
            elif status:
                print(f"- {nodeid} [{status}]")
            else:
                print(f"- {nodeid}")

    _print_items("Failures", derived.get("failures", []))
    _print_items("Regressions", derived.get("regressions", []))
    _print_items("Collection Errors", derived.get("collection_errors", []))

    perf_regs = derived.get("perf_regressions", [])
    if perf_regs:
        print(f"\nPerf regressions (top {min(len(perf_regs), LLM_SUMMARY_MAX_ITEMS)}):")
        for item in perf_regs[:LLM_SUMMARY_MAX_ITEMS]:
            nodeid = item.get("nodeid", "<unknown>")
            delta = item.get("duration_delta_s")
            pct = item.get("speedup_pct")
            if delta is not None and pct is not None:
                print(f"- {nodeid} (+{delta:.2f}s, {pct:.1f}%)")
            else:
                print(f"- {nodeid}")

    slowest = derived.get("slowest", [])
    if slowest:
        print(f"\nSlowest tests (top {min(len(slowest), LLM_SUMMARY_MAX_ITEMS)}):")
        for item in slowest[:LLM_SUMMARY_MAX_ITEMS]:
            nodeid = item.get("nodeid", "<unknown>")
            duration = item.get("duration_s", 0.0)
            print(f"- {nodeid} ({duration:.2f}s)")

    recommended = llm.get("recommended_commands", [])
    if recommended:
        print("\nRecommended commands (top 6):")
        for rec in recommended[:6]:
            desc = rec.get("description", "")
            cmd = rec.get("command", "")
            if desc:
                print(f"- {desc}: {cmd}")
            else:
                print(f"- {cmd}")

    print("\nSchema (top-level keys):")
    print(
        "schema_version, generated_at, run, summary, commit, ci, baseline, "
        "artifacts, collection_errors, tests, derived, llm"
    )
    print("Schema (run keys):")
    print(
        "start_time, end_time, duration_s, pytest_args, selection_applied, "
        "env, git, orchestrator_report_url, output_limits, perf"
    )
    print("Schema (test keys):")
    print(
        "nodeid, file, class, function, params, status, outcome, duration_s, "
        "error_message, output, output_full, output_meta, memory_usage_mb, "
        "memory_peak_mb, compare_status, speedup_pct"
    )

    recipes = llm.get("jq_recipes", [])
    if recipes:
        print("\nJQ tips:")
        for recipe in recipes:
            print(recipe)


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
            outcome = _outcome_to_str(t["outcome"])
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
            output, output_meta = _apply_output_limits(output_full)

            if state == "running" and t["pid"]:
                worker_log = self.get_worker_log(t["pid"])
                if worker_log:
                    live_output, live_meta = _apply_output_limits({"live": worker_log})
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
            error_type, error_summary = _split_error_message(t["error_message"])
            baseline_rec = _baseline_record(baseline.tests, t["nodeid"])
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
            compare_status = _compare_status(status, baseline_outcome)
            if compare_status == "regression":
                regressions += 1
            elif compare_status == "fixed":
                fixed += 1
            elif compare_status == "new":
                new_tests += 1

            duration_delta_s, duration_delta_pct, duration_sig = _perf_change(
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

            memory_delta_mb, memory_delta_pct, memory_sig = _perf_change(
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
                    "start_time": _safe_iso(t["start_time"]),
                    "finish_time": _safe_iso(t["finish_time"]),
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

        duration_percentiles = _percentiles(durations, [50, 90, 95, 99])
        memory_usage_percentiles = _percentiles(memory_usage_values, [50, 90, 95, 99])
        memory_peak_percentiles = _percentiles(memory_peak_values, [50, 90, 95, 99])

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

        llm_section = _default_llm_section()

        report = {
            "schema_version": REPORT_SCHEMA_VERSION,
            "generated_at": _safe_iso(now),
            "run": {
                "start_time": _safe_iso(start_time),
                "end_time": _safe_iso(now if running == 0 and queued == 0 else None),
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
                "env": _collect_env_subset(),
                "git": _get_git_info(),
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
                "llm_json": str(REPORT_LLM_JSON_PATH),
                "logs_dir": str(LOG_DIR),
            },
            "collection_errors": collection_error_entries,
            "tests": test_entries,
            "derived": derived,
            "llm": llm_section,
        }

        recommended = []
        for item in derived["failures"][:LLM_SUMMARY_MAX_ITEMS]:
            nodeid = item["nodeid"]
            recommended.append(
                {
                    "description": "Re-run single test (orchestrated)",
                    "command": f'ato dev test --llm -k "{nodeid}"',
                }
            )
            recommended.append(
                {
                    "description": "Re-run single test (direct, tight loop; no report)",
                    "command": f'ato dev test --direct -k "{nodeid}"',
                }
            )
        report["llm"]["recommended_commands"] = recommended

        return report

    def write_json_report(self, report: dict[str, Any], output_path: Path):
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"Failed to write JSON report: {e}")

    def write_llm_report(self, report: dict[str, Any], output_path: Path):
        llm_data = dict(report.get("llm") or {})
        llm_data["output_sanitized"] = True
        llm_data["contains_full_tests"] = True
        tests = []
        for t in report.get("tests", []):
            entry = dict(t)
            output = entry.get("output")
            output_full = entry.get("output_full")
            sanitized = False
            if output is not None:
                entry["output"] = _sanitize_output(output)
                sanitized = True
            if output_full is not None:
                entry["output_full"] = _sanitize_output(output_full)
                sanitized = True
            if sanitized:
                entry["output_sanitized"] = True
            tests.append(entry)
        llm_report = {
            "schema_version": REPORT_SCHEMA_VERSION,
            "generated_at": report.get("generated_at"),
            "run": report.get("run"),
            "summary": report.get("summary"),
            "baseline": report.get("baseline"),
            "commit": report.get("commit"),
            "ci": report.get("ci"),
            "derived": report.get("derived"),
            "llm": llm_data,
            "tests": tests,
            "collection_errors": report.get("collection_errors", []),
            "artifacts": report.get("artifacts", {}),
            "paths": {
                "json": str(REPORT_JSON_PATH),
                "html": str(REPORT_HTML_PATH),
                "logs_dir": str(LOG_DIR),
            },
        }
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(llm_report, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"Failed to write LLM JSON report: {e}")

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

            if log_content:
                safe_nodeid = html.escape(t["nodeid"])
                modal_id = f"modal_{safe_nodeid}"
                log_button = (
                    f"<button onclick=\"openModal('{modal_id}')\">View Logs</button>"
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
        self.write_llm_report(report, REPORT_LLM_JSON_PATH)
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
        outcome = _outcome_to_str(t.get("outcome") or t.get("status"))
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

        baseline_rec = _baseline_record(baseline.tests, nodeid) if nodeid else None
        baseline_outcome = baseline_rec.get("outcome") if baseline_rec else None
        compare_status = (
            _compare_status(status, baseline_outcome) if baseline.loaded else None
        )
        t["compare_status"] = compare_status
        t["baseline_outcome"] = baseline_outcome

        if compare_status == "regression":
            regressions += 1
        elif compare_status == "fixed":
            fixed += 1
        elif compare_status == "new":
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

        duration_delta_s, duration_delta_pct, duration_sig = _perf_change(
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

        memory_delta_mb, memory_delta_pct, memory_sig = _perf_change(
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

    duration_percentiles = _percentiles(durations, [50, 90, 95, 99])
    memory_usage_percentiles = _percentiles(memory_usage_values, [50, 90, 95, 99])
    memory_peak_percentiles = _percentiles(memory_peak_values, [50, 90, 95, 99])

    total_duration = summary.get("total_duration_s")
    if total_duration is None:
        total_duration = run.get("duration_s", 0.0)
    total_memory_mb = sum(t.get("memory_usage_mb", 0.0) for t in tests)

    total_tests = len(tests)
    total_finished = passed + failed + errors + crashed + skipped
    progress_percent = int((total_finished / total_tests) * 100) if total_tests else 0

    report["generated_at"] = _safe_iso(now)
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

    llm_section = _default_llm_section()
    recommended = []
    for item in report["derived"]["failures"][:LLM_SUMMARY_MAX_ITEMS]:
        nodeid = item["nodeid"]
        recommended.append(
            {
                "description": "Re-run single test (orchestrated)",
                "command": f'ato dev test --llm -k "{nodeid}"',
            }
        )
        recommended.append(
            {
                "description": "Re-run single test (direct, tight loop; no report)",
                "command": f'ato dev test --direct -k "{nodeid}"',
            }
        )
    llm_section["recommended_commands"] = recommended
    report["llm"] = llm_section
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
    TestAggregator([], RemoteBaseline()).write_llm_report(updated, REPORT_LLM_JSON_PATH)
    return updated


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
    report_path = REPORT_HTML_PATH
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


@app.get("/api/baselines")
async def get_baselines():
    """List available local baselines."""
    baselines = list_local_baselines()
    return {"baselines": baselines}


@app.post("/api/change-baseline")
async def change_baseline(request: Request):
    """Change baseline and regenerate report."""
    try:
        body = await request.json()
        baseline_name = body.get("baseline")
    except Exception:
        return {"error": "Invalid request body"}

    if not baseline_name:
        return {"error": "No baseline specified"}

    try:
        if baseline_name.startswith("local:"):
            # Load local baseline
            name = baseline_name[6:]  # Remove "local:" prefix
            new_baseline = load_local_baseline(name)
        else:
            # Fetch remote baseline by commit hash
            new_baseline = fetch_remote_report(commit_hash=baseline_name)

        if not new_baseline.loaded:
            return {"error": new_baseline.error or "Failed to load baseline"}

        # Update global baseline and aggregator
        global remote_baseline
        remote_baseline = new_baseline

        if aggregator:
            aggregator.set_baseline(new_baseline)
            # Regenerate reports with new baseline
            aggregator.generate_reports(periodic=False)

        return {"success": True, "baseline": baseline_name}
    except Exception as e:
        return {"error": str(e)}


# Mount the existing logs WebSocket router from atopile.server
from atopile.server.routes.logs import router as logs_router

app.include_router(logs_router)

# Path to the log viewer static files
LOG_VIEWER_DIST_DIR = (
    Path(__file__).parent.parent.parent / "src" / "ui-server" / "dist"
)


@app.get("/logs")
async def serve_log_viewer():
    """Serve the log viewer HTML page."""
    html_path = LOG_VIEWER_DIST_DIR / "log-viewer.html"
    if not html_path.exists():
        return HTMLResponse(
            content="<html><body><h1>Log viewer not found</h1>"
            f"<p>Expected at: {html_path}</p>"
            "<p>Run 'npm run build' in src/ui-server to build it.</p></body></html>",
            status_code=404,
        )

    content = html_path.read_text(encoding="utf-8")
    return HTMLResponse(content=content)


@app.get("/logViewer.js")
async def serve_log_viewer_js():
    """Serve the log viewer JavaScript bundle."""
    from starlette.responses import FileResponse

    js_path = LOG_VIEWER_DIST_DIR / "logViewer.js"
    if js_path.exists():
        return FileResponse(js_path, media_type="application/javascript")
    return HTMLResponse("Not found", status_code=404)


@app.get("/logViewer.css")
async def serve_log_viewer_css():
    """Serve the log viewer CSS."""
    from starlette.responses import FileResponse

    css_path = LOG_VIEWER_DIST_DIR / "logViewer.css"
    if css_path.exists():
        return FileResponse(css_path, media_type="text/css")
    return HTMLResponse("Not found", status_code=404)


@app.get("/index.css")
async def serve_index_css():
    """Serve the shared CSS."""
    from starlette.responses import FileResponse

    css_path = LOG_VIEWER_DIST_DIR / "index.css"
    if css_path.exists():
        return FileResponse(css_path, media_type="text/css")
    return HTMLResponse("Not found", status_code=404)


@app.get("/index-{hash}.js")
async def serve_shared_js(hash: str):
    """Serve the shared JavaScript chunk."""
    from starlette.responses import FileResponse

    # Find any file matching the pattern
    for f in LOG_VIEWER_DIST_DIR.glob("index-*.js"):
        return FileResponse(f, media_type="application/javascript")
    return HTMLResponse("Not found", status_code=404)


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
            self._aggregator.generate_reports(periodic=True)
            time.sleep(self._interval)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)


def get_free_port(start_port: int = 50000, max_attempts: int = 100) -> int:
    """
    Find a free port starting from start_port.

    First tries to kill any stale process on the preferred port to ensure
    consistent port usage across test runs. This prevents issues where old
    browser tabs connect to stale servers on different ports.
    """
    from atopile.server.server import is_port_in_use, kill_process_on_port

    # Try to claim the preferred port first, killing any stale process
    if is_port_in_use(start_port):
        _print(f"Port {start_port} in use, killing stale process...")
        if kill_process_on_port(start_port):
            _print(f"Killed stale process on port {start_port}")
        else:
            _print(f"Could not kill process on port {start_port}, will try next port")

    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((ORCHESTRATOR_BIND_HOST, port))
                return port
        except OSError:
            continue
    # Fallback to OS-assigned port if all preferred ports are taken
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((ORCHESTRATOR_BIND_HOST, 0))
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
        "--continue-on-collection-errors",
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


def start_server(port) -> uvicorn.Server:
    config = uvicorn.Config(
        app,
        host=ORCHESTRATOR_BIND_HOST,
        port=port,
        log_level="error",
        access_log=False,
    )
    server = uvicorn.Server(config)

    t = threading.Thread(target=server.run, daemon=True)
    t.start()

    # Wait for server to start
    time.sleep(1.0)
    return server


def get_log_file(worker_id: int) -> Path:
    return LOG_DIR / f"worker-{worker_id}.log"


LOG_DIR = Path("artifacts/logs")


def run_report_server(open_browser: bool = False) -> None:
    port = get_free_port()
    url = f"http://127.0.0.1:{port}"
    report_url = f"http://{ORCHESTRATOR_REPORT_HOST}:{port}/report"
    local_report_url = f"http://127.0.0.1:{port}/report"
    _print(f"Starting report server at {url}")
    server = start_server(port)

    clickable_link = f"\033]8;;{report_url}\033\\📊 {report_url}\033]8;;\033\\"
    _print(f"Live report: {clickable_link}")
    if ORCHESTRATOR_REPORT_HOST == "0.0.0.0":
        local_clickable = (
            f"\033]8;;{local_report_url}\033\\📍 {local_report_url}\033]8;;\033\\"
        )
        _print(f"Local report: {local_clickable}")

    if open_browser:
        import webbrowser

        webbrowser.open(local_report_url)

    _print("Keep-open enabled. Press Ctrl+C to stop the report server.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        _print("Stopping report server...")
        server.should_exit = True


def main(
    args: list[str] | None = None,
    baseline_commit: str | None = None,
    local_baseline_name: str | None = None,
    save_baseline_name: str | None = None,
    open_browser: bool = False,
    llm: bool = False,
    keep_open: bool = False,
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
    # or load local baseline synchronously if specified
    global remote_baseline
    baseline_fetch_complete = threading.Event()

    if local_baseline_name:
        # Load local baseline synchronously
        _print(f"Loading local baseline '{local_baseline_name}'...")
        remote_baseline = load_local_baseline(local_baseline_name)
        if remote_baseline.loaded:
            _print(
                f"Local baseline loaded: {local_baseline_name} "
                f"({len(remote_baseline.tests)} tests)"
            )
        elif remote_baseline.error:
            _print(f"Baseline error: {remote_baseline.error}")
        baseline_fetch_complete.set()
    else:

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

        baseline_thread = threading.Thread(
            target=fetch_baseline_background, daemon=True
        )
        baseline_thread.start()
        if baseline_commit:
            _print(f"Fetching baseline for commit {baseline_commit} (background)...")
        else:
            _print("Fetching baseline from GitHub (background)...")

    # Initialize aggregator with loaded baseline (for local) or empty (for remote fetch)
    global aggregator
    initial_baseline = remote_baseline if local_baseline_name else RemoteBaseline()
    aggregator = TestAggregator(
        tests,
        initial_baseline,
        pytest_args=pytest_args,
        baseline_requested=baseline_commit or local_baseline_name,
        collection_errors=errors,
    )

    for error_key, error_value in errors.items():
        aggregator._tests[error_key] = TestState(
            nodeid=error_key,
            pid=None,
            start_time=None,
            output={"stderr": error_value},
            outcome=Outcome.ERROR,
            error_message=error_value.splitlines()[-1].strip(),
            collection_error=True,
        )

    for t in tests:
        test_queue.put(t)

    # 2. Start Orchestrator
    port = get_free_port()
    url = f"http://127.0.0.1:{port}"
    report_url = f"http://{ORCHESTRATOR_REPORT_HOST}:{port}/report"
    local_report_url = f"http://127.0.0.1:{port}/report"
    aggregator.set_orchestrator_url(url)
    _print(f"Starting orchestrator at {url}")
    aggregator.set_orchestrator_report_url(report_url)
    server = start_server(port)

    # Print clickable link to the report (ANSI hyperlink format for terminals)
    # Use OSC 8 hyperlink escape sequence for clickable links in modern terminals
    clickable_link = f"\033]8;;{report_url}\033\\📊 {report_url}\033]8;;\033\\"
    _print(f"Live report: {clickable_link}")
    if ORCHESTRATOR_REPORT_HOST == "0.0.0.0":
        local_clickable = (
            f"\033]8;;{local_report_url}\033\\📍 {local_report_url}\033]8;;\033\\"
        )
        _print(f"Local report: {local_clickable}")

    # Open browser if requested
    if open_browser:
        import webbrowser

        webbrowser.open(local_report_url)

    # 3. Start Workers
    worker_script = Path(__file__).parent / "worker.py"

    env = os.environ.copy()
    env["FBRK_TEST_ORCHESTRATOR_URL"] = url
    # Ensure workers can find test modules
    env["PYTHONPATH"] = os.getcwd()
    # no need to keep on recompiling zig
    # already done during discovery latest
    env["FBRK_ZIG_NORECOMPILE"] = "1"
    if "FBRK_LOG_FMT" not in env:
        env["FBRK_LOG_FMT"] = "1"
    # Generate test_run_id once and share across all workers
    import hashlib
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    test_run_id = hashlib.sha256(f"pytest:{timestamp}".encode()).hexdigest()[:16]
    env["ATO_TEST_RUN_ID"] = test_run_id

    # Store test_run_id for HTML template
    if aggregator:
        aggregator.set_test_run_id(test_run_id)

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
        aggregator.register_worker(i, p.pid)

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

        # Shutdown the HTTP server to release the port
        if not keep_open:
            server.should_exit = True

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

    report = aggregator.generate_reports(periodic=False)

    # Save as local baseline if requested
    if save_baseline_name:
        baseline_path = save_local_baseline(report, save_baseline_name)
        _print(f"Baseline saved: {baseline_path}")

    # Print link to the static report file
    report_path = REPORT_HTML_PATH.resolve()
    file_url = f"file://{report_path}"
    clickable_file = f"\033]8;;{file_url}\033\\📄 {report_path}\033]8;;\033\\"
    _print(f"Report saved: {clickable_file}")

    if llm:
        _print_llm_summary(report)

    exit_code = 1 if aggregator.has_failures() else 0

    if keep_open:
        _print("Keep-open enabled. Press Ctrl+C to stop the report server.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            _print("Stopping report server...")
            server.should_exit = True
        sys.exit(exit_code)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
