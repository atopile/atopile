#!/usr/bin/env python3
"""
Fetch and display pytest summaries from recent GitHub Actions runs.

Polls a workflow on a branch, downloads the "test-report" (pytest-html) artifact,
parses summary counts, caches results, and renders a CRT-style local HTML
dashboard with a multi-run trend chart.

Requirements:
- Python 3.8+
- GH_TOKEN env var with "repo" or "public_repo" scope.

Usage:
  GH_TOKEN=... python scripts/dashboards/fetch_dashboard.py --branch feature/fabll_part2
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo


WORKFLOW_FILENAME = "pytest.yml"  # GitHub workflow file name (override with --workflow)
REPORT_ARTIFACT_NAME = "test-report"
REPORT_COPY_BASENAME = "test-report.html"
POLL_SECONDS = 30
BROWSER_CMD = "chromium-browser"
DEFAULT_REPO = "atopile/atopile"
DEFAULT_BRANCH = "feature/fabll_part2"
DEFAULT_RECENT_RUNS = 50
DEFAULT_DAYS_BACK = 7
CACHE_FILENAME = ".dashboard_cache.json"
SCRIPT_DIR = Path(__file__).resolve().parent


def gh_request(url: str, token: str, accept: str | None = None) -> bytes:
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "dashboard-fetcher")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if accept:
        req.add_header("Accept", accept)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"GitHub API error {e.code}: {e.read().decode()}") from e


def get_recent_runs_page(
    repo: str,
    branch: str,
    token: str,
    workflow_filename: str | None = WORKFLOW_FILENAME,
    per_page: int = 100,
    page: int = 1,
    status: str | None = None,
) -> list[dict]:
    per_page = max(1, min(100, per_page))
    page = max(1, page)
    branch_q = urllib.parse.quote(branch)
    endpoint = (
        f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_filename}/runs"
        if workflow_filename
        else f"https://api.github.com/repos/{repo}/actions/runs"
    )
    url = f"{endpoint}?branch={branch_q}&per_page={per_page}&page={page}"
    if status:
        url += f"&status={urllib.parse.quote(status)}"
    data = json.loads(gh_request(url, token))
    runs = data.get("workflow_runs", []) or []
    return runs


def get_artifact_download_url(repo: str, run_id: int, token: str) -> str | None:
    """
    Find the archive_download_url for the named report artifact.
    The artifacts list is paginated; page until found or exhausted.
    """
    page = 1
    per_page = 100
    while page <= 10:
        url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/artifacts?per_page={per_page}&page={page}"
        data = json.loads(gh_request(url, token))
        artifacts = data.get("artifacts", []) or []
        for artifact in artifacts:
            if artifact.get("name") == REPORT_ARTIFACT_NAME:
                download_url = artifact.get("archive_download_url")
                if download_url:
                    return download_url
        if len(artifacts) < per_page:
            break
        page += 1
    return None


def download_artifact_zip(url: str, token: str, dest_zip: Path) -> None:
    # Follow redirect to signed Azure URL; drop GitHub headers once off github.com
    class _Redirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
            if new_req is None:
                return None
            host = urllib.parse.urlparse(newurl).hostname or ""
            if host not in {"github.com", "api.github.com"}:
                new_req.headers.pop("Authorization", None)
                new_req.headers.pop("X-GitHub-Api-Version", None)
                new_req.headers.pop("Accept", None)
            return new_req

    opener = urllib.request.build_opener(_Redirect)
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "dashboard-fetcher")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    # Per GitHub docs, keep vnd.github+json to get a redirect with a signed URL
    req.add_header("Accept", "application/vnd.github+json")
    with opener.open(req) as resp:
        dest_zip.write_bytes(resp.read())


def extract_artifact_member(zip_path: Path, dest_dir: Path, suffixes: tuple[str, ...]) -> Path | None:
    suffixes = tuple(s.lower() for s in suffixes)
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.namelist():
            if member.lower().endswith(suffixes):
                zf.extract(member, path=dest_dir)
                return Path(dest_dir) / member
    return None


def inject_refresh(html_path: Path, seconds: int) -> None:
    if seconds <= 0:
        return
    text = html_path.read_text(encoding="utf-8")
    if 'http-equiv="refresh"' in text:
        return
    marker = "<head>"
    tag = f'<meta http-equiv="refresh" content="{seconds}">'
    if marker in text:
        text = text.replace(marker, f"{marker}\n  {tag}", 1)
    else:
        text = f"{tag}\n{text}"
    html_path.write_text(text, encoding="utf-8")


def _as_int(value: object) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _extract_first_int(text: str) -> int:
    if not text:
        return 0
    match = re.search(r"(-?\d[\d,]*)", text)
    if not match:
        return 0
    return int(match.group(1).replace(",", ""))


def parse_pytest_html_summary(html_text: str) -> dict:
    """Return pytest result counts parsed from the pytest-html report."""
    summary = {
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "xfailed": 0,
        "xpassed": 0,
        "tests": 0,
    }

    filters_block = None
    marker = '<div class="filters">'
    marker_idx = html_text.find(marker)
    if marker_idx != -1:
        after = html_text[marker_idx + len(marker) :]
        end_idx = after.find("</div>")
        if end_idx != -1:
            filters_block = after[:end_idx]

    class_map = {
        "passed": "passed",
        "failed": "failed",
        "error": "errors",
        "skipped": "skipped",
        "xfailed": "xfailed",
        "xpassed": "xpassed",
    }

    if filters_block:
        for cls, key in class_map.items():
            match = re.search(rf'<span class="{cls}">(.*?)</span>', filters_block, re.IGNORECASE | re.DOTALL)
            if match:
                summary[key] = _extract_first_int(match.group(1))

    run_count_match = re.search(r'<p class="run-count">(.*?)</p>', html_text, re.IGNORECASE | re.DOTALL)
    if run_count_match:
        summary["tests"] = _extract_first_int(run_count_match.group(1))

    if summary["tests"] <= 0:
        summary["tests"] = sum(summary[k] for k in ("passed", "failed", "errors", "skipped", "xfailed", "xpassed"))

    return summary


def parse_failing_tests_by_file(html_text: str) -> list[tuple[str, int]]:
    """
    Extract failing tests from pytest-html report and group by file.
    Returns list of (file_path, failure_count) tuples sorted by count descending.
    """
    import html

    # Find the data-container JSON blob
    match = re.search(r'<div[^>]+id="data-container"[^>]+data-jsonblob="([^"]+)"', html_text)
    if not match:
        return []

    try:
        json_str = html.unescape(match.group(1))
        data = json.loads(json_str)
        tests = data.get("tests", {})
    except (json.JSONDecodeError, KeyError):
        return []

    # Count failures per file
    file_counts: dict[str, int] = {}
    for test_id, runs in tests.items():
        for run in runs:
            # Check for failed or error status
            result = run.get("result", "").lower()
            if result in ("failed", "error"):
                # Extract file path from test_id (format: "path/to/file.py::test_name")
                file_path = test_id.split("::")[0]
                file_counts[file_path] = file_counts.get(file_path, 0) + 1
                break  # Only count once per test_id

    # Sort by count descending, then alphabetically by file path
    sorted_files = sorted(file_counts.items(), key=lambda x: (-x[1], x[0]))
    return sorted_files


def format_commit_time(iso_time: str) -> str:
    """Format ISO timestamp to human-readable PST time."""
    try:
        # Parse ISO 8601 timestamp (GitHub returns UTC)
        dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
        # Convert to PST (Pacific Standard Time)
        pst = ZoneInfo("America/Los_Angeles")
        dt_pst = dt.astimezone(pst)
        # Format: "Nov 20, 2025 at 3:45 PM PST"
        return dt_pst.strftime("%b %d, %Y at %I:%M %p %Z")
    except Exception:
        return iso_time


def inject_run_metadata(summary: dict, run: dict) -> None:
    head_commit = run.get("head_commit") or {}
    status = run.get("conclusion") or run.get("status")
    if status:
        summary["status"] = status
    if "status" not in summary:
        summary["status"] = "unknown"

    run_url = run.get("html_url")
    if run_url:
        summary["run_url"] = run_url
    if "run_url" not in summary:
        summary["run_url"] = ""

    commit_time_raw = (
        head_commit.get("timestamp")
        or run.get("updated_at")
        or run.get("created_at")
    )
    if commit_time_raw:
        summary["commit_time"] = format_commit_time(commit_time_raw)
        summary["commit_time_iso"] = commit_time_raw
    if "commit_time" not in summary:
        summary["commit_time"] = "unknown"
    if "commit_time_iso" not in summary:
        summary["commit_time_iso"] = ""

    message = (head_commit.get("message") or "").strip()
    if message:
        summary["commit_message"] = message
    if "commit_message" not in summary:
        summary["commit_message"] = "unknown"

    author = (
        (head_commit.get("author") or {}).get("name")
        or (head_commit.get("author") or {}).get("email")
    )
    if not author:
        author = (
            (head_commit.get("committer") or {}).get("name")
            or (head_commit.get("committer") or {}).get("email")
        )
    if author:
        summary["commit_author"] = author
    if "commit_author" not in summary:
        summary["commit_author"] = "unknown"


def _load_cache(out_dir: Path) -> dict[str, dict]:
    cache_path = out_dir / CACHE_FILENAME
    if not cache_path.exists():
        return {}
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_cache(out_dir: Path, cache: dict[str, dict]) -> None:
    cache_path = out_dir / CACHE_FILENAME
    try:
        cache_path.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")
    except Exception:
        pass


def _fetch_summary_for_run(repo: str, run: dict, token: str) -> tuple[dict | None, str | None]:
    """
    Download the test-report artifact for a run and parse summary.
    Returns (summary, html_text). html_text is provided for optional extra parsing.
    """
    run_id = run.get("id")
    if not run_id:
        return None, None
    artifact_url = get_artifact_download_url(repo, run_id, token)
    if not artifact_url:
        return None, None
    with TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "artifact.zip"
        download_artifact_zip(artifact_url, token, zip_path)
        artifact_member = extract_artifact_member(zip_path, Path(tmpdir), (".html", ".htm"))
        if not artifact_member:
            return None, None
        html_text = artifact_member.read_text(encoding="utf-8")
        summary: dict[str, object] = parse_pytest_html_summary(html_text)
        inject_run_metadata(summary, run)
        return summary, html_text


def _run_timestamp(run: dict) -> datetime | None:
    ts = run.get("run_started_at") or run.get("created_at") or run.get("updated_at")
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def _parse_iso_timestamp(ts: object) -> datetime | None:
    if not ts or not isinstance(ts, str):
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def get_runs_within_window(
    repo: str,
    branch: str,
    token: str,
    max_runs: int,
    days_back: int,
    status: str | None = None,
    workflow_filename: str | None = WORKFLOW_FILENAME,
    debug: bool = False,
) -> list[dict]:
    """
    Collect up to max_runs completed runs from the last days_back days.
    Fetches additional pages if needed so the window can fill max_runs.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    collected: list[dict] = []
    page = 1
    per_page = 100

    while len(collected) < max_runs and page <= 10:  # hard cap to avoid infinite loops
        runs_page = get_recent_runs_page(
            repo,
            branch,
            token,
            workflow_filename=workflow_filename,
            per_page=per_page,
            page=page,
            status=status,
        )
        if not runs_page:
            break
        for run in runs_page:
            dt = _run_timestamp(run)
            if dt is None:
                continue
            if dt >= cutoff:
                collected.append(run)
                if len(collected) >= max_runs:
                    break
        # If the oldest run in this page is already older than cutoff, no need to keep paging.
        oldest_dt = _run_timestamp(runs_page[-1])
        if oldest_dt is not None and oldest_dt < cutoff:
            break
        page += 1

    # Ensure descending order (newest first)
    collected.sort(key=lambda r: _run_timestamp(r) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    if debug:
        newest = _run_timestamp(collected[0]) if collected else None
        oldest = _run_timestamp(collected[-1]) if collected else None
        wf = workflow_filename or "<all workflows>"
        print(
            f"Debug: workflow={wf} fetched_pages={page-1} "
            f"collected={len(collected)} cutoff={cutoff.isoformat()} "
            f"newest={newest.isoformat() if newest else 'n/a'} "
            f"oldest={oldest.isoformat() if oldest else 'n/a'}"
        )
    return collected[:max_runs]


# =============================================================================
# HTML BUILDING BLOCKS
# =============================================================================


def _get_dashboard_css() -> str:
    """Return the complete CSS stylesheet for the CRT-style dashboard theme."""
    return """
    :root {
      --bg: #020703;
      --panel: rgba(4, 18, 10, 0.82);
      --border: #1c3a25;
      --phosphor: #b4ffb0;
      --muted: #7acb8e;
      --accent: #d4ffd7;
      --danger: #ff6b6b;
    }
    * {
      box-sizing: border-box;
    }

    /* === Page Layout === */
    body {
      margin: 0;
      padding: 24px;
      min-height: 100vh;
      font-family: "IBM Plex Mono", "Fira Code", "SFMono-Regular", monospace;
      background:
        radial-gradient(circle at 50% 15%, rgba(30, 70, 40, 0.35), transparent 40%),
        radial-gradient(circle at 20% 80%, rgba(12, 40, 20, 0.35), transparent 35%),
        radial-gradient(circle at 80% 70%, rgba(8, 25, 15, 0.3), transparent 45%),
        #020703;
      color: var(--phosphor);
      text-shadow: 0 0 12px rgba(158, 252, 141, 0.45), 0 0 28px rgba(158, 252, 141, 0.25);
      overflow-x: hidden;
      position: relative;
      cursor: none;
    }
    .dashboard-layout {
      display: flex;
      gap: 32px;
      align-items: stretch;
      height: calc(100vh - 48px);
    }

    /* === Panel Components === */
    .panel {
      position: relative;
      padding: 24px;
      border: 1px solid var(--border);
      border-radius: 18px;
      background: linear-gradient(135deg, rgba(4, 18, 9, 0.9), rgba(6, 28, 12, 0.92));
      box-shadow:
        0 0 60px rgba(12, 60, 26, 0.45),
        0 0 30px rgba(12, 60, 26, 0.4) inset;
      overflow-y: auto;
    }
    .panel--main {
      flex: 1;
      padding: 32px;
      box-shadow:
        0 0 90px rgba(12, 60, 26, 0.55),
        0 0 40px rgba(12, 60, 26, 0.5) inset,
        0 0 140px rgba(12, 60, 26, 0.35) inset;
    }
    .panel--sidebar {
      width: 500px;
      flex-shrink: 0;
    }
    .panel__content {
      position: relative;
      z-index: 2;
    }
    .panel__glass {
      position: absolute;
      inset: 0;
      pointer-events: none;
      background:
        radial-gradient(ellipse at 20% 10%, rgba(255, 255, 255, 0.08), transparent 30%),
        radial-gradient(ellipse at 80% 0%, rgba(255, 255, 255, 0.05), transparent 28%);
      mix-blend-mode: screen;
      opacity: 0.6;
      z-index: 1;
    }
    .panel::-webkit-scrollbar { width: 8px; }
    .panel::-webkit-scrollbar-track { background: rgba(0, 0, 0, 0.2); border-radius: 4px; }
    .panel::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
    .panel::-webkit-scrollbar-thumb:hover { background: var(--muted); }

    /* === CRT Effects === */
    .scanlines {
      position: fixed;
      inset: 0;
      pointer-events: none;
      background: repeating-linear-gradient(
        to bottom,
        rgba(0, 0, 0, 0.2) 0, rgba(0, 0, 0, 0.2) 2px,
        rgba(255, 255, 255, 0.02) 2px, rgba(255, 255, 255, 0.02) 3px,
        transparent 3px, transparent 5px
      );
      mix-blend-mode: multiply;
      opacity: 0.75;
      z-index: 7;
      animation: roll 8s linear infinite;
    }
    .noise {
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image: radial-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 0);
      background-size: 3px 3px;
      opacity: 0.25;
      mix-blend-mode: screen;
      animation: jitter 1.2s steps(4, end) infinite;
      z-index: 8;
    }
    .flicker { animation: flicker 4s infinite; }
    .ghost { text-shadow: 0 0 10px rgba(158, 252, 141, 0.45), 2px 0 14px rgba(158, 252, 141, 0.18); }

    /* === Typography === */
    h2 { margin: 0 0 12px; font-size: 2rem; letter-spacing: 0.5px; }
    .meta { font-size: 1.6rem; margin: 0 0 12px; color: var(--accent); }

    /* === Main Panel Components === */
    .status {
      font-size: 1.8rem;
      margin-bottom: 16px;
      display: flex;
      align-items: center;
      gap: 12px;
      justify-content: space-between;
      width: 100%;
    }
    .status__left { display: inline-flex; align-items: center; gap: 12px; }
    .status__right { color: var(--accent); font-size: 1.6rem; }
    .pill {
      display: inline-block;
      padding: 6px 16px;
      border-radius: 999px;
      border: 1px solid var(--border);
      background: rgba(0, 0, 0, 0.2);
      color: var(--phosphor);
      box-shadow: 0 0 14px rgba(158, 252, 141, 0.35);
      font-weight: 700;
    }
    ul {
      list-style: none;
      padding: 0;
      margin: 18px 0;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 12px;
    }
    li {
      background: rgba(5, 18, 10, 0.75);
      border: 1px solid #15341f;
      border-radius: 14px;
      padding: 16px 18px;
      box-shadow: 0 0 18px rgba(12, 60, 26, 0.35) inset;
      font-size: 1.4rem;
    }
    .label { color: var(--muted); }
    .count { float: right; color: var(--accent); font-weight: 800; font-size: 1.8rem; }
    .meta-container {
      background: rgba(4, 14, 7, 0.65);
      border: 1px solid #173923;
      border-radius: 14px;
      padding: 18px;
      box-shadow: 0 0 24px rgba(12, 60, 26, 0.4) inset;
      margin-top: 22px;
    }
    .meta-container .meta { color: var(--accent); }
    .meta-container .meta:last-child { margin-bottom: 0; }
    .meta-container a { color: var(--phosphor); text-decoration: none; border-bottom: 1px dashed rgba(158, 252, 141, 0.5); }
    .meta-container a:hover { color: #d6ffd2; }

    /* === Sidebar Components === */
    .panel--sidebar h2 { color: var(--danger); text-shadow: 0 0 12px rgba(255, 107, 107, 0.5); }
    .failing-files-list { display: flex; flex-direction: column; gap: 8px; margin: 16px 0 0 0; }
    .failing-files-list li {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 14px;
      font-size: 1.1rem;
      border-radius: 10px;
    }
    .file-count {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 32px;
      height: 28px;
      padding: 0 8px;
      background: rgba(220, 38, 38, 0.25);
      border: 1px solid rgba(220, 38, 38, 0.5);
      border-radius: 6px;
      color: var(--danger);
      font-weight: 800;
      font-size: 1.2rem;
      text-shadow: 0 0 8px rgba(255, 107, 107, 0.5);
    }
    .file-path { color: var(--muted); font-size: 1rem; word-break: break-all; }

    /* === Animations === */
    @keyframes roll { from { background-position: 0 0; } to { background-position: 0 8px; } }
    @keyframes jitter {
      0% { transform: translate(0, 0); }
      20% { transform: translate(-1px, 0.5px); }
      40% { transform: translate(1px, -0.5px); }
      60% { transform: translate(-0.5px, -1px); }
      80% { transform: translate(0.5px, 0.5px); }
      100% { transform: translate(0, 0); }
    }
    @keyframes flicker {
      0% { opacity: 0.96; } 5% { opacity: 0.85; } 10% { opacity: 0.98; }
      15% { opacity: 0.92; } 25% { opacity: 0.97; } 30% { opacity: 0.88; }
      40% { opacity: 1; } 50% { opacity: 0.9; } 60% { opacity: 0.99; }
      70% { opacity: 0.93; } 80% { opacity: 0.96; } 90% { opacity: 0.89; }
      100% { opacity: 0.98; }
    }

    /* === Charts === */
    .chart-container {
      margin: 24px 0;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .chart {
      width: 100%;
      background: rgba(2, 10, 5, 0.8);
      border: 1px solid #183822;
      border-radius: 14px;
      padding: 8px;
      box-shadow: 0 0 12px rgba(158, 252, 141, 0.25) inset;
    }
    .chart svg { width: 100%; height: 264px; display: block; }
    .chart text {
      fill: var(--phosphor);
      font-size: 12px;
      text-shadow: none;
    }
    .legend {
      display: flex;
      gap: 14px;
      font-size: 1.2rem;
      color: var(--muted);
      flex-wrap: wrap;
      margin-top: 6px;
    }
    .legend-swatch {
      display: inline-block;
      width: 10px;
      height: 10px;
      margin-right: 6px;
      border-radius: 2px;
      vertical-align: middle;
    }
"""


def _build_panel(content: str, modifier: str = "") -> str:
    """Generate a panel HTML element with glass effect and content wrapper."""
    mod_class = f" panel--{modifier}" if modifier else ""
    return f"""<div class="panel{mod_class} flicker">
      <div class="panel__glass"></div>
      <div class="panel__content">
{content}
      </div>
    </div>"""


def _build_trend_charts(history: list[dict]) -> str:
    if not history or len(history) < 2:
        return ""

    # History comes oldest -> newest.
    passed = [_as_int(h.get("passed")) for h in history]
    failed = [_as_int(h.get("failed")) for h in history]
    errors = [_as_int(h.get("errors")) for h in history]
    totals: list[int] = []
    for h in history:
        t = _as_int(h.get("tests"))
        if t <= 0:
            t = (
                _as_int(h.get("passed"))
                + _as_int(h.get("failed"))
                + _as_int(h.get("errors"))
                + _as_int(h.get("skipped"))
                + _as_int(h.get("xfailed"))
                + _as_int(h.get("xpassed"))
            )
        totals.append(max(t, 0))

    # Build x-axis labels at day intervals to reduce clutter.
    labels: list[str] = []
    last_day: str | None = None
    for h in history:
        ct = h.get("commit_time") or ""
        day_str = ""
        if isinstance(ct, str) and ct != "unknown":
            day_str = ct.split(" at ")[0]
        if day_str and day_str != last_day:
            labels.append(day_str)
            last_day = day_str
        else:
            labels.append("")
    if labels and not labels[-1]:
        # Ensure most recent point is labeled.
        ct_last = history[-1].get("commit_time") or ""
        if isinstance(ct_last, str) and ct_last != "unknown":
            labels[-1] = ct_last.split(" at ")[0]

    max_y = max(passed + failed + errors + totals + [1])

    width = 900
    height = int(220 * 1.2)
    pad_left, pad_right, pad_top, pad_bottom = 48, 12, 12, 40
    mascot_gutter = 84  # reserved space on right for mascots
    plot_right = width - pad_right - mascot_gutter
    inner_w = plot_right - pad_left
    inner_h = height - pad_top - pad_bottom

    def y(v: int) -> float:
        return pad_top + inner_h * (1 - (v / max_y))

    n = len(history)
    dts = [
        _parse_iso_timestamp(h.get("commit_time_iso") or h.get("run_time_iso"))
        for h in history
    ]
    known_dts = [dt for dt in dts if dt is not None]
    if len(known_dts) >= 2:
        local_tz = ZoneInfo("America/Los_Angeles")
        work_start_h, work_end_h = 8, 20  # local hours inclusive of weekends

        def _work_seconds_up_to(dt_local: datetime, base_date: datetime.date) -> float:
            total_s = 0.0
            day = base_date
            last_day = dt_local.date()
            one_day = timedelta(days=1)
            full_day_s = (work_end_h - work_start_h) * 3600
            while day < last_day:
                total_s += full_day_s
                day += one_day
            ws = datetime(last_day.year, last_day.month, last_day.day, work_start_h, tzinfo=local_tz)
            we = datetime(last_day.year, last_day.month, last_day.day, work_end_h, tzinfo=local_tz)
            clamped = min(max(dt_local, ws), we)
            total_s += max(0.0, (clamped - ws).total_seconds())
            return total_s

        known_locals = [dt.astimezone(local_tz) for dt in known_dts]
        min_dt_local = min(known_locals)
        base_date = min_dt_local.date()
        base_offset = _work_seconds_up_to(min_dt_local, base_date)

        work_vals: list[float | None] = []
        for dt in dts:
            if dt is None:
                work_vals.append(None)
                continue
            dt_local = dt.astimezone(local_tz)
            work_vals.append(_work_seconds_up_to(dt_local, base_date) - base_offset)

        known_work = [v for v in work_vals if v is not None]
        span_work = max(known_work) - min(known_work) if known_work else 0.0

        if span_work > 0:
            xs = []
            for i, v in enumerate(work_vals):
                if v is None:
                    frac = i / (n - 1)
                else:
                    frac = v / span_work
                xs.append(pad_left + inner_w * frac)
        else:
            xs = [pad_left + (inner_w * i / (n - 1)) for i in range(n)]
    else:
        xs = [pad_left + (inner_w * i / (n - 1)) for i in range(n)]

    def polyline(values: list[int], color: str, width: float = 2.5, dash: str | None = None) -> str:
        points = " ".join(f"{xs[i]:.1f},{y(values[i]):.1f}" for i in range(n))
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        core_w = max(1.0, width * 0.55)
        # Colored beam + white-hot core for over-exposed look.
        return (
            f'<polyline fill="none" stroke="{color}" stroke-width="{width:.1f}" '
            f'stroke-linecap="round" stroke-linejoin="round" '
            f'stroke-opacity="0.7" filter="url(#line-glow)" '
            f'style="mix-blend-mode:plus-lighter"'
            f'{dash_attr} points="{points}" />'
            f'<polyline fill="none" stroke="rgba(248,255,248,0.7)" stroke-width="{core_w:.1f}" '
            f'stroke-linecap="round" stroke-linejoin="round" '
            f'style="mix-blend-mode:plus-lighter"'
            f'{dash_attr} points="{points}" />'
        )

    def markers(values: list[int], color: str, radius: float = 3.0) -> str:
        dots = []
        inner_r = max(1.0, radius * 0.55)
        for i, v in enumerate(values):
            cx = xs[i]
            cy = y(v)
            dots.append(
                f'<g>'
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius:.1f}" '
                f'fill="{color}" fill-opacity="0.75" filter="url(#dot-glow)" '
                f'style="mix-blend-mode:plus-lighter" />'
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{inner_r:.1f}" '
                f'fill="rgba(248,255,248,0.65)" style="mix-blend-mode:plus-lighter" />'
                f'</g>'
            )
        return "\n          ".join(dots)

    # Axes + grid
    grid_lines = ""
    for frac in (0.25, 0.5, 0.75, 1.0):
        yy = pad_top + inner_h * (1 - frac)
        val = int(max_y * frac)
        grid_lines += (
            f'<line x1="{pad_left}" y1="{yy:.1f}" x2="{plot_right}" y2="{yy:.1f}" '
            f'stroke="rgba(180,255,176,0.12)" stroke-width="1" />'
            f'<text x="8" y="{yy + 4:.1f}">{val}</text>'
        )

    x_labels = ""
    for i, lab in enumerate(labels):
        if not lab:
            continue
        x_labels += f'<text x="{xs[i]:.1f}" y="{height - 12}" text-anchor="middle">{lab}</text>'

    run_count_label = (
        f'<g>'
        f'<rect x="{pad_left + 4}" y="{pad_top + 2}" width="88" height="20" '
        f'fill="rgba(2,7,3,0.7)" stroke="rgba(180,255,176,0.25)" rx="4" />'
        f'<text x="{pad_left + 10}" y="{pad_top + 16}" '
        f'text-anchor="start" fill="rgba(180,255,176,0.8)" font-size="14">'
        f'Runs: {n}</text>'
        f'</g>'
    )

    # Tiny mascots "chasing" along their respective lines, placed in right gutter.
    # Keep x aligned to save horizontal space, adjust y to avoid overlap/clipping.
    img_w = 34
    img_h = 34
    mascot_x = min(plot_right + 8, width - pad_right - img_w)

    def _clamp_img_y(v: float) -> float:
        return min(max(v, pad_top), height - pad_bottom - img_h)

    funks_y = _clamp_img_y(y(totals[-1]) - img_h / 2)
    sausage_y = _clamp_img_y(y(passed[-1]) - img_h / 2)
    # If they would overlap vertically, nudge sausage down/up within bounds.
    if abs(sausage_y - funks_y) < img_h * 0.9:
        down = _clamp_img_y(funks_y + img_h * 0.95)
        up = _clamp_img_y(funks_y - img_h * 0.95)
        sausage_y = down if abs(down - funks_y) >= img_h * 0.9 else up
    funktion_img = (
        f'<image href="funktion-1.jpeg" x="{mascot_x:.1f}" y="{funks_y:.1f}" '
        f'width="{img_w}" height="{img_h}" preserveAspectRatio="xMidYMid meet" '
        f'opacity="0.9" filter="url(#dot-glow)" style="mix-blend-mode:screen" />'
    )
    sausage_img = (
        f'<image href="happy.jpg" x="{mascot_x:.1f}" y="{sausage_y:.1f}" '
        f'width="{img_w}" height="{img_h}" preserveAspectRatio="xMidYMid meet" '
        f'opacity="0.9" filter="url(#dot-glow)" style="mix-blend-mode:screen" />'
    )

    line_svg = f"""
      <div class="chart">
        <svg viewBox="0 0 {width} {height}" preserveAspectRatio="none">
          <defs>
            <!-- Hot CRT/laser-style bloom -->
            <filter id="line-glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur in="SourceGraphic" stdDeviation="1.8" result="blur1"/>
              <feGaussianBlur in="SourceGraphic" stdDeviation="0.7" result="blur2"/>
              <feColorMatrix in="blur1" type="matrix" values="
                1 0 0 0 0
                0 1 0 0 0
                0 0 1 0 0
                0 0 0 4.0 0" result="glow1"/>
              <feColorMatrix in="blur2" type="matrix" values="
                1 0 0 0 0
                0 1 0 0 0
                0 0 1 0 0
                0 0 0 3.0 0" result="glow2"/>
              <feMerge>
                <feMergeNode in="glow1"/>
                <feMergeNode in="glow2"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
            <!-- Tighter glow for dots so they don't smear -->
            <filter id="dot-glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur in="SourceGraphic" stdDeviation="1.0" result="blur1"/>
              <feGaussianBlur in="SourceGraphic" stdDeviation="0.4" result="blur2"/>
              <feColorMatrix in="blur1" type="matrix" values="
                1 0 0 0 0
                0 1 0 0 0
                0 0 1 0 0
                0 0 0 3.6 0" result="glow1"/>
              <feColorMatrix in="blur2" type="matrix" values="
                1 0 0 0 0
                0 1 0 0 0
                0 0 1 0 0
                0 0 0 2.6 0" result="glow2"/>
              <feMerge>
                <feMergeNode in="glow1"/>
                <feMergeNode in="glow2"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
          </defs>
          {grid_lines}
          <line x1="{pad_left}" y1="{pad_top + inner_h:.1f}" x2="{plot_right}" y2="{pad_top + inner_h:.1f}"
                stroke="rgba(180,255,176,0.35)" stroke-width="1.5" />
          <line x1="{pad_left}" y1="{pad_top}" x2="{pad_left}" y2="{pad_top + inner_h:.1f}"
                stroke="rgba(180,255,176,0.35)" stroke-width="1.5" />
          {polyline(totals, "#6b7280", width=2.0, dash="6 4")}
          {markers(totals, "#6b7280", radius=2.4)}
          {polyline(errors, "rgba(250,204,21,0.6)", width=2.0)}
          {markers(errors, "rgba(250,204,21,0.6)", radius=2.6)}
          {polyline(passed, "#16a34a", width=3.0)}
          {markers(passed, "#16a34a", radius=3.2)}
          {polyline(failed, "#dc2626", width=3.0)}
          {markers(failed, "#dc2626", radius=3.2)}
          {sausage_img}
          {funktion_img}
          {run_count_label}
          {x_labels}
        </svg>
        <div class="legend">
          <span><span class="legend-swatch" style="background:#6b7280"></span>Total tests</span>
          <span><span class="legend-swatch" style="background:#16a34a"></span>Passed</span>
          <span><span class="legend-swatch" style="background:#dc2626"></span>Failed</span>
          <span><span class="legend-swatch" style="background:rgba(250,204,21,0.6)"></span>Errors</span>
        </div>
      </div>
    """
    return f'<div class="chart-container">{line_svg}</div>'


def _build_main_panel(summary: dict, history: list[dict] | None = None) -> str:
    """Build the main pytest results panel HTML."""
    status = summary.get("status", "unknown")
    pass_count = _as_int(summary.get("passed"))
    fail_count = _as_int(summary.get("failed"))
    error_count = _as_int(summary.get("errors"))
    skip_count = _as_int(summary.get("skipped"))
    xfailed_count = _as_int(summary.get("xfailed"))
    xpassed_count = _as_int(summary.get("xpassed"))

    tests = _as_int(summary.get("tests"))
    inferred_total = (
        pass_count + fail_count + error_count + skip_count
        + xfailed_count + xpassed_count
    )
    total = tests or inferred_total or 1

    # Test result segments with colors
    segments = [
        ("Passed", pass_count, "#16a34a"),
        ("Failed", fail_count, "#dc2626"),
        ("Errors", error_count, "#facc15"),
        ("Unexpected passes", xpassed_count, "#f97316"),
        ("Expected failures", xfailed_count, "#8b5cf6"),
        ("Skipped", skip_count, "#6b7280")
    ]

    # Build summary list items
    summary_items = "".join(
        f"<li><span class='label'>{label}:</span> <span class='count'>{count}</span></li>"
        for label, count, _ in segments
    )

    # Commit metadata
    run_url = summary.get("run_url", "")
    commit_time = summary.get("commit_time", "unknown")
    commit_message = (summary.get("commit_message") or "unknown").strip()
    commit_author = summary.get("commit_author", "unknown")

    charts_html = _build_trend_charts(history or [])

    content = f"""        <div class="status ghost">
          <div class="status__left">Run status: <span class="pill">{status}</span></div>
          <div class="status__right">Total tests: {total}</div>
        </div>
        {charts_html}
        <ul class="ghost">{summary_items}</ul>
        <div class="meta-container ghost">
          <div class="meta">Run: <a href="{run_url}">{run_url}</a></div>
          <div class="meta">Commit time: {commit_time}</div>
          <div class="meta">Commit message: {commit_message}</div>
          <div class="meta">Commit author: {commit_author}</div>
        </div>"""

    return _build_panel(content, "main")


def _build_failing_files_panel(failing_files: list[tuple[str, int]]) -> str:
    """Build the failing files sidebar panel HTML."""
    if not failing_files:
        return ""

    def _short_path(path: str) -> str:
        parts = path.split("/")
        return "/".join(parts[-3:]) if len(parts) > 3 else path

    items = "".join(
        f'<li><span class="file-count">{count}</span><span class="file-path">{_short_path(file_path)}</span></li>'
        for file_path, count in failing_files
    )

    content = f"""        <h2 class="ghost">Failing Files</h2>
        <div class="meta ghost">{len(failing_files)} files with failures</div>
        <ul class="failing-files-list ghost">{items}</ul>"""

    return "\n    " + _build_panel(content, "sidebar")


def _build_page_template(css: str, main_panel: str, sidebar: str) -> str:
    """Assemble the complete HTML page from components."""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Pytest results</title>
  <style>{css}
  </style>
</head>
<body>
  <div class="scanlines"></div>
  <div class="noise"></div>
  <div class="dashboard-layout">
    {main_panel}{sidebar}
  </div>
</body>
</html>
"""


# =============================================================================
# PUBLIC API
# =============================================================================


def build_html(
    summary: dict,
    history: list[dict] | None = None,
    failing_files: list[tuple[str, int]] | None = None,
) -> str:
    """Build the complete dashboard HTML from latest summary, history, and failing files."""
    css = _get_dashboard_css()
    main_panel = _build_main_panel(summary, history=history)
    sidebar = _build_failing_files_panel(failing_files or [])
    return _build_page_template(css, main_panel, sidebar)


def open_in_browser(file_path: Path, browser_cmd: str | None = None) -> None:
    file_path = file_path.resolve()
    cmd = browser_cmd or BROWSER_CMD
    try:
        subprocess.Popen([cmd, file_path.as_uri()])
        print(f"Opened via '{cmd}': {file_path}")
        return
    except FileNotFoundError:
        print(f"Browser command not found: {cmd}")
    # Fallback to python webbrowser (uses xdg-open on most desktops)
    if webbrowser.open_new_tab(file_path.as_uri()):
        print(f"Opened in browser: {file_path}")
    else:
        print(f"Dashboard ready at {file_path} (open manually)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch latest pytest summary artifact and view it.")
    parser.add_argument("--branch", default=DEFAULT_BRANCH, help=f"Branch to monitor (default: {DEFAULT_BRANCH})")
    parser.add_argument("--interval", type=int, default=POLL_SECONDS, help=f"Polling interval seconds (default: {POLL_SECONDS})")
    parser.add_argument(
        "--workflow",
        default=WORKFLOW_FILENAME,
        help=f"Workflow filename to read runs from (default: {WORKFLOW_FILENAME}); use 'all' for any workflow",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=DEFAULT_RECENT_RUNS,
        help=f"Maximum number of recent completed runs to consider (default: {DEFAULT_RECENT_RUNS})",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_DAYS_BACK,
        help=f"Only include runs from the last N days (default: {DEFAULT_DAYS_BACK})",
    )
    parser.add_argument(
        "--output-dir",
        default=str(SCRIPT_DIR),
        help=f"Directory to store the latest dashboard file (default: {SCRIPT_DIR})",
    )
    parser.add_argument("--debug", action="store_true", help="Print run filtering debug info each poll")
    args = parser.parse_args()

    repo = DEFAULT_REPO

    token = os.getenv("GH_TOKEN")
    if not token:
        print("GH_TOKEN environment variable is required", file=sys.stderr)
        return 1

    workflow_filename = None if str(args.workflow).lower() in {"all", "*", "any"} else args.workflow
    print(
        f"Watching {repo} workflow={workflow_filename or '<all workflows>'} branch={args.branch} "
        f"(polling last {args.days} days, capped at {args.runs} runs)"
    )
    opened_once = False
    first_poll = True
    while True:
        try:
            runs = get_runs_within_window(
                repo,
                args.branch,
                token,
                max_runs=args.runs,
                days_back=args.days,
                status="completed",
                workflow_filename=workflow_filename,
                debug=args.debug,
            )
            if not runs:
                print("No completed runs yet; waiting...")
            else:
                latest_run = runs[0]
                html_url = latest_run.get("html_url")
                print(f"Refreshing latest completed run: {html_url}")

                out_dir = Path(args.output_dir).resolve()
                out_dir.mkdir(parents=True, exist_ok=True)
                cache = _load_cache(out_dir)

                # Always fetch latest for failing-files panel + fresh summary
                latest_summary, latest_html = _fetch_summary_for_run(repo, latest_run, token)
                if not latest_summary or not latest_html:
                    print("No test-report artifact found for latest run.")
                    continue

                failing_files = parse_failing_tests_by_file(latest_html)

                cache[str(latest_run["id"])] = latest_summary

                # Build history for charts, oldest->newest.
                # Cache entries may be either a parsed summary dict or {"_missing": True}.
                history: list[dict] = []
                missing_runs: list[dict] = []
                for run in reversed(runs):
                    run_id = run.get("id")
                    if not run_id:
                        continue
                    cached = cache.get(str(run_id))
                    if cached:
                        if not cached.get("_missing"):
                            history.append(cached)
                        continue
                    missing_runs.append(run)

                # Backfill missing runs in parallel.
                # On first poll this fills the full window; later polls usually only fetch new runs.
                if missing_runs:
                    to_fetch = missing_runs
                    if args.debug:
                        phase = "initial backfill" if first_poll else "backfilling"
                        print(f"Debug: {phase} {len(to_fetch)} missing artifacts")
                    with ThreadPoolExecutor(max_workers=4) as pool:
                        future_map = {
                            pool.submit(_fetch_summary_for_run, repo, run, token): run
                            for run in to_fetch
                        }
                        for fut in as_completed(future_map):
                            run = future_map[fut]
                            run_id = run.get("id")
                            try:
                                summary, _ = fut.result()
                            except Exception:
                                summary = None
                            if run_id:
                                if summary:
                                    cache[str(run_id)] = summary
                                    history.append(summary)
                                else:
                                    cache[str(run_id)] = {
                                        "_missing": True,
                                        "checked_at": datetime.now(timezone.utc).isoformat(),
                                    }

                # Rebuild history from cache to ensure ordering and inclusion of newly fetched items.
                history = []
                for run in reversed(runs):
                    run_id = run.get("id")
                    if not run_id:
                        continue
                    cached = cache.get(str(run_id))
                    if cached and not cached.get("_missing"):
                        history.append(cached)

                _save_cache(out_dir, cache)

                # Keep a copy of the latest full report for drill-down
                summary_copy = out_dir / REPORT_COPY_BASENAME
                summary_copy.write_text(latest_html, encoding="utf-8")

                html = build_html(latest_summary, history=history, failing_files=failing_files)
                dest = out_dir / "dashboard.html"
                dest.write_text(html, encoding="utf-8")
                inject_refresh(dest, args.interval)
                if not opened_once:
                    open_in_browser(dest, None)
                    opened_once = True
                else:
                    print(f"Dashboard updated at {dest} (refresh existing tab).")
                first_poll = False
        except Exception as exc:  # pragma: no cover - convenience loop
            print(f"Error: {exc}", file=sys.stderr)

        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
