"""
Baseline management for test results.

Handles fetching, caching, and comparing test baselines from:
- Remote GitHub Actions artifacts
- Local baseline files
"""

import json
import subprocess
import tempfile
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum, auto
from pathlib import Path
from typing import Any, Optional


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


# Global state for remote commits (populated in background)
remote_commits: list[dict[str, Any]] = []
remote_commits_lock = threading.Lock()

# Global cache of workflow runs across all branches (commit_hash -> workflow info)
workflow_runs_cache: dict[str, dict[str, Any]] = {}
workflow_runs_lock = threading.Lock()


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


def get_remote_branch_heads() -> list[dict[str, str]]:
    """
    Get all remote branch heads.
    Returns list of dicts with branch name, commit hash, and commit message.
    """
    branches = []
    try:
        # Get all remote branches with their commit info
        result = subprocess.run(
            [
                "git",
                "for-each-ref",
                "--format=%(refname:short)|%(objectname)|%(objectname:short=8)|%(subject)|%(authorname)|%(committerdate:iso8601)",
                "refs/remotes/origin",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if not line or "origin/HEAD" in line:
                    continue
                parts = line.split("|", 5)
                if len(parts) == 6:
                    ref, full_hash, short_hash, message, author, timestamp = parts
                    # Strip origin/ prefix
                    branch_name = ref.replace("origin/", "", 1)
                    branches.append(
                        {
                            "branch": branch_name,
                            "commit_hash": short_hash,
                            "commit_hash_full": full_hash,
                            "commit_message": message,
                            "commit_author": author,
                            "commit_time": timestamp,
                        }
                    )
    except Exception as e:
        print(f"Warning: Could not fetch remote branches: {e}")
    return branches


def get_branch_base(branch: Optional[str] = None) -> Optional[dict[str, str]]:
    """
    Get the merge-base of the current branch with main/master.
    Returns dict with commit info or None if not found.
    """
    if branch is None:
        branch = get_current_branch()
    if not branch:
        return None

    # Try main first, then master
    for main_branch in ["main", "master"]:
        try:
            # Check if main branch exists
            result = subprocess.run(
                ["git", "rev-parse", "--verify", f"origin/{main_branch}"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode != 0:
                continue

            # Get merge-base
            result = subprocess.run(
                ["git", "merge-base", "HEAD", f"origin/{main_branch}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                merge_base_hash = result.stdout.strip()

                # Get commit info
                result = subprocess.run(
                    [
                        "git",
                        "show",
                        "--format=%H|%h|%s|%an|%ai",
                        "--no-patch",
                        merge_base_hash,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    parts = result.stdout.strip().split("|", 4)
                    if len(parts) == 5:
                        full_hash, short_hash, message, author, timestamp = parts
                        return {
                            "commit_hash": short_hash[:8],
                            "commit_hash_full": full_hash,
                            "commit_message": message,
                            "commit_author": author,
                            "commit_time": timestamp,
                            "base_branch": main_branch,
                        }
        except Exception:
            continue
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


def fetch_remote_report(
    commit_hash: Optional[str] = None,
    use_cache: bool = True,
    remote_baselines_dir: Path = Path("artifacts/baselines/remote"),
) -> RemoteBaseline:
    """
    Fetch a test report from GitHub Actions.

    If commit_hash is provided, fetches the report for that specific commit.
    Otherwise, fetches the most recent completed run for the current branch
    (falling back to 'main' if no runs exist for the current branch).

    Uses the `gh` CLI to download artifacts from workflow runs.
    Caches downloaded baselines for faster subsequent access.
    """
    # Check cache first if commit_hash is provided and caching is enabled
    if commit_hash and use_cache:
        cached = load_cached_remote_baseline(commit_hash, remote_baselines_dir)
        if cached:
            return cached

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

            # Cache the baseline if successfully loaded
            if baseline.loaded and baseline.commit_hash and use_cache:
                cache_remote_baseline(
                    baseline.commit_hash, baseline, remote_baselines_dir
                )

        except Exception as e:
            baseline.error = f"Error downloading/parsing artifact: {e}"
            return baseline

    return baseline


def list_local_baselines(
    baselines_index: Path = Path("artifacts/baselines/index.json"),
) -> list[dict[str, Any]]:
    """List all available local baselines."""
    if not baselines_index.exists():
        return []
    try:
        index_data = json.loads(baselines_index.read_text())
        return index_data.get("baselines", [])
    except Exception:
        return []


def load_local_baseline(
    name: str, baselines_dir: Path = Path("artifacts/baselines")
) -> RemoteBaseline:
    """
    Load a local baseline by name.
    Returns a RemoteBaseline object for compatibility with existing comparison logic.
    """
    baseline = RemoteBaseline()

    baseline_file = baselines_dir / f"{name}.json"
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


def save_local_baseline(
    report: dict[str, Any],
    name: str,
    baselines_dir: Path = Path("artifacts/baselines"),
    baselines_index: Path = Path("artifacts/baselines/index.json"),
    platform_name: str = "unknown",
) -> Path:
    """
    Save the current test report as a named local baseline.
    Returns the path to the saved baseline file.
    """
    # Create baselines directory if needed
    baselines_dir.mkdir(parents=True, exist_ok=True)

    # Save the baseline file
    baseline_file = baselines_dir / f"{name}.json"
    baseline_file.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Update the index
    index_data: dict[str, Any] = {"version": "1", "baselines": []}
    if baselines_index.exists():
        try:
            index_data = json.loads(baselines_index.read_text())
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
        "platform": platform_name,
    }

    # Remove existing entry with same name if present
    baselines = [b for b in index_data.get("baselines", []) if b.get("name") != name]
    baselines.insert(0, entry)  # Add new entry at the beginning
    index_data["baselines"] = baselines

    baselines_index.write_text(json.dumps(index_data, indent=2), encoding="utf-8")

    return baseline_file


def fetch_remote_commits(branch: str, limit: int = 20) -> list[dict[str, Any]]:
    """
    Fetch a list of recent commits from git, marking which ones have workflow runs.

    Strategy:
    1. Use git log to get all recent commits on the branch
    2. Use gh run list to get workflow runs
    3. Match them up to mark which commits have test results available

    Returns a list of commits with metadata including:
    - commit_hash: Short commit hash (8 chars)
    - commit_hash_full: Full commit hash
    - commit_message: First line of commit message
    - commit_author: Author name
    - commit_time: Commit timestamp
    - branch: Branch name
    - run_id: GitHub Actions run ID (if workflow run exists)
    - created_at: Workflow run timestamp (if exists)
    - conclusion: Workflow conclusion (if exists)
    - has_artifact: Whether test-report.json artifact exists
    - has_workflow_run: Whether this commit has any workflow run
    """
    commits = []

    # First, get all recent commits from git log
    try:
        # Try remote branch first, fall back to local branch
        git_ref = f"origin/{branch}"
        result = subprocess.run(
            ["git", "rev-parse", "--verify", git_ref],
            capture_output=True,
            timeout=5,
        )
        if result.returncode != 0:
            # Remote branch doesn't exist, use local
            git_ref = branch

        result = subprocess.run(
            [
                "git",
                "log",
                git_ref,
                "--format=%H|%h|%s|%an|%ai",
                f"-{limit}",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return commits

        # Parse git log output
        git_commits = {}
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|", 4)
            if len(parts) == 5:
                full_hash, short_hash, message, author, timestamp = parts
                git_commits[full_hash] = {
                    "commit_hash": short_hash[:8],
                    "commit_hash_full": full_hash,
                    "commit_message": message,
                    "commit_author": author,
                    "commit_time": timestamp,
                    "branch": branch,
                    "run_id": None,
                    "created_at": "",
                    "conclusion": "",
                    "has_artifact": False,
                    "has_workflow_run": False,
                }
    except Exception as e:
        print(f"Warning: Could not fetch git commits: {e}")
        return commits

    # Check if gh CLI is available
    gh_available = True
    try:
        subprocess.run(
            ["gh", "--version"],
            capture_output=True,
            timeout=5,
        )
    except (FileNotFoundError, Exception):
        gh_available = False

    # Now fetch workflow runs and match them with git commits
    if gh_available:
        try:
            # Fetch more workflow runs than commits to increase chance of matches
            result = subprocess.run(
                [
                    "gh",
                    "run",
                    "list",
                    "--branch",
                    branch,
                    "--workflow",
                    "pytest.yml",
                    "--limit",
                    str(limit * 3),  # Fetch 3x to cover commits without runs
                    "--json",
                    "databaseId,headSha,headBranch,createdAt,conclusion,status",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                runs = json.loads(result.stdout)

                # Create a map of commit hash -> workflow run
                run_map = {}
                for run in runs:
                    commit_hash_full = run.get("headSha", "")
                    if commit_hash_full and commit_hash_full not in run_map:
                        # Keep only the most recent run for each commit
                        run_map[commit_hash_full] = run

                # Match workflow runs with git commits
                for full_hash, commit_data in git_commits.items():
                    if full_hash in run_map:
                        run = run_map[full_hash]
                        commit_data["has_workflow_run"] = True
                        commit_data["run_id"] = run.get("databaseId")
                        commit_data["created_at"] = run.get("createdAt", "")
                        commit_data["conclusion"] = run.get("conclusion", "")
                        commit_data["status"] = run.get("status", "")

                        # Skip artifact check during fetch - too slow.
                        # Check lazily when user selects baseline.
                        # Assume completed runs have artifacts.
                        if run.get("status") == "completed":
                            commit_data["has_artifact"] = True  # Optimistic assumption
        except Exception as e:
            print(f"Warning: Could not fetch workflow runs: {e}")

    # Convert to list and return
    commits = list(git_commits.values())
    return commits


def fetch_all_workflow_runs(limit: int = 200) -> dict[str, dict[str, Any]]:
    """
    Fetch workflow runs across ALL branches (not filtered by branch).
    Returns a map of commit_hash -> workflow info.
    This is used to populate the global workflow runs cache.
    """
    workflow_map = {}

    try:
        # Check if gh CLI is available
        subprocess.run(
            ["gh", "--version"],
            capture_output=True,
            timeout=5,
        )
    except (FileNotFoundError, Exception):
        return workflow_map

    try:
        # Fetch workflow runs WITHOUT branch filter to get all branches
        result = subprocess.run(
            [
                "gh",
                "run",
                "list",
                "--workflow",
                "pytest.yml",
                "--limit",
                str(limit),
                "--json",
                "databaseId,headSha,headBranch,createdAt,conclusion,status",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0 and result.stdout.strip():
            runs = json.loads(result.stdout)

            for run in runs:
                commit_hash_full = run.get("headSha", "")
                if not commit_hash_full:
                    continue

                # Get short hash (8 chars)
                commit_hash_short = (
                    commit_hash_full[:8]
                    if len(commit_hash_full) >= 8
                    else commit_hash_full
                )

                # Only keep the most recent run for each commit
                if commit_hash_short not in workflow_map:
                    workflow_map[commit_hash_short] = {
                        "has_workflow_run": True,
                        "has_artifact": run.get("status")
                        == "completed",  # Optimistic assumption
                        "run_id": run.get("databaseId"),
                        "status": run.get("status", ""),
                        "conclusion": run.get("conclusion", ""),
                        "branch": run.get("headBranch", ""),
                    }

    except Exception as e:
        print(f"Warning: Could not fetch all workflow runs: {e}")

    return workflow_map


def cache_remote_baseline(
    commit_hash: str, baseline: RemoteBaseline, remote_baselines_dir: Path
) -> None:
    """
    Cache a remote baseline to disk.
    Baselines are stored as: artifacts/baselines/remote/<commit_hash>.json
    """
    if not baseline.loaded or not baseline.tests:
        return

    # Create cache directory
    remote_baselines_dir.mkdir(parents=True, exist_ok=True)

    # Build cache data structure (similar to test report format)
    cache_data = {
        "commit": {
            "hash": baseline.commit_hash_full,
            "short_hash": baseline.commit_hash,
            "author": baseline.commit_author,
            "message": baseline.commit_message,
            "time": baseline.commit_time,
        },
        "baseline": {
            "branch": baseline.branch,
        },
        "tests": [
            {
                "nodeid": nodeid,
                "outcome": test_data["outcome"],
                "duration_s": test_data.get("duration_s"),
                "memory_usage_mb": test_data.get("memory_usage_mb", 0.0),
                "memory_peak_mb": test_data.get("memory_peak_mb", 0.0),
            }
            for nodeid, test_data in baseline.tests.items()
        ],
    }

    # Write cache file
    cache_file = remote_baselines_dir / f"{commit_hash}.json"
    cache_file.write_text(json.dumps(cache_data, indent=2), encoding="utf-8")

    # Update cache index
    update_remote_cache_index(commit_hash, baseline, remote_baselines_dir)


def update_remote_cache_index(
    commit_hash: str, baseline: RemoteBaseline, remote_baselines_dir: Path
) -> None:
    """Update the remote baseline cache index."""
    index_file = remote_baselines_dir / "index.json"
    index_data: dict[str, Any] = {"version": "1", "cached_commits": []}

    if index_file.exists():
        try:
            index_data = json.loads(index_file.read_text())
        except Exception:
            pass

    # Remove existing entry for this commit
    cached = [
        c
        for c in index_data.get("cached_commits", [])
        if c.get("commit_hash") != commit_hash
    ]

    # Add new entry
    cached.insert(
        0,
        {
            "commit_hash": commit_hash,
            "commit_hash_full": baseline.commit_hash_full,
            "branch": baseline.branch,
            "cached_at": datetime.now().isoformat(),
            "test_count": len(baseline.tests),
        },
    )

    index_data["cached_commits"] = cached
    index_file.write_text(json.dumps(index_data, indent=2), encoding="utf-8")


def load_cached_remote_baseline(
    commit_hash: str, remote_baselines_dir: Path
) -> Optional[RemoteBaseline]:
    """
    Load a cached remote baseline from disk.
    Returns None if not cached.
    """
    cache_file = remote_baselines_dir / f"{commit_hash}.json"
    if not cache_file.exists():
        return None

    try:
        data = json.loads(cache_file.read_text())
        baseline = RemoteBaseline()

        # Parse tests
        tests = {}
        for t in data.get("tests", []):
            nodeid = t.get("nodeid")
            outcome = t.get("outcome")
            if not nodeid or not outcome:
                continue
            tests[nodeid] = {
                "outcome": str(outcome).lower(),
                "duration_s": t.get("duration_s"),
                "memory_usage_mb": t.get("memory_usage_mb", 0.0),
                "memory_peak_mb": t.get("memory_peak_mb", 0.0),
            }
        baseline.tests = tests
        baseline.loaded = True

        # Parse metadata
        commit_data = data.get("commit", {})
        baseline.commit_hash = commit_data.get("short_hash", commit_hash)
        baseline.commit_hash_full = commit_data.get("hash")
        baseline.commit_author = commit_data.get("author")
        baseline.commit_message = commit_data.get("message")
        baseline.commit_time = commit_data.get("time")
        baseline.branch = data.get("baseline", {}).get("branch")

        return baseline
    except Exception as e:
        print(f"Warning: Failed to load cached baseline for {commit_hash}: {e}")
        return None
