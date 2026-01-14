"""CLI command definition for `ato build`."""

from __future__ import annotations

import logging
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import IO, Annotated

import typer

from atopile.telemetry import capture

logger = logging.getLogger(__name__)

# Default worker count is CPU count
DEFAULT_WORKER_COUNT = os.cpu_count() or 4


def discover_projects(root: Path) -> list[Path]:
    """
    Discover ato projects in a directory.

    If root contains ato.yaml, returns [root].
    Otherwise, finds all directories containing ato.yaml below root.
    """
    config_file = root / "ato.yaml"
    if config_file.exists():
        return [root]

    # Find all ato.yaml files below root (non-recursive in .ato/modules)
    projects = []
    for path in root.rglob("ato.yaml"):
        # Skip .ato/modules (dependencies)
        if ".ato" in path.parts:
            continue
        projects.append(path.parent)

    return sorted(projects)


class BuildProcess:
    """Manages a single build subprocess."""

    def __init__(
        self,
        build_name: str,
        log_dir: Path,
        project_root: Path,
        project_name: str | None = None,
    ):
        self.name = build_name
        self.project_name = project_name  # For multi-project builds
        if project_name:
            self.display_name = f"{project_name}/{build_name}"
        else:
            self.display_name = build_name
        self.log_dir = log_dir
        self.project_root = project_root
        self.process: subprocess.Popen | None = None
        self.log_file: Path | None = None
        self.status_file: Path | None = None
        self.start_time: float = 0.0
        self.end_time: float = 0.0
        self.return_code: int | None = None
        self.current_stage: str = "Queued"
        self.warnings: int = 0
        self.errors: int = 0
        self._log_handle: IO | None = None
        self._error_reported: bool = False  # Track if error was already printed

    def start(self, passthrough: bool = False) -> None:
        """Start the build subprocess.

        Args:
            passthrough: If True, output goes to terminal. If False, captured to log.
        """
        # Create log directory for this build
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "build.log"
        self.status_file = self.log_dir / "status.txt"

        # Initialize status file
        self.status_file.write_text("Starting...")

        # Build the command - run ato build for just this target
        cmd = [
            sys.executable,
            "-m",
            "atopile",
            "build",
            "-b",
            self.name,
            "--parallel-worker",  # Signal this is a worker process
        ]

        # Copy environment and set worker mode
        env = os.environ.copy()
        env["ATO_PARALLEL_WORKER"] = "1"
        env["ATO_BUILD_STATUS_FILE"] = str(self.status_file)
        # Pass timestamp so worker writes logs to same directory as parent
        from atopile.cli.logging_ import NOW

        env["ATO_BUILD_TIMESTAMP"] = NOW

        self.start_time = time.time()

        if passthrough:
            # Verbose mode: output goes to terminal AND tee to log file
            # Disable Python buffering in subprocess for real-time output
            env["PYTHONUNBUFFERED"] = "1"
            # Force Rich to output colors even though stdout is a pipe
            env["FORCE_COLOR"] = "1"
            # Disable animated progress spinners (they don't work when piped)
            env["ATO_NO_PROGRESS_ANIMATION"] = "1"
            self._log_handle = open(self.log_file, "w", encoding="utf-8")
            self.process = subprocess.Popen(
                cmd,
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                bufsize=1,  # Line buffered
                text=True,  # Text mode for proper encoding
                encoding="utf-8",
            )
        else:
            # Normal mode: output captured to log file only
            self._log_handle = open(self.log_file, "w")
            self.process = subprocess.Popen(
                cmd,
                cwd=self.project_root,
                stdout=self._log_handle,
                stderr=subprocess.STDOUT,
                env=env,
            )

    def poll(self) -> int | None:
        """Check if process has finished. Returns exit code or None if still running."""
        if self.process is None:
            return None

        # Read current stage from status file
        self._read_status()

        ret = self.process.poll()
        if ret is not None and self.return_code is None:
            self.return_code = ret
            self.end_time = time.time()
            if self._log_handle:
                self._log_handle.close()
                self._log_handle = None
            self._parse_log_for_stats()
        return ret

    def wait(self) -> int:
        """Wait for process to complete, streaming output to terminal and log.

        Used in verbose mode where output should be visible in real-time.
        """
        if self.process is None:
            return -1

        # If process.stdout is piped (passthrough mode), tee to console and log
        if self.process.stdout:
            # Read lines and stream in real-time
            # PYTHONUNBUFFERED=1 ensures subprocess flushes after each line
            for line in iter(self.process.stdout.readline, ""):
                sys.stdout.write(line)
                sys.stdout.flush()
                if self._log_handle:
                    self._log_handle.write(line)
                    self._log_handle.flush()

        ret = self.process.wait()
        self.return_code = ret
        self.end_time = time.time()
        if self._log_handle:
            self._log_handle.close()
            self._log_handle = None
        self._parse_log_for_stats()
        return ret

    def _read_status(self) -> None:
        """Read current stage from status file."""
        if self.status_file and self.status_file.exists():
            try:
                import re

                status = self.status_file.read_text().strip()
                # Strip Rich markup like [green]...[/green]
                status = re.sub(r"\[/?[a-z_]+\]", "", status)
                self.current_stage = status
            except Exception:
                pass  # File might be being written to

    def _parse_log_for_stats(self) -> None:
        """Parse log file for warnings/errors count."""
        if self.log_file and self.log_file.exists():
            try:
                content = self.log_file.read_text()
                # Count warnings and errors from log
                self.warnings = content.lower().count("warning")
                self.errors = content.lower().count("error")
            except Exception:
                pass

    def get_error_message(self) -> str | None:
        """Extract a brief error summary for inline display."""
        if not self.log_file or not self.log_file.exists():
            return None

        try:
            content = self.log_file.read_text()
            lines = content.strip().split("\n")

            # Skip patterns that are just generic footers
            skip_patterns = [
                "unfortunately errors",
                "if you need a hand",
                "discord",
            ]

            def is_useful_line(line: str) -> bool:
                line_lower = line.lower()
                return not any(skip in line_lower for skip in skip_patterns)

            # First pass: look for lines starting with "error:" (most specific)
            for line in lines:
                line = line.strip()
                if line.lower().startswith("error:") and is_useful_line(line):
                    if len(line) > 80:
                        line = line[:77] + "..."
                    return line

            # Second pass: look for "ERROR" log level and extract the message
            for i, line in enumerate(lines):
                if "ERROR" in line and is_useful_line(line):
                    # Extract the error title (text after ERROR)
                    parts = line.split("ERROR", 1)
                    if len(parts) > 1:
                        msg = parts[1].strip()
                        if msg and is_useful_line(msg):
                            if len(msg) > 80:
                                msg = msg[:77] + "..."
                            return msg

            # Final fallback
            for line in lines:
                line = line.strip()
                if line and not line.startswith("[") and is_useful_line(line):
                    if len(line) > 80:
                        line = line[:77] + "..."
                    return line

        except Exception:
            pass

        return "Build failed (check logs)"

    def get_error_details(self) -> list[str]:
        """Extract detailed error context for rich display."""
        if not self.log_file or not self.log_file.exists():
            return []

        try:
            content = self.log_file.read_text()
            lines = content.strip().split("\n")

            # Skip patterns
            skip_patterns = ["unfortunately errors", "if you need a hand", "discord"]

            def should_skip(line: str) -> bool:
                line_lower = line.lower()
                return any(skip in line_lower for skip in skip_patterns)

            # Find ERROR block and extract context
            error_lines = []
            in_error_block = False
            blank_count = 0

            for line in lines:
                # Start capturing at ERROR
                if "ERROR" in line and not should_skip(line):
                    in_error_block = True
                    # Extract message after ERROR
                    parts = line.split("ERROR", 1)
                    if len(parts) > 1 and parts[1].strip():
                        error_lines.append(parts[1].strip())
                    continue

                if in_error_block:
                    stripped = line.strip()
                    if should_skip(stripped):
                        break
                    if not stripped:
                        blank_count += 1
                        if blank_count > 1:
                            break  # Two blank lines ends the block
                        continue
                    blank_count = 0
                    # Keep the line (preserve some indentation for context)
                    error_lines.append(line.rstrip())

                    # Stop after reasonable amount of context
                    if len(error_lines) > 10:
                        break

            return error_lines

        except Exception:
            return []

    @property
    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        if self.start_time == 0:
            return 0.0
        end = self.end_time if self.end_time > 0 else time.time()
        return end - self.start_time

    @property
    def is_running(self) -> bool:
        """Check if build is still running."""
        return self.process is not None and self.return_code is None

    @property
    def status(self) -> str:
        """Get current status string."""
        if self.process is None:
            return "queued"
        elif self.return_code is None:
            return "building"
        elif self.return_code == 0:
            return "warning" if self.warnings > 0 else "success"
        else:
            return "failed"

    def terminate(self) -> None:
        """Terminate the build process."""
        if self.process and self.return_code is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()


class ParallelBuildManager:
    """Manages multiple build processes with live display and job queue."""

    # Status icons with colors (rich markup)
    _STATUS_ICONS = {
        "queued": "[dim]○[/dim]",
        "pending": "[dim]○[/dim]",
        "building": "[blue]●[/blue]",
        "success": "[green]✓[/green]",
        "warning": "[yellow]⚠[/yellow]",
        "failed": "[red]✗[/red]",
    }

    _STAGE_WIDTH = 22  # "Building... [123.4s]" fits in ~22 chars

    def __init__(
        self,
        # (build_name, project_root, project_name)
        build_tasks: list[tuple[str, Path, str | None]],
        logs_base: Path,
        max_workers: int = DEFAULT_WORKER_COUNT,
        verbose: bool = False,
    ):
        """
        Initialize the build manager.

        Args:
            build_tasks: List of (build_name, project_root, project_name) tuples
            logs_base: Base directory for logs
            max_workers: Maximum concurrent builds (default: CPU count)
            verbose: Show full output (runs sequentially, no live display)
        """
        self.build_tasks = build_tasks
        self.logs_base = logs_base
        self.max_workers = max_workers
        self.verbose = verbose

        # Check if this is multi-project mode (any task has a project_name)
        self.multi_project_mode = any(t[2] is not None for t in build_tasks)

        # Create BuildProcess objects for all tasks
        self.processes: dict[str, BuildProcess] = {}
        self._task_queue: queue.Queue[str] = queue.Queue()

        from atopile.cli.logging_ import NOW

        self._now = NOW

        for build_name, project_root, project_name in build_tasks:
            if project_name:
                display_name = f"{project_name}/{build_name}"
            else:
                display_name = build_name
            if project_name:
                log_dir = logs_base / "archive" / NOW / project_name / build_name
            else:
                log_dir = logs_base / "archive" / NOW / build_name
            bp = BuildProcess(build_name, log_dir, project_root, project_name)
            self.processes[display_name] = bp
            self._task_queue.put(display_name)

        self._lock = threading.Lock()
        self._display_lock = threading.Lock()  # Synchronize display updates
        self._stop_display = threading.Event()
        self._display_thread: threading.Thread | None = None
        self._active_workers: set[str] = set()

        # Import rich for display
        from rich.console import Console
        from rich.live import Live
        from rich.table import Table

        self._console = Console()
        self._Table = Table
        self._live: Live | None = None

    @classmethod
    def _make_file_uri(cls, path: Path | str, line: int | None = None) -> str:
        """Create a file:// URI with optional line number fragment."""
        path = Path(path) if isinstance(path, str) else path
        uri = path.absolute().as_uri()
        # Some terminals/editors support #L<line> fragment for line numbers
        if line:
            uri = f"{uri}#L{line}"
        return uri

    @classmethod
    def _linkify_paths(cls, text: str) -> str:
        """Make file paths in text clickable using Rich link markup."""
        import re

        def make_link(match: re.Match) -> str:
            path = match.group(1)
            line_num = match.group(2)
            col = match.group(3) if match.group(3) else "1"
            # Use file:// URI with line fragment
            uri = f"file://{path}#L{line_num}"
            return f"[link={uri}]{path}:{line_num}:{col}[/link]"

        # Match file paths with line numbers (e.g., /path/to/file.ato:38:10)
        return re.sub(r"(/[^\s:]+\.ato):(\d+):?(\d+)?", make_link, text)

    def _start_next_build(self) -> bool:
        """Start the next build from the queue. Returns True if a build was started."""
        try:
            display_name = self._task_queue.get_nowait()
        except queue.Empty:
            return False

        bp = self.processes[display_name]
        bp.start()
        with self._lock:
            self._active_workers.add(display_name)
        return True

    def _fill_worker_slots(self) -> None:
        """Start builds to fill available worker slots."""
        with self._lock:
            active_count = len(self._active_workers)

        while active_count < self.max_workers:
            if not self._start_next_build():
                break
            with self._lock:
                active_count = len(self._active_workers)

    def _get_project_states(self) -> dict[str, dict]:
        """
        Aggregate build states by project for multi-project view.

        Returns dict of project_name -> {
            'builds': list of BuildProcess,
            'status': aggregate status (failed > building > warning > success > queued),
            'completed': count of completed builds,
            'total': total builds for this project,
            'current_build': name of currently building target (if any),
            'current_stage': stage of current build,
            'elapsed': max elapsed time across builds,
            'log_dir': project-level log directory,
        }
        """
        projects: dict[str, dict] = {}

        for display_name, bp in self.processes.items():
            project = bp.project_name or display_name
            if project not in projects:
                projects[project] = {
                    "builds": [],
                    "completed": 0,
                    "failed": 0,
                    "warnings": 0,
                    "building": 0,
                    "queued": 0,
                    "total": 0,
                    "current_build": None,
                    "current_stage": None,
                    "elapsed": 0.0,
                    "log_dir": None,
                }

            p = projects[project]
            p["builds"].append(bp)
            p["total"] += 1
            p["elapsed"] = max(p["elapsed"], bp.elapsed)

            # Set log dir to project level (parent of build log dir)
            if bp.log_dir and bp.project_name:
                p["log_dir"] = bp.log_dir.parent

            status = bp.status
            if status == "building":
                p["building"] += 1
                p["current_build"] = bp.name
                p["current_stage"] = bp.current_stage
            elif status == "failed":
                p["failed"] += 1
                p["completed"] += 1
            elif status in ("success", "warning"):
                p["completed"] += 1
                if status == "warning":
                    p["warnings"] += 1
            elif status == "queued":
                p["queued"] += 1

        # Determine aggregate status for each project
        for p in projects.values():
            if p["failed"] > 0:
                p["status"] = "failed"
            elif p["building"] > 0:
                p["status"] = "building"
            elif p["queued"] == p["total"]:
                p["status"] = "queued"
            elif p["warnings"] > 0:
                p["status"] = "warning"
            else:
                p["status"] = "success"

        return projects

    def _render_table(self):
        """Render current status as a table with smart row limiting."""
        import shutil

        from rich.box import SIMPLE

        # Use project-level view for multi-project mode
        if self.multi_project_mode:
            return self._render_project_table()

        # Get terminal size
        term_size = shutil.get_terminal_size()
        term_height = term_size.lines
        term_width = term_size.columns
        max_rows = max(term_height - 10, 10)  # At least 10 rows

        # Determine max target name length for dynamic column width
        max_name_len = max(len(bp.display_name) for bp in self.processes.values())
        target_width = min(max(max_name_len, 12), 30)  # Clamp between 12 and 30

        # Calculate available width for status column
        # Fixed widths: icon(1) + time(5) + logs(~6) + padding(~10)
        fixed_width = 1 + target_width + 5 + 6 + 10
        status_width = max(self._STAGE_WIDTH, term_width - fixed_width)
        status_width = min(status_width, 50)  # Cap at reasonable max

        table = self._Table(
            show_header=True,
            header_style="bold dim",
            box=SIMPLE,
            padding=(0, 1),
            expand=False,
        )

        table.add_column("", width=1)  # Status icon
        table.add_column("Target", width=target_width, style="cyan")
        table.add_column("Status", width=status_width)
        table.add_column("Time", width=5, justify="right")
        table.add_column("Logs", style="dim")

        with self._lock:
            # Sort builds by priority: building > failed > warning > success > queued
            priority_order = {
                "building": 0,
                "failed": 1,
                "warning": 2,
                "success": 3,
                "queued": 4,
            }
            sorted_builds = sorted(
                self.processes.items(),
                key=lambda x: (priority_order.get(x[1].status, 5), x[0]),
            )

            # Determine which rows to show
            rows_shown = 0
            hidden_queued = 0

            for display_name, bp in sorted_builds:
                status = bp.status

                # If we've hit the limit, only skip queued items
                if rows_shown >= max_rows:
                    if status == "queued":
                        hidden_queued += 1
                        continue
                    # Always show non-queued items (building/failed/completed)

                icon = self._STATUS_ICONS.get(status, "[dim]○[/dim]")

                # Format stage text with colors
                if status == "building":
                    stage_name = bp.current_stage or "Building..."
                    # Truncate based on available status width
                    max_stage = status_width - 3  # Leave room for "..."
                    if len(stage_name) > max_stage:
                        stage_name = stage_name[: max_stage - 3] + "..."
                    stage_text = f"[blue]{stage_name}[/blue]"
                elif status in ("success", "warning"):
                    stage_text = "[green]Completed[/green]"
                elif status == "failed":
                    stage_text = "[red]Failed[/red]"
                elif status == "queued":
                    stage_text = "[dim]Queued[/dim]"
                else:
                    stage_text = "[dim]Waiting...[/dim]"

                # Format time
                if status == "building":
                    time_text = f"[blue]{int(bp.elapsed)}s[/blue]"
                elif status == "failed":
                    time_text = f"[red]{int(bp.elapsed)}s[/red]"
                elif status == "queued":
                    time_text = "[dim]-[/dim]"
                else:
                    time_text = f"{int(bp.elapsed)}s"

                # Log path - show as clickable hyperlink to summary.md
                if bp.log_dir and bp.log_dir.exists():
                    summary_file = bp.log_dir / "summary.md"
                    uri = self._make_file_uri(summary_file.absolute())
                    log_text = f"[link={uri}]logs[/link]"
                else:
                    log_text = ""

                table.add_row(icon, display_name, stage_text, time_text, log_text)
                rows_shown += 1

            # Add a summary row for hidden queued items
            if hidden_queued > 0:
                table.add_row(
                    "[dim]...[/dim]",
                    f"[dim]+{hidden_queued} more queued[/dim]",
                    "",
                    "",
                    "",
                )

        return table

    def _render_project_table(self):
        """Render project-level status table for multi-project mode."""
        import shutil

        from rich.box import SIMPLE

        term_size = shutil.get_terminal_size()
        term_height = term_size.lines
        term_width = term_size.columns
        max_rows = max(term_height - 10, 10)

        # Find max project name length
        projects = self._get_project_states()
        max_name_len = max(len(name) for name in projects.keys())
        project_width = min(max(max_name_len, 12), 28)

        # Calculate available width for status column
        # Fixed widths: icon(1) + time(5) + logs(~6) + padding(~10)
        fixed_width = 1 + project_width + 5 + 6 + 10
        status_width = max(self._STAGE_WIDTH + 12, term_width - fixed_width)
        # Cap at reasonable max to avoid super long lines
        status_width = min(status_width, 60)

        table = self._Table(
            show_header=True,
            header_style="bold dim",
            box=SIMPLE,
            padding=(0, 1),
            expand=False,
        )

        table.add_column("", width=1)  # Status icon
        table.add_column("Project", width=project_width, style="cyan")
        table.add_column("Status", width=status_width)
        table.add_column("Time", width=5, justify="right")
        table.add_column("Logs", style="dim")

        # Sort projects by priority
        priority_order = {
            "building": 0,
            "failed": 1,
            "warning": 2,
            "success": 3,
            "queued": 4,
        }
        sorted_projects = sorted(
            projects.items(),
            key=lambda x: (priority_order.get(x[1]["status"], 5), x[0]),
        )

        rows_shown = 0
        hidden_queued = 0

        for project_name, p in sorted_projects:
            status = p["status"]

            # Limit rows, but always show non-queued
            if rows_shown >= max_rows:
                if status == "queued":
                    hidden_queued += 1
                    continue

            icon = self._STATUS_ICONS.get(status, "[dim]○[/dim]")

            # Build status text showing progress and current activity
            if status == "building":
                stage = p["current_stage"] or "Building"
                build_name = p["current_build"] or ""
                progress = f"{p['completed']}/{p['total']}"

                # Calculate available space for stage based on status_width
                # Format: "{build_name} {progress} {stage}"
                # Reserve: build_name(max 10) + space + progress + space
                reserved = min(len(build_name), 10) + 1 + len(progress) + 1
                max_stage_len = max(status_width - reserved, 10)

                if len(stage) > max_stage_len:
                    stage = stage[: max_stage_len - 3] + "..."
                if len(build_name) > 10:
                    build_name = build_name[:8] + ".."

                status_text = f"[blue]{build_name}[/blue] {progress} {stage}"
            elif status == "failed":
                status_text = (
                    f"[red]{p['failed']} failed[/red], "
                    f"{p['completed'] - p['failed']}/{p['total']} done"
                )
            elif status == "warning":
                status_text = f"[yellow]{p['completed']}/{p['total']} done[/yellow]"
            elif status == "success":
                status_text = f"[green]{p['completed']}/{p['total']} done[/green]"
            elif status == "queued":
                status_text = f"[dim]Queued ({p['total']} builds)[/dim]"
            else:
                status_text = f"{p['completed']}/{p['total']}"

            # Time
            if status == "building":
                time_text = f"[blue]{int(p['elapsed'])}s[/blue]"
            elif status == "failed":
                time_text = f"[red]{int(p['elapsed'])}s[/red]"
            elif status == "queued":
                time_text = "[dim]-[/dim]"
            else:
                time_text = f"{int(p['elapsed'])}s"

            # Log path - show as clickable hyperlink to project log dir
            # (project level doesn't have a single summary, so link to dir)
            log_text = ""
            if p["log_dir"] and p["log_dir"].exists():
                # Directories always use file:// (vscode:// doesn't work for dirs)
                uri = p["log_dir"].absolute().as_uri()
                log_text = f"[link={uri}]logs[/link]"

            table.add_row(icon, project_name, status_text, time_text, log_text)
            rows_shown += 1

        if hidden_queued > 0:
            table.add_row(
                "[dim]...[/dim]",
                f"[dim]+{hidden_queued} more queued[/dim]",
                "",
                "",
                "",
            )

        return table

    def _render_summary(self) -> str:
        """Render summary line."""
        with self._lock:
            queued = sum(1 for bp in self.processes.values() if bp.status == "queued")
            building = sum(
                1 for bp in self.processes.values() if bp.status == "building"
            )
            completed = sum(
                1
                for bp in self.processes.values()
                if bp.status in ("success", "warning")
            )
            failed = sum(1 for bp in self.processes.values() if bp.status == "failed")
            warnings = sum(bp.warnings for bp in self.processes.values())

        parts = []
        if queued > 0:
            parts.append(f"[dim]Queued: {queued}[/dim]")
        if building > 0:
            parts.append(f"Building: {building}/{self.max_workers}")
        if completed > 0:
            parts.append(f"Completed: {completed}")
        if failed > 0:
            parts.append(f"[red]Failed: {failed}[/red]")
        if warnings > 0:
            parts.append(f"Warnings: {warnings}")

        return "  ".join(parts) if parts else "Starting..."

    def _display_loop(self) -> None:
        """Background thread that updates display."""
        from rich.console import Group

        while not self._stop_display.is_set():
            if self._live:
                with self._display_lock:
                    table = self._render_table()
                    summary = self._render_summary()
                    self._live.update(Group(table, "", summary))
            time.sleep(0.5)

    def run_until_complete(self) -> dict[str, int]:
        """
        Run all builds until complete, showing live progress.

        Uses a queue to limit concurrent builds to max_workers.
        In verbose mode, runs sequentially with full output.

        Returns dict of display_name -> exit_code.
        """
        if self.verbose:
            return self._run_verbose()
        return self._run_parallel()

    def _run_verbose(self) -> dict[str, int]:
        """Run builds sequentially with full output visible."""
        results: dict[str, int] = {}

        for display_name, bp in self.processes.items():
            self._console.print(f"\n[bold cyan]▶ Building {display_name}[/bold cyan]")
            self._console.print(f"[dim]  Logs: {bp.log_dir}[/dim]\n")

            # Start the build with stdout/stderr passed through
            bp.start(passthrough=True)

            # Wait for completion
            ret = bp.wait()
            results[display_name] = ret

            if ret == 0:
                if bp.warnings > 0:
                    self._console.print(
                        f"\n[yellow]⚠ {display_name} completed with "
                        f"{bp.warnings} warning(s)[/yellow]"
                    )
                else:
                    self._console.print(f"\n[green]✓ {display_name} completed[/green]")
            else:
                self._console.print(f"\n[red]✗ {display_name} failed[/red]")

        return results

    def _run_parallel(self) -> dict[str, int]:
        """Run builds in parallel with live progress display."""
        from rich.console import Group
        from rich.live import Live

        results: dict[str, int] = {}

        with Live(
            self._render_table(),
            console=self._console,
            refresh_per_second=2,
        ) as live:
            self._live = live

            # Start display update thread
            self._display_thread = threading.Thread(
                target=self._display_loop, daemon=True
            )
            self._display_thread.start()

            try:
                # Fill initial worker slots
                self._fill_worker_slots()

                # Poll until all processes complete
                while True:
                    completed_this_round = []

                    with self._lock:
                        # Check for completed builds
                        for display_name in list(self._active_workers):
                            bp = self.processes[display_name]
                            ret = bp.poll()
                            if ret is not None:
                                results[display_name] = ret
                                completed_this_round.append(display_name)

                                # Print error immediately if build failed
                                if ret != 0 and not bp._error_reported:
                                    bp._error_reported = True
                                    error_details = bp.get_error_details()
                                    error_msg = bp.get_error_message()

                                    # Print error above display (lock to sync)
                                    with self._display_lock:
                                        live.console.print(
                                            f"[red bold]✗ {display_name}[/red bold]"
                                        )
                                        if error_details:
                                            for line in error_details:
                                                # Make file paths clickable
                                                line = self._linkify_paths(line)
                                                live.console.print(f"  {line}")
                                        elif error_msg:
                                            live.console.print(f"  {error_msg}")

                                        # Add link to full log at the end
                                        if bp.log_file and bp.log_file.exists():
                                            log_path = bp.log_file.absolute()
                                            uri = self._make_file_uri(log_path)
                                            link = f"[link={uri}]View full log[/link]"
                                            live.console.print(f"  [dim]→ {link}[/dim]")
                                        live.console.print("")  # Blank line

                        # Remove completed builds from active set
                        for name in completed_this_round:
                            self._active_workers.discard(name)

                    # Fill any freed worker slots
                    if completed_this_round:
                        self._fill_worker_slots()

                    # Check if all builds are done
                    all_done = (
                        len(results) == len(self.processes) and self._task_queue.empty()
                    )
                    if all_done:
                        break

                    time.sleep(0.2)

            except KeyboardInterrupt:
                # Terminate all processes on interrupt
                for bp in self.processes.values():
                    bp.terminate()
                raise

            finally:
                self._stop_display.set()
                if self._display_thread:
                    self._display_thread.join(timeout=1.0)

            # Final update
            table = self._render_table()
            summary = self._render_summary()
            live.update(Group(table, "", summary))

        return results

    def _generate_build_summary(self, bp: "BuildProcess", summary_dir: Path) -> None:
        """Generate per-build summary with log file listings."""
        build_summary_file = bp.log_dir / "summary.md"

        # Determine status emoji
        if bp.status == "success":
            status_text = "✅ Success"
        elif bp.status == "warning":
            status_text = "⚠️ Warning"
        else:
            status_text = "❌ Failed"

        lines = [
            f"# Build: {bp.display_name}",
            "",
            f"**Status:** {status_text}",
            f"**Time:** {bp.elapsed:.1f}s",
            f"**Warnings:** {bp.warnings}",
            f"**Errors:** {bp.errors}",
            "",
        ]

        # Extract errors from log files
        errors = self._extract_log_messages(bp.log_dir, "error")
        if errors:
            lines.append("## Errors")
            lines.append("")
            lines.append("```")
            for error in errors[:20]:  # Limit to 20 errors
                lines.append(error)
            if len(errors) > 20:
                lines.append(f"... and {len(errors) - 20} more errors")
            lines.append("```")
            lines.append("")

        # Extract warnings from log files
        warnings = self._extract_log_messages(bp.log_dir, "warning")
        if warnings:
            lines.append("## Warnings")
            lines.append("")
            lines.append("```")
            for warning in warnings[:20]:  # Limit to 20 warnings
                lines.append(warning)
            if len(warnings) > 20:
                lines.append(f"... and {len(warnings) - 20} more warnings")
            lines.append("```")
            lines.append("")

        lines.append("## Log Files")
        lines.append("")

        # Group log files by stage
        log_files = sorted(bp.log_dir.glob("*.log"))
        stages: dict[str, list[Path]] = {}

        for log_file in log_files:
            # Parse stage name from filename (e.g., "picker.info.log" -> "picker")
            parts = log_file.stem.split(".")
            if len(parts) >= 2:
                stage = parts[0]
            else:
                stage = log_file.stem

            if stage not in stages:
                stages[stage] = []
            stages[stage].append(log_file)

        # List stages with their log files
        for stage, files in stages.items():
            lines.append(f"### {stage}")
            lines.append("")
            for f in sorted(files, key=lambda x: x.name):
                # Check if file has content
                try:
                    size = f.stat().st_size
                    if size > 0:
                        lines.append(f"- [{f.name}](./{f.name}) ({size} bytes)")
                    else:
                        lines.append(f"- {f.name} (empty)")
                except OSError:
                    lines.append(f"- {f.name}")
            lines.append("")

        build_summary_file.write_text("\n".join(lines))

    def _extract_log_messages(self, log_dir: Path, level: str) -> list[str]:
        """Extract messages from log files of a specific level."""
        messages = []

        # Check build.log for ERROR/WARNING lines
        build_log = log_dir / "build.log"
        if build_log.exists():
            try:
                content = build_log.read_text()
                for line in content.split("\n"):
                    if level.upper() in line:
                        # Extract message after the level indicator
                        msg = line.strip()
                        if msg and msg not in messages:
                            messages.append(msg)
            except Exception:
                pass

        # Check level-specific log files (e.g., *.error.log, *.warning.log)
        for log_file in log_dir.glob(f"*.{level}.log"):
            try:
                content = log_file.read_text().strip()
                if content:
                    for line in content.split("\n"):
                        line = line.strip()
                        if line and line not in messages:
                            messages.append(line)
            except Exception:
                pass

        return messages

    def generate_summary(self) -> Path:
        """Generate summary markdown file."""
        from atopile.cli.logging_ import NOW

        summary_dir = self.logs_base / "archive" / NOW
        summary_dir.mkdir(parents=True, exist_ok=True)
        summary_file = summary_dir / "summary.md"

        lines = [
            "# Build Summary",
            "",
            f"**Date:** {NOW}",
            "",
            "## Build Results",
            "",
            "| Target | Status | Time | Warn | Err | Logs |",
            "|--------|--------|------|------|-----|------|",
        ]

        for display_name, bp in self.processes.items():
            status = bp.status
            if status == "success":
                status_text = "✅"
            elif status == "warning":
                status_text = "⚠️"
            elif status == "failed":
                status_text = "❌"
            else:
                status_text = "⏳"

            time_text = f"{bp.elapsed:.1f}s"

            if bp.log_dir and bp.log_dir.exists():
                # Use relative path from summary file location for cleaner links
                try:
                    rel_path = bp.log_dir.relative_to(summary_dir)
                except ValueError:
                    rel_path = bp.log_dir.name
                # Link to the per-build summary.md
                log_link = f"[📁 {bp.name}](./{rel_path}/summary.md)"
            else:
                log_link = "-"

            lines.append(
                f"| {display_name} | {status_text} | {time_text} | "
                f"{bp.warnings} | {bp.errors} | {log_link} |"
            )

            # Generate per-build summary with log file listing
            if bp.log_dir and bp.log_dir.exists():
                self._generate_build_summary(bp, summary_dir)

        # Summary stats
        total = len(self.processes)
        success = sum(
            1 for bp in self.processes.values() if bp.status in ("success", "warning")
        )
        failed = sum(1 for bp in self.processes.values() if bp.status == "failed")
        warnings = sum(bp.warnings for bp in self.processes.values())
        errors = sum(bp.errors for bp in self.processes.values())

        lines.extend(
            [
                "",
                "## Summary",
                "",
                f"- **Total builds:** {total}",
                f"- **Successful:** {success}",
                f"- **Failed:** {failed}",
                f"- **Total warnings:** {warnings}",
                f"- **Total errors:** {errors}",
            ]
        )

        summary_file.write_text("\n".join(lines))

        # Update latest symlink
        latest_link = self.logs_base / "latest"
        if latest_link.exists() and latest_link.is_symlink():
            latest_link.unlink()
        try:
            latest_link.symlink_to(summary_dir, target_is_directory=True)
        except OSError:
            pass

        return summary_file


def _run_single_build(frozen: bool | None = None) -> None:
    """
    Run a single build target (worker mode).

    This is called when --parallel-worker flag is set.
    """
    from atopile import build as buildlib
    from atopile import buildutil
    from atopile.config import config

    # Get the single build target from config
    build_names = list(config.selected_builds)
    if len(build_names) != 1:
        raise RuntimeError(
            f"Worker mode expects exactly 1 build, got {len(build_names)}"
        )

    build_name = build_names[0]

    with config.select_build(build_name):
        app = buildlib.init_app()
        buildutil.build(app)


def _build_all_projects(
    root: Path,
    jobs: int,
    frozen: bool | None = None,
    selected_builds: list[str] | None = None,
    verbose: bool = False,
) -> None:
    """
    Build all projects in a directory.

    Discovers all ato.yaml files and builds all their targets.
    Use -b to filter to specific build targets across all projects.
    """
    from atopile.cli.logging_ import NOW
    from atopile.config import ProjectConfig

    # Discover projects
    projects = discover_projects(root)

    if not projects:
        logger.error("No ato projects found in %s", root)
        raise typer.Exit(1)

    logger.info("Found %d projects", len(projects))

    # Collect build tasks from all projects
    # Format: (build_name, project_root, project_name)
    build_tasks: list[tuple[str, Path, str | None]] = []

    for project_path in projects:
        project_name = project_path.name

        # Load project config to get build targets
        project_config = ProjectConfig.from_path(project_path)
        if project_config is None:
            logger.warning("Skipping %s: could not load config", project_name)
            continue

        # Get builds to run for this project
        if selected_builds:
            # Use specified builds if they exist in this project
            builds = [b for b in selected_builds if b in project_config.builds]
        else:
            # Build ALL targets in the project
            builds = list(project_config.builds.keys())

        if not builds:
            logger.warning("Skipping %s: no matching builds", project_name)
            continue

        for build_name in builds:
            build_tasks.append((build_name, project_path, project_name))

    if not build_tasks:
        logger.error("No builds to run")
        raise typer.Exit(1)

    logger.info(
        "Building %d targets across %d projects (max %d concurrent)",
        len(build_tasks),
        len(projects),
        jobs,
    )

    # Use the first project's log directory as base, or create one in cwd
    logs_base = root / "build" / "logs"
    logs_base.mkdir(parents=True, exist_ok=True)

    logger.info("Saving logs to %s", logs_base / NOW)

    # Create and run parallel build manager
    manager = ParallelBuildManager(
        build_tasks,
        logs_base,
        max_workers=jobs,
        verbose=verbose,
    )

    results = manager.run_until_complete()

    # Generate summary
    summary_path = manager.generate_summary()

    # Check for failures
    failed = [name for name, code in results.items() if code != 0]
    if failed:
        logger.error(
            "Build failed! %d of %d targets failed",
            len(failed),
            len(build_tasks),
        )
        for name in failed[:10]:  # Show first 10 failures
            logger.error("  - %s", name)
        if len(failed) > 10:
            logger.error("  ... and %d more", len(failed) - 10)
        logger.info("See summary at: %s", summary_path)
        raise typer.Exit(1)
    else:
        logger.info("Build successful! 🚀 (%d targets)", len(build_tasks))
        logger.info("See summary at: %s", summary_path)


@capture("cli:build_start", "cli:build_end")
def build(
    entry: Annotated[
        str | None,
        typer.Argument(
            help="Path to the project directory or build target address "
            '("path_to.ato:Module")'
        ),
    ] = None,
    selected_builds: Annotated[
        list[str], typer.Option("--build", "-b", envvar="ATO_BUILD")
    ] = [],
    target: Annotated[
        list[str], typer.Option("--target", "-t", envvar="ATO_TARGET")
    ] = [],
    exclude_target: Annotated[
        list[str], typer.Option("--exclude-target", "-x", envvar="ATO_EXCLUDE_TARGET")
    ] = [],
    frozen: Annotated[
        bool | None,
        typer.Option(
            help="PCB must be rebuilt without changes. Useful in CI",
            envvar="ATO_FROZEN",
        ),
    ] = None,
    keep_picked_parts: bool | None = None,
    keep_net_names: bool | None = None,
    keep_designators: bool | None = None,
    standalone: bool = False,
    open_layout: Annotated[
        bool | None, typer.Option("--open", envvar="ATO_OPEN_LAYOUT")
    ] = None,
    parallel_worker: Annotated[
        bool, typer.Option("--parallel-worker", hidden=True)
    ] = False,
    all_projects: Annotated[
        bool,
        typer.Option(
            "--all",
            help="Build all projects in directory (recursively finds ato.yaml)",
        ),
    ] = False,
    jobs: Annotated[
        int,
        typer.Option(
            "--jobs",
            "-j",
            help=f"Max concurrent builds (default: {DEFAULT_WORKER_COUNT})",
        ),
    ] = DEFAULT_WORKER_COUNT,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Show full build output (runs sequentially)",
        ),
    ] = False,
):
    """
    Build the specified --target(s) or the targets specified by the build config.
    Optionally specify a different entrypoint with the argument ENTRY.

    Use --all to build all projects in a directory (e.g., `ato build --all`).

    eg. `ato build --target my_target path/to/source.ato:module.path`
    """
    from atopile.cli.logging_ import NOW
    from atopile.config import config
    from faebryk.libs.app.pcb import open_pcb
    from faebryk.libs.kicad.ipc import reload_pcb
    from faebryk.libs.project.dependencies import ProjectDependencies

    # Worker mode - run single build directly (no config needed yet)
    if parallel_worker or os.environ.get("ATO_PARALLEL_WORKER") == "1":
        config.apply_options(
            entry=entry,
            selected_builds=selected_builds,
            include_targets=target,
            exclude_targets=exclude_target,
            standalone=standalone,
            frozen=frozen,
            keep_picked_parts=keep_picked_parts,
            keep_net_names=keep_net_names,
            keep_designators=keep_designators,
        )
        _run_single_build(frozen=frozen)
        return

    # Multi-project mode: discover and build all projects
    if all_projects:
        _build_all_projects(
            root=Path.cwd(),
            jobs=jobs,
            frozen=frozen,
            selected_builds=selected_builds,
            verbose=verbose,
        )
        return

    # Single project mode
    config.apply_options(
        entry=entry,
        selected_builds=selected_builds,
        include_targets=target,
        exclude_targets=exclude_target,
        standalone=standalone,
        frozen=frozen,
        keep_picked_parts=keep_picked_parts,
        keep_net_names=keep_net_names,
        keep_designators=keep_designators,
    )

    deps = ProjectDependencies(sync_versions=False)
    if deps.not_installed_dependencies:
        logger.info("Installing missing dependencies")
        deps.install_missing_dependencies()

    if open_layout is not None:
        config.project.open_layout_on_build = open_layout

    # Get the list of builds to run
    build_names = list(config.selected_builds)

    logger.info("Saving logs to %s", config.project.paths.logs / NOW)

    # Create build tasks: (build_name, project_root, project_name)
    build_tasks: list[tuple[str, Path, str | None]] = [
        (name, config.project.paths.root, None) for name in build_names
    ]

    # Create and run parallel build manager
    manager = ParallelBuildManager(
        build_tasks,
        config.project.paths.logs,
        max_workers=jobs,
        verbose=verbose,
    )

    results = manager.run_until_complete()

    # Generate summary
    summary_path = manager.generate_summary()

    # Check for failures
    failed = [name for name, code in results.items() if code != 0]
    if failed:
        logger.error(
            "Build failed! %d of %d targets failed: %s",
            len(failed),
            len(build_names),
            ", ".join(failed),
        )
        logger.info("See summary at: %s", summary_path)
        raise typer.Exit(1)
    else:
        logger.info("Build successful! 🚀")
        logger.info("See summary at: %s", summary_path)

    # Open layouts if requested
    for build_name in build_names:
        build_cfg = config.project.builds[build_name]

        opened = False
        if config.should_open_layout_on_build():
            try:
                open_pcb(build_cfg.paths.layout)
                opened = True
            except FileNotFoundError:
                continue
            except RuntimeError:
                pass

        if not opened:
            try:
                reload_pcb(
                    build_cfg.paths.layout, backup_path=build_cfg.paths.output_base
                )
            except Exception as e:
                logger.warning(f"{e}\nReload pcb manually in KiCAD")
