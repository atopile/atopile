#!/usr/bin/env python3
"""
Fetch and display the latest pytest summary artifact for a branch.

Designed for a Raspberry Pi or other always-on device. Polls GitHub for new
runs on a branch, downloads the "test-report" artifact (pytest-html), parses the
summary counts, renders them to HTML locally, and opens the output in a browser
whenever a new run appears.

Requirements:
- Python 3.8+
- Environment variable GH_TOKEN set to a GitHub token with "repo" (or public_repo)

Usage:
  GH_TOKEN=... python scripts/dashboards/fetch_dashboard.py --repo atopile/atopile --branch main
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
import zipfile
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo


WORKFLOW_FILENAME = "pytest.yml"  # GitHub workflow file name
REPORT_ARTIFACT_NAME = "test-report"
REPORT_COPY_BASENAME = "test-report.html"
POLL_SECONDS = 60
BROWSER_CMD = "chromium-browser"
DEFAULT_REPO = "atopile/atopile"
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


def get_latest_run(repo: str, branch: str, token: str, status: str | None = None) -> dict | None:
    url = (
        f"https://api.github.com/repos/{repo}/actions/workflows/"
        f"{WORKFLOW_FILENAME}/runs?branch={urllib.parse.quote(branch)}&per_page=1"
    )
    if status:
        url += f"&status={urllib.parse.quote(status)}"
    data = json.loads(gh_request(url, token))
    runs = data.get("workflow_runs", [])
    return runs[0] if runs else None


def get_artifact_download_url(repo: str, run_id: int, token: str) -> str | None:
    url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/artifacts"
    data = json.loads(gh_request(url, token))
    artifacts = data.get("artifacts", [])
    for artifact in artifacts:
        if artifact.get("name") == REPORT_ARTIFACT_NAME:
            download_url = artifact.get("archive_download_url")
            if download_url:
                return download_url
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
        "rerun": 0,
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
        "rerun": "rerun",
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
        summary["tests"] = sum(summary[k] for k in ("passed", "failed", "errors", "skipped", "xfailed", "xpassed", "rerun"))

    return summary


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

    commit_time = (
        head_commit.get("timestamp")
        or run.get("updated_at")
        or run.get("created_at")
    )
    if commit_time:
        summary["commit_time"] = format_commit_time(commit_time)
    if "commit_time" not in summary:
        summary["commit_time"] = "unknown"

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


def build_html(summary: dict) -> str:
    status = summary.get("status", "unknown")
    pass_count = _as_int(summary.get("passed"))
    fail_count = _as_int(summary.get("failed"))
    error_count = _as_int(summary.get("errors"))
    skip_count = _as_int(summary.get("skipped"))
    xfailed_count = _as_int(summary.get("xfailed"))
    xpassed_count = _as_int(summary.get("xpassed"))
    rerun_count = _as_int(summary.get("rerun"))

    tests = _as_int(summary.get("tests"))
    inferred_total = (
        pass_count
        + fail_count
        + error_count
        + skip_count
        + xfailed_count
        + xpassed_count
        + rerun_count
    )
    total = tests or inferred_total or 1

    segments = [
        ("Passed", pass_count, "#16a34a"),
        ("Failed", fail_count, "#dc2626"),
        ("Errors", error_count, "#b91c1c"),
        ("Unexpected passes", xpassed_count, "#f97316"),
        ("Expected failures", xfailed_count, "#8b5cf6"),
        ("Skipped", skip_count, "#6b7280"),
        ("Rerun", rerun_count, "#0ea5e9"),
    ]

    def segment_html(label: str, count: int, color: str) -> str:
        if count <= 0:
            return ""
        pct = (count / total) * 100
        return f'<div class="seg" style="width:{pct:.1f}%;background:{color}" title="{label}: {count} ({pct:.1f}%)"></div>'

    bar_html = "".join(segment_html(*s) for s in segments if s[1] > 0)
    summary_items = "".join(
        f"<li><span class='label'>{label}:</span> <span class='count'>{count}</span></li>"
        for label, count, _ in segments
    )
    run_url = summary.get("run_url", "")

    commit_time = summary.get("commit_time", "unknown")
    commit_message = (summary.get("commit_message") or "unknown").strip()
    commit_author = summary.get("commit_author", "unknown")

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Pytest results</title>
  <style>
    body {{ font-family: Arial, sans-serif; font-size: 2rem; padding: 48px; max-width: 1440px; margin: auto; color: #e8ecff; background: #070a23; overflow-x: hidden; position: relative; }}
    h1 {{ margin-bottom: 16px; font-size: 3.4rem; position: relative; z-index: 2; }}
    .status {{ font-size: 2rem; margin-bottom: 32px; position: relative; z-index: 2; }}
    .pill {{ display: inline-block; padding: 8px 20px; border-radius: 9999px; font-weight: 600; font-size: 1.8rem; background: #f95015; color: #070a23; }}
    .bar-row {{ display: flex; align-items: center; gap: 32px; margin: 32px 0; position: relative; z-index: 2; }}
    .bar {{ flex: 1; display: flex; height: 48px; border-radius: 24px; overflow: hidden; background: #0f1335; box-shadow: inset 0 1px 2px rgba(0,0,0,0.2); }}
    .seg {{ height: 100%; }}
    ul {{ list-style: none; padding: 0; margin: 24px 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; position: relative; z-index: 2; }}
    li {{ background: rgba(15, 20, 51, 0.6); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); border-radius: 20px; padding: 20px 24px; box-shadow: 0 2px 6px rgba(0,0,0,0.3); font-size: 1.8rem; border: 1px solid rgba(203, 211, 255, 0.1); }}
    .label {{ color: #cbd3ff; }}
    .count {{ font-weight: 700; float: right; color: #ffffff; }}
    .meta-container {{ background: rgba(15, 20, 51, 0.6); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); border-radius: 20px; padding: 24px; margin-top: 32px; position: relative; z-index: 2; border: 1px solid rgba(203, 211, 255, 0.1); }}
    .meta {{ font-size: 1.8rem; margin-bottom: 16px; }}
    .meta:last-child {{ margin-bottom: 0; }}
    .meta a {{ color: #f95015; text-decoration: none; }}
    .mascot {{ width: 140px; max-width: 20%; height: auto; display: block; }}

    /* Laser Animation Styles */
    .laser-overlay {{
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
      z-index: 1;
      overflow: hidden;
    }}
    .laser {{
      position: absolute;
      height: 8px;
      width: 200vmax;
      background: linear-gradient(
        to right,
        currentColor 0%,
        currentColor 30%,
        transparent 100%
      );
      box-shadow: 
        0 0 40px 8px currentColor,
        0 0 80px 15px currentColor,
        0 0 120px 25px currentColor;
      opacity: 0.7;
      transform-origin: left center;
      border-radius: 50%;
    }}
    .laser-source {{
      position: absolute;
      width: 20px;
      height: 20px;
      border-radius: 50%;
      background: currentColor;
      box-shadow: 
        0 0 20px 5px currentColor,
        0 0 40px 10px currentColor;
      z-index: 2;
    }}

    /* Laser variations with visible origin points */
    .laser-1 {{
      top: 15%;
      left: 10%;
      color: #ff0055;
      animation: scan-1 5s ease-in-out infinite alternate;
    }}
    .source-1 {{
      top: 15%;
      left: 10%;
      color: #ff0055;
    }}
    .laser-2 {{
      top: 20%;
      right: 15%;
      left: auto;
      transform-origin: right center;
      color: #00ffaa;
      animation: scan-2 7s ease-in-out infinite alternate;
    }}
    .source-2 {{
      top: 20%;
      right: 15%;
      color: #00ffaa;
    }}
    .laser-3 {{
      bottom: 25%;
      left: 8%;
      top: auto;
      color: #00aaff;
      animation: scan-3 6s ease-in-out infinite alternate;
    }}
    .source-3 {{
      bottom: 25%;
      left: 8%;
      color: #00aaff;
    }}
    .laser-4 {{
      bottom: 20%;
      right: 12%;
      left: auto;
      top: auto;
      transform-origin: right center;
      color: #ffcc00;
      animation: scan-4 8s ease-in-out infinite alternate;
    }}
    .source-4 {{
      bottom: 20%;
      right: 12%;
      color: #ffcc00;
    }}
    .laser-5 {{
      top: 10%;
      left: 50%;
      transform-origin: left center;
      color: #aa00ff;
      animation: scan-5 9s ease-in-out infinite;
    }}
    .source-5 {{
      top: 10%;
      left: 50%;
      color: #aa00ff;
    }}

    @keyframes scan-1 {{
      0% {{ transform: rotate(20deg); opacity: 0; }}
      15% {{ opacity: 0.8; }}
      85% {{ opacity: 0.8; }}
      100% {{ transform: rotate(90deg); opacity: 0; }}
    }}
    @keyframes scan-2 {{
      0% {{ transform: rotate(-20deg); opacity: 0; }}
      15% {{ opacity: 0.8; }}
      85% {{ opacity: 0.8; }}
      100% {{ transform: rotate(-90deg); opacity: 0; }}
    }}
    @keyframes scan-3 {{
      0% {{ transform: rotate(-15deg); opacity: 0; }}
      15% {{ opacity: 0.8; }}
      85% {{ opacity: 0.8; }}
      100% {{ transform: rotate(-85deg); opacity: 0; }}
    }}
    @keyframes scan-4 {{
      0% {{ transform: rotate(15deg); opacity: 0; }}
      15% {{ opacity: 0.8; }}
      85% {{ opacity: 0.8; }}
      100% {{ transform: rotate(85deg); opacity: 0; }}
    }}
    @keyframes scan-5 {{
      0% {{ transform: translateX(-50%) rotate(30deg); opacity: 0; }}
      20% {{ opacity: 0.9; }}
      80% {{ opacity: 0.9; }}
      100% {{ transform: translateX(-50%) rotate(150deg); opacity: 0; }}
    }}

  </style>
</head>
<body>
  <div class="laser-overlay">
    <div class="laser-source source-1"></div>
    <div class="laser laser-1"></div>
    <div class="laser-source source-2"></div>
    <div class="laser laser-2"></div>
    <div class="laser-source source-3"></div>
    <div class="laser laser-3"></div>
    <div class="laser-source source-4"></div>
    <div class="laser laser-4"></div>
    <div class="laser-source source-5"></div>
    <div class="laser laser-5"></div>
  </div>
  <h1>Pytest Progress</h1>
  <div class="status">Run status: <span class="pill">{status}</span></div>
  <div class="meta">Total tests: {total}</div>
  <div class="bar-row">
    <img class="mascot" src="happy.jpg" alt="happy sausage" />
    <div class="bar">{bar_html or '<div class="seg" style="width:100%;background:#e5e7eb"></div>'}</div>
    <img class="mascot" src="angry.png" alt="angry sausage" />
  </div>
  <ul>{summary_items}</ul>
  <div class="meta-container">
    <div class="meta">Run: <a href="{run_url}">{run_url}</a></div>
    <div class="meta">Commit time: {commit_time}</div>
    <div class="meta">Commit message: {commit_message}</div>
    <div class="meta">Commit author: {commit_author}</div>
  </div>
</body>
</html>
"""
    return html


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
    parser.add_argument("--branch", default="main", help="Branch to monitor (default: main)")
    parser.add_argument("--interval", type=int, default=POLL_SECONDS, help="Polling interval seconds (default: 60)")
    parser.add_argument(
        "--output-dir",
        default=str(SCRIPT_DIR),
        help=f"Directory to store the latest dashboard file (default: {SCRIPT_DIR})",
    )
    args = parser.parse_args()

    repo = DEFAULT_REPO

    token = os.getenv("GH_TOKEN")
    if not token:
        print("GH_TOKEN environment variable is required", file=sys.stderr)
        return 1

    print(f"Watching {repo} workflow={WORKFLOW_FILENAME} branch={args.branch} (polling latest completed run)")
    opened_once = False
    while True:
        try:
            run = get_latest_run(repo, args.branch, token, status="completed")
            if not run:
                print("No completed runs yet; waiting...")
            else:
                run_id = run["id"]
                html_url = run.get("html_url")
                print(f"Refreshing latest completed run: {html_url}")
                artifact_url = get_artifact_download_url(repo, run_id, token)
                if not artifact_url:
                    print("No test-report artifact found for this run.")
                else:
                    with TemporaryDirectory() as tmpdir:
                        zip_path = Path(tmpdir) / "artifact.zip"
                        download_artifact_zip(artifact_url, token, zip_path)
                        artifact_member = extract_artifact_member(zip_path, Path(tmpdir), (".html", ".htm"))
                        if not artifact_member:
                            print("Artifact did not contain an HTML report.")
                            continue
                        try:
                            html_text = artifact_member.read_text(encoding="utf-8")
                            summary: dict[str, object] = parse_pytest_html_summary(html_text)
                        except Exception as exc:
                            print(f"Could not parse pytest HTML report: {exc}")
                            continue

                        inject_run_metadata(summary, run)

                        out_dir = Path(args.output_dir).resolve()
                        out_dir.mkdir(parents=True, exist_ok=True)

                        summary_copy = out_dir / REPORT_COPY_BASENAME
                        shutil.copy2(artifact_member, summary_copy)

                        html = build_html(summary)
                        dest = out_dir / "dashboard.html"
                        dest.write_text(html, encoding="utf-8")
                        inject_refresh(dest, args.interval)
                        if not opened_once:
                            open_in_browser(dest, None)
                            opened_once = True
                        else:
                            print(f"Dashboard updated at {dest} (refresh existing tab).")
        except Exception as exc:  # pragma: no cover - convenience loop
            print(f"Error: {exc}", file=sys.stderr)

        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
