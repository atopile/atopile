#!/usr/bin/env python3
"""
CI test orchestrator using FastAPI and custom workers.

Replaces pytest-xdist with a central orchestrator that distributes tests
to persistent worker processes via HTTP.
"""

import datetime
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import uvicorn

# Ensure we can import from test package
sys.path.insert(0, os.getcwd())

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from test.runner.baselines import (
    RemoteBaseline,
    fetch_all_workflow_runs,
    fetch_remote_commits,
    fetch_remote_report,
    get_current_branch,
    load_local_baseline,
    remote_commits,
    remote_commits_lock,
    save_local_baseline,
    workflow_runs_cache,
    workflow_runs_lock,
)
from test.runner.common import Outcome
from test.runner.git_info import (
    CIInfo,
    CommitInfo,
    get_ci_info,
    get_commit_info,
    get_platform_name,
)
from test.runner.orchestrator import router as orchestrator_router
from test.runner.orchestrator import set_globals as set_orchestrator_globals
from test.runner.report import (
    REPORT_HTML_PATH,
    TestAggregator,
    TestState,
    _print,
)
from test.runner.report import (
    set_globals as set_report_globals,
)
from test.runner.ui import LOG_VIEWER_DIST_DIR
from test.runner.ui import router as ui_router
from test.runner.ui import set_globals as set_ui_globals

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
ORCHESTRATOR_BIND_HOST = os.getenv("FBRK_TEST_BIND_HOST", "0.0.0.0")
ORCHESTRATOR_REPORT_HOST = os.getenv("FBRK_TEST_REPORT_HOST", ORCHESTRATOR_BIND_HOST)

# Local baselines config
BASELINES_DIR = Path("artifacts/baselines")
BASELINES_INDEX = BASELINES_DIR / "index.json"

# Remote baselines cache config
REMOTE_BASELINES_DIR = Path("artifacts/baselines/remote")
REMOTE_COMMIT_LIMIT = int(os.getenv("FBRK_TEST_REMOTE_COMMIT_LIMIT", "50"))
SKIP_REMOTE_BASELINES = os.getenv("FBRK_TEST_SKIP_REMOTE_BASELINES", "").lower() in (
    "1",
    "true",
    "yes",
)

LOG_DIR = Path("artifacts/logs")

# Global state
test_queue: queue.Queue[str] = queue.Queue()
tests_total = 0
workers: dict[int, subprocess.Popen[bytes]] = {}

# Global baseline (fetched once at startup)
remote_baseline: RemoteBaseline = RemoteBaseline()

# Global commit and CI info (populated once at startup)
commit_info: CommitInfo = CommitInfo()
ci_info: CIInfo = CIInfo()

# Global aggregator instance (initialized in main)
aggregator: TestAggregator | None = None

# Create FastAPI app and include routers
app = FastAPI()
app.include_router(orchestrator_router)
app.include_router(ui_router)

# Mount log viewer static assets at root (must be last - acts as fallback)
# Specific routes like /logs, /report take precedence over this catch-all
app.mount(
    "/",
    StaticFiles(directory=LOG_VIEWER_DIST_DIR, html=False),
    name="log-viewer-static",
)


def get_log_file(worker_id: int) -> Path:
    """Get the log file path for a worker."""
    return LOG_DIR / f"worker-{worker_id}.log"


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
            # Give OS time to release the port
            time.sleep(0.2)
            if not is_port_in_use(start_port):
                return start_port

    # If preferred port is free, use it
    if not is_port_in_use(start_port):
        return start_port

    # Fall back to finding any free port
    for attempt in range(max_attempts):
        port = start_port + attempt
        if not is_port_in_use(port):
            return port
    raise RuntimeError(
        f"No free port found in range {start_port}-{start_port + max_attempts}"
    )


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
        for line in result.stderr.splitlines():
            _print(line)
        # Also print stdout for collection errors
        for line in stdout.splitlines():
            _print(line)
        # Parse collection errors from output
        if "ERROR" in stdout:
            current_file = None
            current_error = []
            for line in stdout.splitlines():
                if line.startswith("ERROR "):
                    if current_file and current_error:
                        errors_clean[current_file] = "\n".join(current_error)
                    # Extract file path from ERROR line
                    parts = line.split(" ", 1)
                    if len(parts) > 1:
                        current_file = parts[1].strip()
                        current_error = [line]
                elif current_file:
                    current_error.append(line)
            if current_file and current_error:
                errors_clean[current_file] = "\n".join(current_error)

    # Parse tests from stdout (lines that look like test nodeids)
    tests = []
    for line in stdout.strip().split("\n"):
        line = line.strip()
        # Skip empty lines and summary lines (but not test names containing 'error')
        if not line or line.startswith("="):
            continue
        # Test nodeids contain "::" - skip actual error messages which don't
        if "::" in line:
            tests.append(line)

    return tests, errors_clean


def start_server(port) -> uvicorn.Server:
    """Start the uvicorn server."""
    config = uvicorn.Config(
        app,
        host=ORCHESTRATOR_BIND_HOST,
        port=port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    # Wait for server to start
    time.sleep(0.5)
    return server


def run_report_server(open_browser: bool = False) -> None:
    """Run the report server standalone (for --keep-open without running tests)."""
    port = get_free_port()
    report_url = f"http://127.0.0.1:{port}/report"
    _print(f"Starting report server at {report_url}")

    # Initialize globals for orchestrator and UI
    set_orchestrator_globals(test_queue, None)
    set_ui_globals(None, REPORT_HTML_PATH, REMOTE_BASELINES_DIR)

    server = start_server(port)

    if open_browser:
        import webbrowser

        webbrowser.open(report_url)

    _print(f"Report available at: {report_url}")
    _print("Press Ctrl+C to stop...")

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
    keep_open: bool = False,
    test_run_id: str | None = None,
    extra_env: dict[str, str] | None = None,
):
    global tests_total, commit_info, ci_info, workers, aggregator, remote_baseline

    # Set up globals for report module
    set_report_globals(test_queue, workers, commit_info, ci_info)

    # Gather commit and CI info at startup (robust to failures)
    commit_info = get_commit_info()
    ci_info = get_ci_info()

    # Update report module with fresh info
    set_report_globals(test_queue, workers, commit_info, ci_info)

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

    # Start fetching remote commits list in background (for dropdown)
    def fetch_remote_commits_background():
        if SKIP_REMOTE_BASELINES:
            return
        try:
            branch = get_current_branch() or "main"
            commits = fetch_remote_commits(branch, limit=REMOTE_COMMIT_LIMIT)
            with remote_commits_lock:
                remote_commits.clear()
                remote_commits.extend(commits)

            # Fetch workflow runs across ALL branches for branch heads dropdown
            all_workflow_runs = fetch_all_workflow_runs(limit=200)
            with workflow_runs_lock:
                workflow_runs_cache.clear()
                workflow_runs_cache.update(all_workflow_runs)

            # Download HEAD baseline to cache if not already cached
            if commits and not baseline_commit and not local_baseline_name:
                head_commit = commits[0]
                if head_commit.get("has_artifact"):
                    commit_hash_val = head_commit["commit_hash"]
                    cache_file = REMOTE_BASELINES_DIR / f"{commit_hash_val}.json"
                    if not cache_file.exists():
                        # Download and cache HEAD baseline
                        fetch_remote_report(commit_hash=commit_hash_val, use_cache=True)
        except Exception as e:
            print(f"Warning: Could not fetch remote commits: {e}")

    if not local_baseline_name:
        commits_thread = threading.Thread(
            target=fetch_remote_commits_background, daemon=True
        )
        commits_thread.start()

    # Initialize aggregator with loaded baseline (for local) or empty (for remote fetch)
    initial_baseline = remote_baseline if local_baseline_name else RemoteBaseline()
    aggregator = TestAggregator(
        tests,
        initial_baseline,
        pytest_args=pytest_args,
        baseline_requested=baseline_commit or local_baseline_name,
        collection_errors=errors,
    )

    # Set up orchestrator and UI globals
    set_orchestrator_globals(test_queue, aggregator)
    set_ui_globals(aggregator, REPORT_HTML_PATH, REMOTE_BASELINES_DIR)

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
    # Use provided test_run_id if available, otherwise generate one
    if test_run_id is None:
        import hashlib

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        test_run_id = hashlib.sha256(f"pytest:{timestamp}".encode()).hexdigest()[:16]
    env["ATO_TEST_RUN_ID"] = test_run_id

    # Apply extra environment variables (e.g., ConfigFlags from UI)
    if extra_env:
        for key, value in extra_env.items():
            env[key] = value
        _print(f"Custom env vars: {', '.join(extra_env.keys())}")

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
                    n = len(pending_unstarted)
                    _print(f"WARNING: {n} pending unstarted tests; requeueing.")
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

    from test.runner.report import format_duration

    total_duration = (datetime.datetime.now() - aggregator.start_time).total_seconds()
    _print(f"Total time: {format_duration(total_duration)}")

    report = aggregator.generate_reports(periodic=False)

    # Save as local baseline if requested
    if save_baseline_name:
        baseline_path = save_local_baseline(
            report,
            save_baseline_name,
            BASELINES_DIR,
            BASELINES_INDEX,
            get_platform_name(),
        )
        _print(f"Baseline saved: {baseline_path}")

    # Print link to the static report file
    report_path = REPORT_HTML_PATH.resolve()
    file_url = f"file://{report_path}"
    clickable_file = f"\033]8;;{file_url}\033\\📄 {report_path}\033]8;;\033\\"
    _print(f"Report saved: {clickable_file}")

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
