"""
UI routes for the test runner dashboard.

Provides endpoints for viewing reports, managing baselines, and the log viewer.
"""

import subprocess
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from atopile.server.routes.logs import router as logs_router
from test.runner.baselines import (
    fetch_remote_report,
    get_branch_base,
    get_remote_branch_heads,
    list_local_baselines,
    load_local_baseline,
    remote_commits,
    remote_commits_lock,
    workflow_runs_cache,
    workflow_runs_lock,
)

router = APIRouter()

# These will be set by main.py
aggregator = None  # type: ignore
REPORT_HTML_PATH = Path("artifacts/test-report.html")
REMOTE_BASELINES_DIR = Path("artifacts/baselines/remote")

# Path to the log viewer static files
LOG_VIEWER_DIST_DIR = Path(__file__).parent.parent.parent / "src" / "ui-server" / "dist"


def set_globals(agg_ref, report_path, remote_dir):
    """Set global references from main module."""
    global aggregator, REPORT_HTML_PATH, REMOTE_BASELINES_DIR
    aggregator = agg_ref
    REPORT_HTML_PATH = report_path
    REMOTE_BASELINES_DIR = remote_dir


def get_aggregator():
    """Get the current aggregator instance."""
    return aggregator


def set_aggregator(agg):
    """Set the aggregator instance."""
    global aggregator
    aggregator = agg


@router.get("/")
async def report_redirect():
    """Redirect root to the test report."""
    return HTMLResponse(
        content='<html><head><meta http-equiv="refresh" content="0; url=/report">'
        "</head></html>"
    )


@router.get("/report")
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


@router.get("/api/baselines")
async def get_baselines():
    """List available local baselines."""
    baselines = list_local_baselines()
    return {"baselines": baselines}


@router.post("/api/change-baseline")
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
        elif baseline_name.startswith("remote:"):
            # Fetch remote baseline by commit hash
            commit_hash = baseline_name[7:]  # Remove "remote:" prefix
            new_baseline = fetch_remote_report(commit_hash=commit_hash, use_cache=True)
        else:
            # Legacy support: assume it's a commit hash
            new_baseline = fetch_remote_report(
                commit_hash=baseline_name, use_cache=True
            )

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


@router.get("/api/remote-commits")
async def get_remote_commits(branch: Optional[str] = None):
    """
    Get list of recent commits with workflow runs from GitHub.
    Returns cached commit list populated during test startup.
    Also includes branch heads and branch base.
    """
    with remote_commits_lock:
        commits_list = list(remote_commits)

    # Get current commit for comparison
    current_commit = None
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=8", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            current_commit = result.stdout.strip()
    except Exception:
        pass

    # Mark cached commits
    for commit in commits_list:
        commit_hash = commit.get("commit_hash", "")
        cache_file = REMOTE_BASELINES_DIR / f"{commit_hash}.json"
        commit["cached"] = cache_file.exists()

    # Get remote branch heads
    branch_heads = get_remote_branch_heads()

    # Get workflow runs cache
    with workflow_runs_lock:
        workflow_cache = dict(workflow_runs_cache)

    for branch_head in branch_heads:
        commit_hash = branch_head.get("commit_hash", "")
        cache_file = REMOTE_BASELINES_DIR / f"{commit_hash}.json"
        branch_head["cached"] = cache_file.exists()

        # If cached, it definitely has artifacts
        if branch_head["cached"]:
            branch_head["has_workflow_run"] = True
            branch_head["has_artifact"] = True
        elif commit_hash in workflow_cache:
            # Use workflow info from global cache (across all branches)
            branch_head["has_workflow_run"] = workflow_cache[commit_hash][
                "has_workflow_run"
            ]
            branch_head["has_artifact"] = workflow_cache[commit_hash]["has_artifact"]
        else:
            # Not cached and not in workflow runs - no workflow run
            branch_head["has_workflow_run"] = False
            branch_head["has_artifact"] = False

    # Get branch base (merge-base with main)
    branch_base = get_branch_base()
    if branch_base:
        commit_hash = branch_base.get("commit_hash", "")
        cache_file = REMOTE_BASELINES_DIR / f"{commit_hash}.json"
        branch_base["cached"] = cache_file.exists()

        # If cached, it definitely has artifacts
        if branch_base["cached"]:
            branch_base["has_workflow_run"] = True
            branch_base["has_artifact"] = True
        elif commit_hash in workflow_cache:
            # Use workflow info from global cache
            branch_base["has_workflow_run"] = workflow_cache[commit_hash][
                "has_workflow_run"
            ]
            branch_base["has_artifact"] = workflow_cache[commit_hash]["has_artifact"]
        else:
            # Not cached and not in workflow runs - no workflow run
            branch_base["has_workflow_run"] = False
            branch_base["has_artifact"] = False

    return {
        "commits": commits_list,
        "current_commit": current_commit,
        "branch_heads": branch_heads,
        "branch_base": branch_base,
    }


@router.get("/api/baseline-status")
async def get_baseline_status(commit: str):
    """
    Check the status of a baseline (cached, downloading, error).
    """
    cache_file = REMOTE_BASELINES_DIR / f"{commit}.json"
    cached = cache_file.exists()

    return {
        "cached": cached,
        "downloading": False,  # Could track with background download tasks
        "error": None,
    }


@router.get("/logs")
async def serve_log_viewer(request: Request):
    """Serve the log viewer HTML page with injected API URL."""
    html_path = LOG_VIEWER_DIST_DIR / "log-viewer.html"
    if not html_path.exists():
        return HTMLResponse(
            content="<html><body><h1>Log viewer not found</h1>"
            f"<p>Expected at: {html_path}</p>"
            "<p>Run 'npm run build' in src/ui-server to build it.</p></body></html>",
            status_code=404,
        )

    content = html_path.read_text(encoding="utf-8")

    # Inject the API URL so the log viewer can connect to this server's WebSocket
    # The log viewer JavaScript expects window.__ATOPILE_API_URL__ to be set
    host = request.headers.get("host", "127.0.0.1")
    # Ensure we use http (not https) for local server
    api_url = f"http://{host}"
    inject_script = f"""<script>
    window.__ATOPILE_API_URL__ = "{api_url}";
    </script>
    """
    # Insert the script right after <head>
    content = content.replace("<head>", f"<head>\n    {inject_script}", 1)

    return HTMLResponse(content=content)


# Include the logs WebSocket router from atopile.server
router.include_router(logs_router)
