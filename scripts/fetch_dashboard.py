#!/usr/bin/env python3
"""
Fetch and display the latest pytest dashboard artifact for a branch.

Designed for a Raspberry Pi or other always-on device. Polls GitHub for new
runs on a branch, downloads the "pytest-dashboard" artifact, and opens the
HTML in a browser whenever a new run appears.

Requirements:
- Python 3.8+
- Environment variable GH_TOKEN set to a GitHub token with "repo" (or public_repo)

Usage:
  GH_TOKEN=... python scripts/fetch_dashboard.py --repo atopile/atopile --branch main
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
import webbrowser
import shutil
import subprocess


WORKFLOW_FILENAME = "pytest.yml"  # GitHub workflow file name
ARTIFACT_NAME = "pytest-dashboard"
POLL_SECONDS = 60
BROWSER_CMD = "chromium-browser"
DEFAULT_REPO = "atopile/atopile"


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
    for artifact in data.get("artifacts", []):
        if artifact.get("name") == ARTIFACT_NAME:
            # archive_download_url is a signed redirect URL for the zip
            return artifact.get("archive_download_url")
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


def extract_dashboard(zip_path: Path, dest_dir: Path) -> Path | None:
    with zipfile.ZipFile(zip_path, "r") as zf:
        html_files = [n for n in zf.namelist() if n.endswith(".html")]
        if not html_files:
            return None
        zf.extract(html_files[0], path=dest_dir)
        return dest_dir / html_files[0]


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
    parser = argparse.ArgumentParser(description="Fetch latest pytest dashboard artifact and view it.")
    parser.add_argument("--branch", default="main", help="Branch to monitor (default: main)")
    parser.add_argument("--interval", type=int, default=POLL_SECONDS, help="Polling interval seconds (default: 60)")
    parser.add_argument("--output-dir", default="dashboards", help="Directory to store the latest dashboard file (default: dashboards/)")
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
                    print("No pytest-dashboard artifact found for this run.")
                else:
                    with TemporaryDirectory() as tmpdir:
                        zip_path = Path(tmpdir) / "artifact.zip"
                        download_artifact_zip(artifact_url, token, zip_path)
                        html_path = extract_dashboard(zip_path, Path(tmpdir))
                        if html_path:
                            out_dir = Path(args.output_dir).resolve()
                            out_dir.mkdir(parents=True, exist_ok=True)
                            dest = out_dir / "dashboard.html"
                            shutil.copy2(html_path, dest)
                            inject_refresh(dest, args.interval)
                            if not opened_once:
                                open_in_browser(dest, None)
                                opened_once = True
                            else:
                                print(f"Dashboard updated at {dest} (refresh existing tab).")
                        else:
                            print("Artifact did not contain an HTML file.")
        except Exception as exc:  # pragma: no cover - convenience loop
            print(f"Error: {exc}", file=sys.stderr)

        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
