#!/usr/bin/env python3
"""
Fetch and display pytest summaries from recent GitHub Actions runs.

Polls a workflow on a branch, downloads the "test-report" artifact,
parses summary counts from `test-report.json`, and renders a CRT-style local HTML
dashboard with a multi-run trend chart.

Requirements:
- Python 3.8+
- GH_TOKEN env var with "repo" or "public_repo" scope.

Usage:
  GH_TOKEN=... python scripts/dashboards/fetch_dashboard.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo


REPO = "atopile/atopile"
WORKFLOW_FILENAME = "pytest.yml"
WORKFLOW_NAME = "pytest"
BRANCH = "feature/fabll_part2"

REPORT_ARTIFACT_NAME = "test-report"
REPORT_JSON_BASENAME = "test-report.json"
REPORT_COPY_BASENAME = REPORT_JSON_BASENAME

RECENT_RUNS = 50
POLL_SECONDS = 30
OUTPUT_DIR = Path(__file__).resolve().parent
BROWSER_CMD = "chromium-browser"


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


def get_recent_completed_runs(
    repo: str,
    branch: str,
    token: str,
    *,
    workflow_filename: str | None,
    max_runs: int,
) -> list[dict]:
    max_runs = max(1, max_runs)
    collected: list[dict] = []
    page = 1
    per_page = min(100, max_runs)
    while len(collected) < max_runs and page <= 10:
        runs_page = get_recent_runs_page(
            repo,
            branch,
            token,
            workflow_filename=workflow_filename,
            per_page=per_page,
            page=page,
            status="completed",
        )
        if not runs_page:
            break
        collected.extend(runs_page)
        if len(runs_page) < per_page:
            break
        page += 1
    return collected[:max_runs]


def list_run_artifacts(repo: str, run_id: int, token: str) -> list[dict]:
    artifacts: list[dict] = []
    page = 1
    per_page = 100
    while page <= 10:
        url = (
            f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/artifacts"
            f"?per_page={per_page}&page={page}"
        )
        data = json.loads(gh_request(url, token))
        items = data.get("artifacts", []) or []
        artifacts.extend(a for a in items if isinstance(a, dict))
        if len(items) < per_page:
            break
        page += 1
    return artifacts


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


def extract_artifact_member(
    zip_path: Path,
    dest_dir: Path,
    suffixes: tuple[str, ...],
    *,
    basenames: tuple[str, ...] | None = None,
) -> Path | None:
    suffixes = tuple(s.lower() for s in suffixes)
    basenames_norm = tuple(b.lower() for b in basenames) if basenames else None
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.namelist():
            if member.lower().endswith(suffixes):
                if basenames_norm and Path(member).name.lower() not in basenames_norm:
                    continue
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


def parse_test_report_summary(report: dict) -> dict[str, object]:
    summary = (report.get("summary") or {}) if isinstance(report, dict) else {}
    errors = _as_int(summary.get("errors"))
    crashed = _as_int(summary.get("crashed"))
    return {
        "passed": _as_int(summary.get("passed")),
        "failed": _as_int(summary.get("failed")),
        "errors": errors,
        "crashed": crashed,
        "skipped": _as_int(summary.get("skipped")),
        "tests": _as_int(summary.get("total")),
        "total_duration": summary.get("total_duration", 0.0) or 0.0,
        "workers_used": _as_int(summary.get("workers_used")),
    }


def parse_failing_files_from_test_report(report: dict) -> list[tuple[str, int]]:
    tests = report.get("tests") if isinstance(report, dict) else None
    if not isinstance(tests, list):
        return []

    file_counts: dict[str, int] = {}
    for test in tests:
        if not isinstance(test, dict):
            continue
        outcome = str(test.get("outcome") or "").lower()
        if outcome not in {"failed", "error", "crashed"}:
            continue
        file_path = test.get("file") or ""
        if not file_path:
            nodeid = str(test.get("nodeid") or "")
            file_path = nodeid.split("::")[0] if nodeid else ""
        if not file_path:
            continue
        file_counts[file_path] = file_counts.get(file_path, 0) + 1

    return sorted(file_counts.items(), key=lambda x: (-x[1], x[0]))


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


def build_dashboard_summary(*, run: dict, report: dict) -> dict[str, object]:
    """
    Normalize a single run into the dict expected by the existing dashboard UI.
    """
    out: dict[str, object] = {}
    out.update(parse_test_report_summary(report))

    status = run.get("conclusion") or run.get("status") or "unknown"
    out["status"] = status
    out["run_url"] = run.get("html_url") or ""

    run_time_iso = run.get("run_started_at") or run.get("created_at") or run.get("updated_at") or ""
    out["run_time_iso"] = run_time_iso

    head_commit = run.get("head_commit") or {}
    commit_time_iso = head_commit.get("timestamp") or run.get("updated_at") or run.get("created_at") or ""
    out["commit_time_iso"] = commit_time_iso
    out["commit_time"] = format_commit_time(commit_time_iso) if commit_time_iso else "unknown"

    commit = report.get("commit") if isinstance(report, dict) else None
    if not isinstance(commit, dict):
        commit = {}
    out["commit_message"] = (commit.get("message") or head_commit.get("message") or "").strip() or "unknown"
    out["commit_short_hash"] = (commit.get("short_hash") or "").strip()
    out["commit_author"] = (
        commit.get("author")
        or (head_commit.get("author") or {}).get("name")
        or (head_commit.get("author") or {}).get("email")
        or (head_commit.get("committer") or {}).get("name")
        or (head_commit.get("committer") or {}).get("email")
        or "unknown"
    )
    return out


def fetch_test_report_for_run(repo: str, run: dict, token: str) -> dict | None:
    run_id = run.get("id")
    if not run_id:
        return None

    artifacts = list_run_artifacts(repo, run_id, token)
    if not artifacts:
        return None

    # Prefer the expected artifact name, but ultimately search all artifacts.
    def _prio(a: dict) -> tuple[int, str]:
        name = str(a.get("name") or "")
        return (0 if name == REPORT_ARTIFACT_NAME else 1, name)

    for artifact in sorted(artifacts, key=_prio):
        if artifact.get("expired"):
            continue
        artifact_url = artifact.get("archive_download_url")
        if not artifact_url:
            continue
        with TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "artifact.zip"
            try:
                download_artifact_zip(str(artifact_url), token, zip_path)
            except Exception:
                continue
            artifact_member = extract_artifact_member(
                zip_path,
                Path(tmpdir),
                (".json",),
                basenames=(REPORT_JSON_BASENAME,),
            )
            if not artifact_member:
                continue
            try:
                return json.loads(artifact_member.read_text(encoding="utf-8"))
            except Exception:
                continue
    return None


def _run_id(run: dict) -> int | None:
    run_id = run.get("id")
    return run_id if isinstance(run_id, int) else None


def _run_sha(run: dict) -> str | None:
    sha = run.get("head_sha")
    if not isinstance(sha, str):
        return None
    sha = sha.strip()
    return sha or None


def _reports_cache_dir(out_dir: Path) -> Path:
    return out_dir / "reports"


def _cached_report_path(out_dir: Path, key: str) -> Path:
    return _reports_cache_dir(out_dir) / f"{key}.json"


def _missing_marker_path(out_dir: Path, key: str) -> Path:
    return _reports_cache_dir(out_dir) / f"{key}.missing"


def _load_cached_report(out_dir: Path, key: str) -> dict | None:
    report_path = _cached_report_path(out_dir, key)
    if not report_path.exists():
        return None
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _write_cached_report(out_dir: Path, key: str, report: dict) -> None:
    cache_dir = _reports_cache_dir(out_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    report_path = _cached_report_path(out_dir, key)
    tmp_path = report_path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    tmp_path.replace(report_path)
    missing_path = _missing_marker_path(out_dir, key)
    if missing_path.exists():
        try:
            missing_path.unlink()
        except Exception:
            pass


def _mark_report_missing(out_dir: Path, key: str) -> None:
    cache_dir = _reports_cache_dir(out_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    missing_path = _missing_marker_path(out_dir, key)
    if not missing_path.exists():
        missing_path.write_text("", encoding="utf-8")


def refresh_dashboard_once(
    *,
    repo: str,
    branch: str,
    token: str,
    workflow_filename: str | None,
    max_runs: int,
    interval_seconds: int,
    out_dir: Path,
    debug: bool,
) -> Path | None:
    runs = get_recent_completed_runs(
        repo,
        branch,
        token,
        workflow_filename=workflow_filename,
        max_runs=max_runs,
    )
    if not runs:
        print("No completed runs yet; waiting...")
        return None

    out_dir.mkdir(parents=True, exist_ok=True)
    _reports_cache_dir(out_dir).mkdir(parents=True, exist_ok=True)

    # Only fetch reports for commits we haven't downloaded yet.
    # Cache key is commit hash (prefer run.head_sha; fallback to run.id for odd cases).
    to_fetch: list[tuple[int, dict, str]] = []
    cached: list[tuple[int, dict, dict]] = []
    for i, run in enumerate(runs):
        run_id = _run_id(run)
        sha = _run_sha(run)
        key = sha or (str(run_id) if run_id is not None else None)
        if not key:
            continue

        # Migrate legacy run-id based cache files to sha-based names when possible.
        if sha and run_id is not None:
            legacy_json = _cached_report_path(out_dir, str(run_id))
            legacy_missing = _missing_marker_path(out_dir, str(run_id))
            sha_json = _cached_report_path(out_dir, sha)
            sha_missing = _missing_marker_path(out_dir, sha)
            if legacy_json.exists() and not sha_json.exists():
                try:
                    legacy_json.replace(sha_json)
                except Exception:
                    pass
            if legacy_missing.exists() and not sha_missing.exists():
                try:
                    legacy_missing.replace(sha_missing)
                except Exception:
                    pass

        if _cached_report_path(out_dir, key).exists():
            report = _load_cached_report(out_dir, key)
            if report:
                cached.append((i, run, report))
            else:
                # corrupted cache file -> re-fetch
                to_fetch.append((i, run, key))
            continue
        if _missing_marker_path(out_dir, key).exists():
            continue
        to_fetch.append((i, run, key))

    fetched: list[tuple[int, dict, dict]] = []
    if to_fetch:
        max_workers = min(16, max(4, len(to_fetch)))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            future_map = {
                pool.submit(fetch_test_report_for_run, repo, run, token): (i, run, key)
                for i, run, key in to_fetch
            }
            for fut in as_completed(future_map):
                i, run, key = future_map[fut]
                try:
                    report = fut.result()
                except Exception:
                    report = None
                if report:
                    report_key = key
                    commit = report.get("commit") if isinstance(report, dict) else None
                    if isinstance(commit, dict):
                        commit_hash = commit.get("hash")
                        if isinstance(commit_hash, str) and commit_hash.strip():
                            report_key = commit_hash.strip()
                    _write_cached_report(out_dir, report_key, report)
                    fetched.append((i, run, report))
                else:
                    _mark_report_missing(out_dir, key)

    available = cached + fetched
    if not available:
        print(
            f"No {REPORT_JSON_BASENAME} found in last {len(runs)} workflow runs "
            f"(downloaded {len(to_fetch)} new runs)."
        )
        return None

    # runs are newest->oldest (index 0 is newest).
    summaries: list[tuple[int, dict, dict, dict]] = []
    for i, run, report in available:
        summary = build_dashboard_summary(run=run, report=report)
        summaries.append((i, run, report, summary))

    # Display the newest run that has a report JSON (fallback handled above).
    summaries_by_newest = sorted(summaries, key=lambda t: t[0])
    display_i, display_run, display_report, display_summary = summaries_by_newest[0]
    prev = summaries_by_newest[1] if len(summaries_by_newest) > 1 else None
    if prev:
        _prev_summary = prev[3]
        display_summary = dict(display_summary)
        display_summary["passed_delta"] = _as_int(display_summary.get("passed")) - _as_int(_prev_summary.get("passed"))
        display_summary["failed_delta"] = _as_int(display_summary.get("failed")) - _as_int(_prev_summary.get("failed"))
    display_label = "latest run with report"

    html_url = display_run.get("html_url")
    print(
        f"Refreshing {display_label} with report: {html_url} "
        f"(cached {len(cached)}, downloaded {len(fetched)}/{len(to_fetch)}, total {len(available)}/{len(runs)})"
    )

    # History is oldest->newest for the chart.
    history: list[dict] = []
    for i, run, report, summary in sorted(summaries, key=lambda t: t[0], reverse=True):
        history.append(display_summary if i == display_i else summary)

    failing_files = parse_failing_files_from_test_report(display_report)
    (out_dir / REPORT_COPY_BASENAME).write_text(
        json.dumps(display_report, indent=2, sort_keys=True), encoding="utf-8"
    )
    html = build_html(display_summary, history=history, failing_files=failing_files)
    dest = out_dir / "dashboard.html"
    dest.write_text(html, encoding="utf-8")
    inject_refresh(dest, interval_seconds)
    return dest


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
      font-size: 1.6rem;
      margin-bottom: 16px;
      display: flex;
      align-items: center;
      gap: 12px;
      justify-content: space-between;
      width: 100%;
    }
    .status__left { display: inline-flex; align-items: center; gap: 12px; }
    .status__label { color: var(--muted); font-weight: 700; }
    .status__meta { display: inline-flex; align-items: center; gap: 16px; }
    .status__kv { display: inline-flex; align-items: center; gap: 8px; }
    .status__k { color: var(--muted); font-weight: 700; }
    .status__v { color: var(--accent); font-weight: 800; }
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
      font-size: 1.5rem;
      display: flex;
      align-items: center; /* vertical centering */
      justify-content: space-between;
      gap: 12px;
    }
    .metric__label { color: var(--muted); font-weight: 700; }
    .metric__value { display: inline-flex; align-items: center; gap: 8px; }
    .metric__count { color: var(--accent); font-weight: 800; }
    .metric__delta { font-weight: 800; opacity: 0.9; }
    .metric__delta--good { color: var(--accent); }
    .metric__delta--bad { color: var(--danger); }
    .metric__delta--neutral { color: var(--muted); }
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
	    .chart svg { width: 100%; height: 343px; display: block; }
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
                + _as_int(h.get("crashed"))
                + _as_int(h.get("skipped"))
            )
        totals.append(max(t, 0))

    # Build x-axis labels based on commit, not time.
    labels: list[str] = []
    n = len(history)
    label_step = max(1, n // 6)
    for i, h in enumerate(history):
        short_hash = str(h.get("commit_short_hash") or "")
        if not short_hash:
            labels.append("")
            continue
        if i == 0 or i == n - 1 or (i % label_step) == 0:
            labels.append(short_hash)
        else:
            labels.append("")

    max_y = max(passed + failed + errors + totals + [1])

    width = 900
    height = int(220 * 1.56)
    pad_left, pad_right, pad_top, pad_bottom = 48, 12, 12, 40
    mascot_gutter = 84  # reserved space on right for mascots
    plot_right = width - pad_right - mascot_gutter
    inner_w = plot_right - pad_left
    inner_h = height - pad_top - pad_bottom

    def y(v: int) -> float:
        return pad_top + inner_h * (1 - (v / max_y))

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
    crashed_count = _as_int(summary.get("crashed"))
    skip_count = _as_int(summary.get("skipped"))

    tests = _as_int(summary.get("tests"))
    inferred_total = (
        pass_count + fail_count + error_count + crashed_count + skip_count
    )
    total = tests or inferred_total or 1
    run_count = len(history) if history else 1

    # Test result segments with colors
    segments = [
        ("Passed", pass_count, "#16a34a"),
        ("Failed", fail_count, "#dc2626"),
        ("Errors", error_count, "#facc15"),
        ("Crashed", crashed_count, "#f97316"),
        ("Skipped", skip_count, "#6b7280")
    ]

    def _delta_for(label: str) -> int | None:
        if label == "Passed":
            delta = summary.get("passed_delta")
        elif label == "Failed":
            delta = summary.get("failed_delta")
        else:
            return None
        return int(delta) if isinstance(delta, int) else None

    def _delta_span(label: str, delta: int | None) -> str:
        if delta is None:
            return ""
        text = f"[{delta:+d}]"
        if delta == 0:
            cls = "metric__delta metric__delta--neutral"
        else:
            is_good = (label == "Passed" and delta > 0) or (label == "Failed" and delta < 0)
            is_bad = (label == "Passed" and delta < 0) or (label == "Failed" and delta > 0)
            cls = (
                "metric__delta metric__delta--good"
                if is_good
                else "metric__delta metric__delta--bad"
                if is_bad
                else "metric__delta metric__delta--neutral"
            )
        return f"<span class='{cls}' title='Δ vs previous report-backed run'>{text}</span>"

    def _metric_row(label: str, count: int, delta: int | None) -> str:
        return (
            "<li>"
            f"<span class='metric__label'>{label}:</span>"
            "<span class='metric__value'>"
            f"{_delta_span(label, delta)}"
            f"<span class='metric__count'>{count}</span>"
            "</span>"
            "</li>"
        )

    # Build summary list items
    summary_items = "".join(
        _metric_row(label, count, _delta_for(label)) for label, count, _color in segments
    )

    # Commit metadata
    run_url = summary.get("run_url", "")
    commit_time = summary.get("commit_time", "unknown")
    commit_message = (summary.get("commit_message") or "unknown").strip()
    commit_author = summary.get("commit_author", "unknown")

    charts_html = _build_trend_charts(history or [])

    content = f"""        <div class="status ghost">
          <div class="status__left">
            <span class="status__label">Run status:</span>
            <span class="pill">{status}</span>
          </div>
          <div class="status__meta">
            <div class="status__kv"><span class="status__k">Total tests:</span> <span class="status__v">{total}</span></div>
            <div class="status__kv"><span class="status__k">Runs:</span> <span class="status__v">{run_count}</span></div>
          </div>
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
    token = os.getenv("GH_TOKEN")
    if not token:
        print("GH_TOKEN environment variable is required", file=sys.stderr)
        return 1

    print(
        f"Watching {REPO} workflow={WORKFLOW_FILENAME} ({WORKFLOW_NAME}) branch={BRANCH} "
        f"(checking last {RECENT_RUNS} workflow runs)"
    )
    opened_once = False
    while True:
        try:
            dest = refresh_dashboard_once(
                repo=REPO,
                branch=BRANCH,
                token=token,
                workflow_filename=WORKFLOW_FILENAME,
                max_runs=RECENT_RUNS,
                interval_seconds=POLL_SECONDS,
                out_dir=OUTPUT_DIR,
                debug=False,
            )
            if dest:
                if not opened_once:
                    open_in_browser(dest, None)
                    opened_once = True
                else:
                    print(f"Dashboard updated at {dest} (refresh existing tab).")
        except KeyboardInterrupt:
            return 0
        except Exception as exc:  # pragma: no cover - convenience loop
            print(f"Error: {exc}", file=sys.stderr)

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
