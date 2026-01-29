"""
Git and CI information utilities.

Handles extracting commit and CI information from git and environment variables.
"""

import json
import os
import platform
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, cast


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


def get_git_info() -> dict[str, Any] | None:
    """Get git repository information (branch, dirty status, etc.)."""
    from .baselines import get_current_branch, get_remote_tracking_branch

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


def collect_env_subset() -> dict[str, str]:
    """Collect a subset of environment variables relevant to testing."""
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


# Get platform name
def get_platform_name() -> str:
    """Get normalized platform name."""
    return platform.system().lower()
