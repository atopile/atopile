"""CLI command definition for `ato build`."""

from __future__ import annotations

import logging
import os
import queue
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Annotated, Callable

import pathvalidate
import typer
from rich.console import Console

from atopile.telemetry import capture

logger = logging.getLogger(__name__)

# Constants
DEFAULT_WORKER_COUNT = os.cpu_count() or 4


# Fixed port for the dashboard server - extension opens this directly
DASHBOARD_PORT = 8501


class Status(str, Enum):
    """Build status states."""

    QUEUED = "queued"
    BUILDING = "building"
    SUCCESS = "success"
    WARNING = "warning"
    FAILED = "failed"


@dataclass
class ProjectState:
    """Aggregate state for a project containing multiple builds."""

    builds: list[BuildProcess] = field(default_factory=list)
    status: Status = Status.QUEUED
    completed: int = 0
    failed: int = 0
    warnings: int = 0
    building: int = 0
    queued: int = 0
    total: int = 0
    current_build: str | None = None
    current_stage: str | None = None
    elapsed: float = 0.0
    log_dir: Path | None = None


def _status_rich_icon(status: Status | str) -> str:
    """Get Rich-formatted icon for status (for terminal display)."""
    icon_map = {
        Status.QUEUED: "[dim]○[/dim]",
        Status.BUILDING: "[blue]●[/blue]",
        Status.SUCCESS: "[green]✓[/green]",
        Status.WARNING: "[yellow]⚠[/yellow]",
        Status.FAILED: "[red]✗[/red]",
    }
    if isinstance(status, str):
        status = Status(status)
    return icon_map.get(status, "[dim]○[/dim]")


def _status_rich_text(status: Status | str, text: str) -> str:
    """Format text with Rich color markup for status."""
    color_map = {
        Status.QUEUED: "dim",
        Status.BUILDING: "blue",
        Status.SUCCESS: "green",
        Status.WARNING: "yellow",
        Status.FAILED: "red",
    }
    if isinstance(status, str):
        status = Status(status)
    color = color_map.get(status, "")
    return f"[{color}]{text}[/{color}]" if color else text


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


# Semantic status -> (icon, color)
_STATUS_STYLE = {
    "success": ("✓", "green"),
    "warning": ("⚠", "yellow"),
    "failed": ("✗", "red"),
    "running": ("●", "blue"),
}


def _format_stage_entry(entry: "StageEntry") -> str:
    """Render a completed stage entry with status color and counts."""
    icon, color = _STATUS_STYLE.get(entry.status, ("✓", "green"))
    counts = ""
    if entry.errors > 0:
        counts = f"({entry.errors}E"
        if entry.warnings > 0:
            counts += f",{entry.warnings}W"
        counts += ")"
    elif entry.warnings > 0:
        counts = f"({entry.warnings})"
    label = f"{icon}{counts} {entry.name} [{entry.duration:.1f}s]"
    return f"[{color}]{label}[/{color}]"


@dataclass
class StageEntry:
    """A completed build stage with timing and status."""

    name: str
    duration: float
    status: str  # "success", "warning", or "failed"
    warnings: int
    errors: int
    log_name: str


class BuildProcess:
    """Manages a single build subprocess."""

    def __init__(
        self,
        build_name: str,
        log_dir: Path,
        project_root: Path,
        project_name: str | None = None,
        targets: list[str] | None = None,
        exclude_targets: list[str] | None = None,
        frozen: bool | None = None,
        keep_picked_parts: bool | None = None,
        keep_net_names: bool | None = None,
        keep_designators: bool | None = None,
    ):
        self.name = build_name
        self.project_name = project_name  # For multi-project builds
        if project_name:
            self.display_name = f"{project_name}/{build_name}"
        else:
            self.display_name = build_name
        self.log_dir = log_dir
        self.project_root = project_root
        self.targets = targets or []
        self.exclude_targets = exclude_targets or []
        self.frozen = frozen
        self.keep_picked_parts = keep_picked_parts
        self.keep_net_names = keep_net_names
        self.keep_designators = keep_designators
        self.process: subprocess.Popen | None = None
        self.status_file: Path | None = None
        self.start_time: float = 0.0
        self.end_time: float = 0.0
        self.return_code: int | None = None
        self.current_stage: str = "Queued"
        self.warnings: int = 0
        self.errors: int = 0
        self._error_reported: bool = False  # Track if error was already printed
        self._stage_history: list[StageEntry] = []
        self._stage_start_time: float = 0.0
        self._stage_finalized: bool = False
        self._event_rfd: int | None = None
        self._event_wfd: int | None = None
        self._event_buffer: str = ""
        self._stage_printer: Callable[[StageEntry, Path | None], None] | None = None
        self._stream_thread: threading.Thread | None = None
        self._stream_console: Console | None = None
        self._buffer_stream_output: bool = False
        self._stream_buffer: list[str] = []

    def start(
        self,
        *,
        stream_output: bool = False,
        stream_console: Console | None = None,
        error_only_console: Console | None = None,
    ) -> None:
        """Start the build subprocess."""
        # Create log directory for this build
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.status_file = self.log_dir / "status.txt"

        # Initialize status file
        self.status_file.write_text("Starting...")
        self._setup_event_pipe()

        # Build the command - run ato build for just this target
        cmd = [
            sys.executable,
            "-m",
            "atopile",
            "build",
            "-b",
            self.name,
        ]

        # Copy environment and set IPC channels for worker subprocess
        env = os.environ.copy()
        env["ATO_BUILD_STATUS_FILE"] = str(self.status_file)
        if self._event_wfd is not None:
            env["ATO_BUILD_EVENT_FD"] = str(self._event_wfd)
        # Pass timestamp so worker writes logs to same directory as parent
        from atopile.cli.logging_ import NOW

        env["ATO_BUILD_TIMESTAMP"] = NOW

        # Pass build options to worker subprocess via environment variables
        # These are picked up by the corresponding CLI options
        if self.targets:
            env["ATO_TARGET"] = ",".join(self.targets)
        if self.exclude_targets:
            env["ATO_EXCLUDE_TARGET"] = ",".join(self.exclude_targets)
        if self.frozen is not None:
            env["ATO_FROZEN"] = "1" if self.frozen else "0"
        if self.keep_picked_parts is not None:
            env["ATO_KEEP_PICKED_PARTS"] = "1" if self.keep_picked_parts else "0"
        if self.keep_net_names is not None:
            env["ATO_KEEP_NET_NAMES"] = "1" if self.keep_net_names else "0"
        if self.keep_designators is not None:
            env["ATO_KEEP_DESIGNATORS"] = "1" if self.keep_designators else "0"
        if stream_output and error_only_console is None:
            env["ATO_VERBOSE_STREAM"] = "1"
            if stream_console is not None and stream_console.width:
                env["ATO_VERBOSE_WIDTH"] = str(stream_console.width)
        if error_only_console is not None:
            env["ATO_VERBOSE_ERRORS_ONLY"] = "1"

        self.start_time = time.time()

        if stream_output:
            self._stream_console = stream_console
            self._buffer_stream_output = error_only_console is not None
            self.process = subprocess.Popen(
                cmd,
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                pass_fds=self._get_pass_fds(),
            )
            self._start_output_stream()
        else:
            # No output capture needed - logs are written per-stage
            self.process = subprocess.Popen(
                cmd,
                cwd=self.project_root,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
                pass_fds=self._get_pass_fds(),
            )
        self._close_event_pipe_in_parent()

    def poll(self) -> int | None:
        """Check if process has finished. Returns exit code or None if still running."""
        if self.process is None:
            return None

        # Read current stage from status file
        self._read_status()
        self._read_event_pipe()

        ret = self.process.poll()
        if ret is not None and self.return_code is None:
            self.return_code = ret
            self.end_time = time.time()
            self._finalize_stage_history()
            if self._buffer_stream_output:
                self._stop_output_stream()
                self._flush_stream_buffer()
            self._count_log_issues()
        return ret

    def wait(self) -> int:
        """Wait for process to complete while reading stage events."""
        if self.process is None:
            return -1

        # Poll process and read stage events until complete
        while True:
            ret = self.process.poll()
            self._read_status()
            self._read_event_pipe()
            if ret is not None:
                break
            time.sleep(0.05)

        self.return_code = ret
        self.end_time = time.time()
        self._finalize_stage_history()
        self._stop_output_stream()
        if self._buffer_stream_output:
            self._flush_stream_buffer()
        self._count_log_issues()
        return ret

    def _read_status(self) -> None:
        """Read current stage from status file."""
        if not (self.status_file and self.status_file.exists()):
            return
        try:
            import re

            status = self.status_file.read_text().strip()
            # Strip Rich markup like [green]...[/green]
            status = re.sub(r"\[/?[a-z_]+\]", "", status)
            if status and status != self.current_stage:
                self._stage_start_time = time.time()
                self.current_stage = status
        except Exception:
            pass  # File might be being written to

    def _finalize_stage_history(self) -> None:
        if self._stage_finalized:
            return
        self._read_event_pipe()
        if self._event_rfd is not None:
            try:
                os.close(self._event_rfd)
            except OSError:
                pass
            self._event_rfd = None
        self._stage_finalized = True

    def _setup_event_pipe(self) -> None:
        try:
            rfd, wfd = os.pipe()
            os.set_blocking(rfd, False)
            os.set_inheritable(wfd, True)
            self._event_rfd = rfd
            self._event_wfd = wfd
        except Exception:
            self._event_rfd = None
            self._event_wfd = None

    def _get_pass_fds(self) -> tuple[int, ...]:
        if self._event_wfd is None:
            return ()
        return (self._event_wfd,)

    def _close_event_pipe_in_parent(self) -> None:
        if self._event_wfd is None:
            return
        try:
            os.close(self._event_wfd)
        except OSError:
            pass
        self._event_wfd = None

    def _read_event_pipe(self) -> None:
        if self._event_rfd is None:
            return
        while True:
            try:
                chunk = os.read(self._event_rfd, 4096)
            except BlockingIOError:
                break
            except OSError:
                break
            if not chunk:
                break
            self._event_buffer += chunk.decode(errors="ignore")
            while "\n" in self._event_buffer:
                line, _, rest = self._event_buffer.partition("\n")
                self._event_buffer = rest
                self._parse_event_line(line)

    def _parse_event_line(self, line: str) -> None:
        if not line:
            return
        parts = line.split("\t")
        if len(parts) < 6:
            return
        try:
            duration = float(parts[0])
        except ValueError:
            return
        log_name = parts[4].strip()
        description = "\t".join(parts[5:]).strip()
        if not description:
            return
        warnings = int(parts[2]) if parts[2].strip().isdigit() else 0
        errors = int(parts[3]) if parts[3].strip().isdigit() else 0
        # Derive semantic status from errors/warnings counts
        if errors > 0:
            status = "failed"
        elif warnings > 0:
            status = "warning"
        else:
            status = "success"
        self._stage_history.append(
            StageEntry(
                name=description,
                duration=duration,
                status=status,
                warnings=warnings,
                errors=errors,
                log_name=log_name,
            )
        )
        if self._stage_printer:
            self._stage_printer(
                self._stage_history[-1], self._stage_info_log_path(log_name)
            )

    def _stage_info_log_path(self, stage_name: str) -> Path | None:
        """Return the info log path for a stage, if available."""
        if not self.log_dir:
            return None
        sanitized = pathvalidate.sanitize_filename(stage_name)
        return self.log_dir / f"{sanitized}.info.log"

    def set_stage_printer(
        self, printer: Callable[[StageEntry, Path | None], None] | None
    ) -> None:
        """Set a callback invoked for each completed stage."""
        self._stage_printer = printer

    def format_stage_history(self, max_width: int, include_current: bool) -> str:
        """Return a multi-line stage history string, wrapped on step boundaries."""
        from rich.text import Text

        parts = [_format_stage_entry(e) for e in self._stage_history]
        if include_current and self.is_running and self.current_stage:
            elapsed = (
                time.time() - self._stage_start_time if self._stage_start_time else 0.0
            )
            icon, color = _STATUS_STYLE["running"]
            parts.append(
                f"[{color}]{icon} {self.current_stage} [{elapsed:.1f}s][/{color}]"
            )

        if not parts:
            return ""

        sep = " -> "
        lines: list[str] = []
        current = ""
        for part in parts:
            if not current:
                current = part
                continue
            candidate = f"{current}{sep}{part}"
            if Text.from_markup(candidate).cell_len <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = part
        if current:
            lines.append(current)

        return "\n".join(lines)

    def _count_log_issues(self) -> None:
        """Count warnings and errors from per-stage log files."""
        if not self.log_dir or not self.log_dir.exists():
            return

        try:
            warnings = 0
            errors = 0
            for log_file in self.log_dir.glob("*.log"):
                content = log_file.read_text().lower()
                warnings += content.count("warning")
                errors += content.count("error")
            self.warnings = warnings
            self.errors = errors
        except Exception:
            pass

    def _extract_from_log(self, detailed: bool = False) -> str | list[str]:
        """Extract error information from per-stage error log files.

        Args:
            detailed: If True, return list. If False, return string summary.
        """
        if not self.log_dir or not self.log_dir.exists():
            return [] if detailed else "Build failed (check logs)"

        try:
            # Collect error messages from *.error.log files
            error_lines = []
            for error_log in sorted(self.log_dir.glob("*.error.log")):
                content = error_log.read_text().strip()
                if content:
                    if detailed:
                        error_lines.extend(content.split("\n")[:10])
                    else:
                        # Return first error line for brief summary
                        first_line = content.split("\n")[0].strip()
                        if first_line:
                            truncated = first_line[:77] + "..."
                            return truncated if len(first_line) > 80 else first_line

            if detailed:
                return error_lines[:20]  # Limit to first 20 errors

            if not error_lines:
                return "Build failed (check error logs)"
            return error_lines[0]
        except Exception:
            return [] if detailed else "Build failed (check logs)"

    def get_error_message(self) -> str | None:
        """Extract a brief error summary for inline display."""
        result = self._extract_from_log(detailed=False)
        return result if isinstance(result, str) else None

    def get_error_details(self) -> list[str]:
        """Extract detailed error context for rich display."""
        result = self._extract_from_log(detailed=True)
        return result if isinstance(result, list) else []

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
    def status(self) -> Status:
        """Get current status."""
        if self.process is None:
            return Status.QUEUED
        elif self.return_code is None:
            return Status.BUILDING
        elif self.return_code == 0:
            return Status.WARNING if self.warnings > 0 else Status.SUCCESS
        else:
            return Status.FAILED

    def terminate(self) -> None:
        """Terminate the build process."""
        if self.process and self.return_code is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self._stop_output_stream()

    def _start_output_stream(self) -> None:
        if not self.process or self.process.stdout is None:
            return
        stdout = self.process.stdout

        def stream() -> None:
            while True:
                chunk = stdout.readline()
                if not chunk:
                    break
                text = chunk.decode(errors="replace")
                if self._buffer_stream_output:
                    self._stream_buffer.append(text)
                elif self._stream_console:
                    self._stream_console.file.write(text)
                    self._stream_console.file.flush()

        self._stream_thread = threading.Thread(target=stream, daemon=True)
        self._stream_thread.start()

    def _stop_output_stream(self) -> None:
        if self._stream_thread:
            self._stream_thread.join(timeout=1.0)
            self._stream_thread = None

    def _flush_stream_buffer(self) -> None:
        if not self._stream_buffer or not self._stream_console:
            self._stream_buffer.clear()
            return
        for text in self._stream_buffer:
            self._stream_console.file.write(text)
        self._stream_console.file.flush()
        self._stream_buffer.clear()


class ParallelBuildManager:
    """Manages multiple build processes with live display and job queue."""

    _STAGE_WIDTH = 22  # "Building... [123.4s]" fits in ~22 chars

    def __init__(
        self,
        # (build_name, project_root, project_name)
        build_tasks: list[tuple[str, Path, str | None]],
        logs_base: Path,
        max_workers: int = DEFAULT_WORKER_COUNT,
        verbose: bool = False,
        targets: list[str] | None = None,
        exclude_targets: list[str] | None = None,
        frozen: bool | None = None,
        keep_picked_parts: bool | None = None,
        keep_net_names: bool | None = None,
        keep_designators: bool | None = None,
    ):
        """
        Initialize the build manager.

        Args:
            build_tasks: List of (build_name, project_root, project_name) tuples
            logs_base: Base directory for logs
            max_workers: Maximum concurrent builds (default: CPU count)
            verbose: Show full output (runs sequentially, no live display)
            targets: Build targets to run (passed to workers via ATO_TARGET env var)
            exclude_targets: Build targets to exclude (passed via ATO_EXCLUDE_TARGET)
            frozen: If True, fail if PCB changes. Pass to workers via ATO_FROZEN env var
            keep_picked_parts: Keep previously picked parts from PCB
            keep_net_names: Keep net names from PCB
            keep_designators: Keep designators from PCB
        """
        self.build_tasks = build_tasks
        self.logs_base = logs_base
        self.max_workers = max_workers
        self.verbose = verbose
        self.targets = targets or []
        self.exclude_targets = exclude_targets or []
        self.frozen = frozen
        self.keep_picked_parts = keep_picked_parts
        self.keep_net_names = keep_net_names
        self.keep_designators = keep_designators

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
            bp = BuildProcess(
                build_name,
                log_dir,
                project_root,
                project_name,
                targets=self.targets,
                exclude_targets=self.exclude_targets,
                frozen=self.frozen,
                keep_picked_parts=self.keep_picked_parts,
                keep_net_names=self.keep_net_names,
                keep_designators=self.keep_designators,
            )
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

        # Set up summary directory and symlink early for live updates
        self._summary_dir = logs_base / "archive" / NOW
        self._summary_dir.mkdir(parents=True, exist_ok=True)
        self._summary_file = self._summary_dir / "summary.json"

        # Create latest symlink
        latest_link = logs_base / "latest"
        if latest_link.exists() and latest_link.is_symlink():
            latest_link.unlink()
        try:
            latest_link.symlink_to(self._summary_dir, target_is_directory=True)
        except OSError:
            pass

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

    def _fill_worker_slots(
        self,
        start_next_build: Callable[[], bool] | None = None,
        max_workers: int | None = None,
    ) -> None:
        """Start builds to fill available worker slots."""
        start_fn = start_next_build or self._start_next_build
        target_workers = max_workers or self.max_workers

        with self._lock:
            active_count = len(self._active_workers)

        while active_count < target_workers:
            if not start_fn():
                break
            with self._lock:
                active_count = len(self._active_workers)

    def _get_project_states(self) -> dict[str, ProjectState]:
        """Aggregate build states by project for multi-project view."""
        projects: dict[str, ProjectState] = {}

        for display_name, bp in self.processes.items():
            project = bp.project_name or display_name
            if project not in projects:
                projects[project] = ProjectState()

            p = projects[project]
            p.builds.append(bp)
            p.total += 1
            p.elapsed = max(p.elapsed, bp.elapsed)

            # Set log dir to project level (parent of build log dir)
            if bp.log_dir and bp.project_name:
                p.log_dir = bp.log_dir.parent

            status = bp.status
            if status == Status.BUILDING:
                p.building += 1
                p.current_build = bp.name
                p.current_stage = bp.current_stage
            elif status == Status.FAILED:
                p.failed += 1
                p.completed += 1
            elif status in (Status.SUCCESS, Status.WARNING):
                p.completed += 1
                if status == Status.WARNING:
                    p.warnings += 1
            elif status == Status.QUEUED:
                p.queued += 1

        # Determine aggregate status for each project
        for p in projects.values():
            if p.failed > 0:
                p.status = Status.FAILED
            elif p.building > 0:
                p.status = Status.BUILDING
            elif p.queued == p.total:
                p.status = Status.QUEUED
            elif p.warnings > 0:
                p.status = Status.WARNING
            else:
                p.status = Status.SUCCESS

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
        term_width = self._console.width or term_size.columns
        max_rows = max(term_height - 10, 10)  # At least 10 rows

        # Determine max target name length for dynamic column width
        max_name_len = max(len(bp.display_name) for bp in self.processes.values())
        target_width = min(max(max_name_len, 12), 40)  # Clamp between 12 and 40

        # Calculate available width for status column
        # Fixed widths: icon(1) + time(5) + padding(~10)
        fixed_width = 1 + target_width + 5 + 10
        status_width = max(self._STAGE_WIDTH, term_width - fixed_width)

        table = self._Table(
            show_header=True,
            header_style="bold dim",
            box=SIMPLE,
            padding=(0, 1),
            expand=True,
        )

        table.add_column("", width=1)  # Status icon
        table.add_column("Target", width=target_width, style="cyan")
        table.add_column("Status", width=status_width, no_wrap=True, overflow="ignore")
        table.add_column("Time", width=5, justify="right")

        with self._lock:
            rows_shown = 0
            hidden_queued = 0

            for display_name, bp in self.processes.items():
                status = bp.status

                # If we've hit the limit, only skip queued items
                if rows_shown >= max_rows:
                    if status == Status.QUEUED:
                        hidden_queued += 1
                        continue
                    # Always show non-queued items (building/failed/completed)

                icon = _status_rich_icon(status)

                # Format stage text with colors
                if status == Status.BUILDING:
                    stage_name = bp.format_stage_history(
                        status_width, include_current=True
                    )
                    if not stage_name:
                        stage_name = bp.current_stage or "Building..."
                        stage_text = _status_rich_text(status, stage_name)
                    else:
                        stage_text = stage_name
                elif status in (Status.SUCCESS, Status.WARNING):
                    stage_name = bp.format_stage_history(
                        status_width, include_current=False
                    )
                    if stage_name:
                        stage_text = stage_name
                    else:
                        stage_text = _status_rich_text(Status.SUCCESS, "Completed")
                elif status == Status.FAILED:
                    stage_name = bp.format_stage_history(
                        status_width, include_current=False
                    )
                    if stage_name:
                        stage_text = stage_name
                    else:
                        stage_text = _status_rich_text(status, "Failed")
                elif status == Status.QUEUED:
                    stage_text = _status_rich_text(status, "Queued")
                else:
                    stage_text = _status_rich_text(Status.QUEUED, "Waiting...")

                # Format time
                if status == Status.QUEUED:
                    time_text = _status_rich_text(status, "-")
                else:
                    time_text = _status_rich_text(status, f"{int(bp.elapsed)}s")

                table.add_row(icon, display_name, stage_text, time_text)
                rows_shown += 1
                if rows_shown < max_rows:
                    table.add_row("", "", "", "")

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
        term_width = self._console.width or term_size.columns
        max_rows = max(term_height - 10, 10)

        # Find max project name length
        projects = self._get_project_states()
        max_name_len = max(len(name) for name in projects.keys())
        project_width = min(max(max_name_len, 12), 40)

        # Calculate available width for status column
        # Fixed widths: icon(1) + time(5) + padding(~10)
        fixed_width = 1 + project_width + 5 + 10
        status_width = max(self._STAGE_WIDTH + 12, term_width - fixed_width)

        table = self._Table(
            show_header=True,
            header_style="bold dim",
            box=SIMPLE,
            padding=(0, 1),
            expand=True,
        )

        table.add_column("", width=1)  # Status icon
        table.add_column("Project", width=project_width, style="cyan")
        table.add_column("Status", width=status_width, no_wrap=True, overflow="ignore")
        table.add_column("Time", width=5, justify="right")

        rows_shown = 0
        hidden_queued = 0

        for project_name, p in projects.items():
            status = p.status

            # Limit rows, but always show non-queued
            if rows_shown >= max_rows:
                if status == Status.QUEUED:
                    hidden_queued += 1
                    continue

            icon = _status_rich_icon(status)

            # Build status text showing progress and current activity
            if status == Status.BUILDING:
                stage = p.current_stage or "Building"
                build_name = p.current_build or ""
                progress = f"{p.completed}/{p.total}"

                # Calculate available space for stage based on status_width
                # Format: "{build_name} {progress} {stage}"
                # Reserve: build_name(max 10) + space + progress + space
                reserved = min(len(build_name), 10) + 1 + len(progress) + 1
                max_stage_len = max(status_width - reserved, 10)

                if len(stage) > max_stage_len:
                    stage = stage[: max_stage_len - 3] + "..."
                if len(build_name) > 10:
                    build_name = build_name[:8] + ".."

                colored_name = _status_rich_text(status, build_name)
                status_text = f"{colored_name} {progress} {stage}"
            elif status == Status.FAILED:
                failed_text = _status_rich_text(status, f"{p.failed} failed")
                status_text = f"{failed_text}, {p.completed - p.failed}/{p.total} done"
            elif status == Status.WARNING:
                progress_text = f"{p.completed}/{p.total} done"
                status_text = _status_rich_text(status, progress_text)
            elif status == Status.SUCCESS:
                progress_text = f"{p.completed}/{p.total} done"
                status_text = _status_rich_text(status, progress_text)
            elif status == Status.QUEUED:
                status_text = _status_rich_text(status, f"Queued ({p.total} builds)")
            else:
                status_text = f"{p.completed}/{p.total}"

            # Time
            if status == Status.QUEUED:
                time_text = _status_rich_text(status, "-")
            else:
                time_text = _status_rich_text(status, f"{int(p.elapsed)}s")

            table.add_row(icon, project_name, status_text, time_text)
            rows_shown += 1
            if rows_shown < max_rows:
                table.add_row("", "", "", "")

        if hidden_queued > 0:
            table.add_row(
                "[dim]...[/dim]",
                f"[dim]+{hidden_queued} more queued[/dim]",
                "",
                "",
            )

        return table

    def _render_summary(self) -> str:
        """Render summary line."""
        with self._lock:
            queued = sum(
                1 for bp in self.processes.values() if bp.status == Status.QUEUED
            )
            building = sum(
                1 for bp in self.processes.values() if bp.status == Status.BUILDING
            )
            completed = sum(
                1
                for bp in self.processes.values()
                if bp.status in (Status.SUCCESS, Status.WARNING)
            )
            failed = sum(
                1 for bp in self.processes.values() if bp.status == Status.FAILED
            )
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

    _VERBOSE_INDENT = 20

    def _print_verbose_stage(self, entry: StageEntry, log_path: Path | None) -> None:
        """Print a single verbose stage line with its log path."""
        log_text = ""
        if log_path is not None:
            try:
                log_path = log_path.relative_to(Path.cwd())
            except ValueError:
                pass
            log_text = f"  {log_path}"

        self._console.print(
            f"{'':>{self._VERBOSE_INDENT}}{_format_stage_entry(entry)}{log_text}"
        )

    def _print_failure_details(
        self, display_name: str, bp: "BuildProcess", console: "Console"
    ) -> None:
        """Print failure details similar to parallel mode output."""
        error_details = bp.get_error_details()
        if not error_details and bp.log_dir:
            error_details = self._extract_log_messages(bp.log_dir, "error")
        error_msg = bp.get_error_message()

        console.print(f"[red bold]✗ {display_name}[/red bold]")
        if error_details:
            for line in error_details:
                line = self._linkify_paths(line)
                console.print(f"  {line}")
        elif error_msg:
            console.print(f"  {error_msg}")

        if bp.log_dir and bp.log_dir.exists():
            log_dir_path = bp.log_dir.absolute()
            uri = self._make_file_uri(log_dir_path)
            link = f"[link={uri}]View logs[/link]"
            console.print(f"  [dim]→ {link}[/dim]")
        console.print("")

    def _print_warning_details(
        self, display_name: str, bp: "BuildProcess", console: "Console"
    ) -> None:
        """Print warning details above the build table."""
        warning_details: list[str] = []
        if bp.log_dir:
            warning_details = self._extract_log_messages(bp.log_dir, "warning")

        if not warning_details:
            return

        console.print(f"[yellow bold]⚠ {display_name}[/yellow bold]")
        for line in warning_details:
            line = self._linkify_paths(line)
            console.print(f"  {line}")
        console.print("")

    def _display_loop(self) -> None:
        """Background thread that updates display."""
        from rich.console import Group

        while not self._stop_display.is_set():
            if self._live:
                with self._display_lock:
                    table = self._render_table()
                    summary = self._render_summary()
                    self._live.update(Group(table, "", summary))
            self._write_live_summary()
            time.sleep(0.5)

    def _write_live_summary(self) -> None:
        """Write current build state to JSON summary file."""
        import json

        # Collect all build data
        builds = [self._get_build_data(bp) for bp in self.processes.values()]

        # Aggregate stats
        total = len(self.processes)
        success = sum(
            1
            for bp in self.processes.values()
            if bp.status in (Status.SUCCESS, Status.WARNING)
        )
        failed = sum(1 for bp in self.processes.values() if bp.status == Status.FAILED)

        summary = {
            "timestamp": self._now,
            "totals": {
                "builds": total,
                "successful": success,
                "failed": failed,
                "warnings": sum(bp.warnings for bp in self.processes.values()),
                "errors": sum(bp.errors for bp in self.processes.values()),
            },
            "builds": builds,
        }

        try:
            self._summary_file.write_text(json.dumps(summary, indent=2))
        except Exception:
            pass  # Don't fail the build if we can't write summary

    def run_until_complete(self) -> dict[str, int]:
        """
        Run all builds until complete, showing live progress.

        Uses a queue to limit concurrent builds to max_workers.
        In verbose mode, runs sequentially with full output.

        Returns dict of display_name -> exit_code.
        """
        # Write initial summary with all builds queued
        self._write_live_summary()

        if self.verbose:
            return self._run_verbose()

        results = self._run_parallel()

        # Errors are now printed above the table during the live display,
        # so we don't need to print them again here.

        return results

    def _print_build_result(
        self,
        display_name: str,
        bp: "BuildProcess",
        ret: int,
        console: "Console",
        show_failure_details: bool,
    ) -> None:
        """Print per-build success/failure summary with details."""
        if ret == 0:
            if bp.warnings > 0:
                console.print(
                    f"[yellow]⚠ {display_name} completed with "
                    f"{bp.warnings} warning(s)[/yellow]"
                )
            else:
                console.print(f"[green]✓ {display_name} completed[/green]")
        else:
            if show_failure_details:
                self._print_failure_details(display_name, bp, console)
            console.print(f"[red]✗ {display_name} failed[/red]")

    def _run_verbose(self) -> dict[str, int]:
        """Run builds sequentially with full output visible."""
        console = self._get_full_width_console()
        return self._run_parallel(
            live=False,
            max_workers=1,
            print_headers=True,
            print_results=True,
            stage_printer=self._print_verbose_stage,
            console=console,
            stream_output=True,
            show_failure_details=False,
            error_only_console=console,
        )

    @staticmethod
    def _get_full_width_console() -> "Console":
        import shutil

        from rich.console import Console

        width = shutil.get_terminal_size(fallback=(120, 24)).columns
        return Console(width=width)

    def _run_parallel(
        self,
        *,
        live: bool = True,
        max_workers: int | None = None,
        print_headers: bool = False,
        print_results: bool = False,
        stage_printer: Callable[[StageEntry, Path | None], None] | None = None,
        console: Console | None = None,
        stream_output: bool = False,
        show_failure_details: bool = True,
        error_only_console: Console | None = None,
    ) -> dict[str, int]:
        """Run builds with an optional live progress display."""
        from rich.console import Group
        from rich.live import Live

        results: dict[str, int] = {}
        console = console or self._console

        def start_next_build() -> bool:
            try:
                display_name = self._task_queue.get_nowait()
            except queue.Empty:
                return False

            bp = self.processes[display_name]
            if print_headers:
                console.print(f"[bold cyan]▶ Building {display_name}[/bold cyan]")
                console.print(f"[dim]  Logs: {bp.log_dir}[/dim]\n")
            if stage_printer is not None:
                bp.set_stage_printer(stage_printer)
            bp.start(
                stream_output=stream_output,
                stream_console=console,
                error_only_console=error_only_console,
            )
            with self._lock:
                self._active_workers.add(display_name)
            return True

        def run_loop(console: "Console") -> dict[str, int]:
            try:
                # Fill initial worker slots
                self._fill_worker_slots(
                    start_next_build=start_next_build, max_workers=max_workers
                )

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

                                if stage_printer is not None:
                                    bp.set_stage_printer(None)

                                if print_results:
                                    self._print_build_result(
                                        display_name,
                                        bp,
                                        ret,
                                        console,
                                        show_failure_details,
                                    )
                                    bp._error_reported = True
                                elif ret != 0 and not bp._error_reported:
                                    # Print error details above the live table
                                    self._print_failure_details(
                                        display_name, bp, console
                                    )
                                    bp._error_reported = True
                                elif ret == 0 and bp.warnings > 0:
                                    # Print warning details above the live table
                                    self._print_warning_details(
                                        display_name, bp, console
                                    )

                        # Remove completed builds from active set
                        for name in completed_this_round:
                            self._active_workers.discard(name)

                    # Fill any freed worker slots
                    if completed_this_round:
                        self._fill_worker_slots(
                            start_next_build=start_next_build, max_workers=max_workers
                        )

                    # Check if all builds are done
                    all_done = (
                        len(results) == len(self.processes) and self._task_queue.empty()
                    )
                    if all_done:
                        break

                    # Update JSON summary (verbose mode; live mode uses _display_loop)
                    if not live:
                        self._write_live_summary()

                    time.sleep(0.5)

            except KeyboardInterrupt:
                # Terminate all processes on interrupt
                for bp in self.processes.values():
                    bp.terminate()
                raise

            return results

        if live:
            with Live(
                self._render_table(),
                console=console,
                refresh_per_second=2,
            ) as live_display:
                self._live = live_display
                self._stop_display.clear()

                # Start display update thread
                self._display_thread = threading.Thread(
                    target=self._display_loop, daemon=True
                )
                self._display_thread.start()

                try:
                    run_loop(live_display.console)
                finally:
                    self._stop_display.set()
                    if self._display_thread:
                        self._display_thread.join(timeout=1.0)

                # Final update
                table = self._render_table()
                summary = self._render_summary()
                live_display.update(Group(table, "", summary))
        else:
            run_loop(self._console)

        return results

    def _extract_log_messages(self, log_dir: Path, level: str) -> list[str]:
        """Extract messages from per-stage log files of a specific level."""
        messages = []

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

    def _get_build_data(self, bp: "BuildProcess") -> dict:
        """Collect all data for a single build as a dictionary."""
        data = {
            "name": bp.name,
            "display_name": bp.display_name,
            "project_name": bp.project_name,
            "status": bp.status.value,
            "elapsed_seconds": round(bp.elapsed, 2),
            "warnings": bp.warnings,
            "errors": bp.errors,
            "return_code": bp.return_code,
        }

        # Add log dir
        if bp.log_dir and bp.log_dir.exists():
            data["log_dir"] = str(bp.log_dir)

            # Collect all log files grouped by stage and log type
            log_files_by_stage: dict[str, dict[str, str]] = {}
            for log_file in sorted(bp.log_dir.glob("*.log")):
                parts = log_file.stem.split(".")
                if len(parts) >= 2:
                    stage = parts[0]
                    log_type = parts[1] if len(parts) >= 2 else "log"
                    if stage not in log_files_by_stage:
                        log_files_by_stage[stage] = {}
                    log_files_by_stage[stage][log_type] = str(log_file)

            # Add timing data from stage history with associated log files
            if bp._stage_history:
                data["stages"] = [
                    {
                        "name": entry.name,
                        "elapsed_seconds": round(entry.duration, 3),
                        "status": entry.status,
                        "warnings": entry.warnings,
                        "errors": entry.errors,
                        "log_files": log_files_by_stage.get(entry.log_name, {}),
                    }
                    for entry in bp._stage_history
                ]

        return data

    def generate_summary(self) -> Path:
        """Generate final build summary as JSON file."""
        self._write_live_summary()
        return self._summary_file


def _run_single_build() -> None:
    """
    Run a single build target (worker mode).

    This is called when IPC env vars are set by the parent process.
    """
    from atopile import buildutil
    from atopile.config import config

    # Get the single build target from config
    build_names = list(config.selected_builds)
    if len(build_names) != 1:
        raise RuntimeError(
            f"Worker mode expects exactly 1 build, got {len(build_names)}"
        )

    build_name = build_names[0]

    from atopile.cli.excepthook import install_worker_excepthook

    with config.select_build(build_name):
        install_worker_excepthook()
        buildutil.build()


def _build_all_projects(
    root: Path,
    jobs: int,
    frozen: bool | None = None,
    selected_builds: list[str] | None = None,
    verbose: bool = False,
    targets: list[str] | None = None,
    exclude_targets: list[str] | None = None,
    keep_picked_parts: bool | None = None,
    keep_net_names: bool | None = None,
    keep_designators: bool | None = None,
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
        targets=targets,
        exclude_targets=exclude_targets,
        frozen=frozen,
        keep_picked_parts=keep_picked_parts,
        keep_net_names=keep_net_names,
        keep_designators=keep_designators,
    )

    results = manager.run_until_complete()

    # Generate summary
    summary_path = manager.generate_summary()

    failed = [name for name, code in results.items() if code != 0]
    exit_code = _report_build_results(
        summary_path=summary_path,
        failed=failed,
        total=len(build_tasks),
        failed_names=failed[:10],
    )
    if exit_code != 0:
        raise typer.Exit(exit_code)


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
    keep_picked_parts: Annotated[
        bool | None,
        typer.Option(
            help="Keep previously picked parts from PCB",
            envvar="ATO_KEEP_PICKED_PARTS",
        ),
    ] = None,
    keep_net_names: Annotated[
        bool | None,
        typer.Option(
            help="Keep net names from PCB",
            envvar="ATO_KEEP_NET_NAMES",
        ),
    ] = None,
    keep_designators: Annotated[
        bool | None,
        typer.Option(
            help="Keep designators from PCB",
            envvar="ATO_KEEP_DESIGNATORS",
        ),
    ] = None,
    standalone: bool = False,
    open_layout: Annotated[
        bool | None, typer.Option("--open", envvar="ATO_OPEN_LAYOUT")
    ] = None,
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
    ui: Annotated[
        bool,
        typer.Option(
            "--ui",
            help="Open a live build dashboard in your browser",
            envvar="ATO_UI",
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

    if verbose:
        logging.getLogger().setLevel(logging.INFO)

    # Worker mode - run single build directly (no config needed yet)
    if os.environ.get("ATO_BUILD_EVENT_FD") or os.environ.get("ATO_BUILD_STATUS_FILE"):
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

        # Install dependencies if needed (same as single project mode)
        deps = ProjectDependencies(sync_versions=False)
        if deps.not_installed_dependencies:
            logger.info("Installing missing dependencies")
            for dep in deps.not_installed_dependencies:
                try:  # protect against parallel worker race condition
                    assert dep.dist is not None
                    from faebryk.libs.project.dependencies import _log_add_package

                    _log_add_package(dep.identifier, dep.dist.version)
                    dep.dist.install(dep.target_path)
                except FileExistsError:
                    logger.debug(
                        f"Dependency {dep.identifier} already exists at "
                        f"{dep.target_path}"
                    )

        _run_single_build()
        return

    # Multi-project mode: discover and build all projects
    if all_projects:
        _build_all_projects(
            root=Path.cwd(),
            jobs=jobs,
            frozen=frozen,
            selected_builds=selected_builds,
            verbose=verbose,
            targets=target,
            exclude_targets=exclude_target,
            keep_picked_parts=keep_picked_parts,
            keep_net_names=keep_net_names,
            keep_designators=keep_designators,
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
        targets=target,
        exclude_targets=exclude_target,
        frozen=frozen,
        keep_picked_parts=keep_picked_parts,
        keep_net_names=keep_net_names,
        keep_designators=keep_designators,
    )

    # Start dashboard server if enabled (and not in verbose mode)
    # Uses fixed port so extension can open webview immediately
    dashboard_server = None
    dashboard_url = None
    if ui and not verbose:
        try:
            from atopile.dashboard import is_dashboard_built
            from atopile.dashboard.server import start_dashboard_server

            if is_dashboard_built():
                dashboard_server, dashboard_url = start_dashboard_server(
                    manager._summary_file,
                    manager.logs_base,
                    port=DASHBOARD_PORT,
                )
                logger.info("Dashboard available at: %s", dashboard_url)
            else:
                logger.debug("Dashboard not built, skipping")
        except Exception as e:
            logger.debug("Failed to start dashboard: %s", e)

    try:
        results = manager.run_until_complete()
    except KeyboardInterrupt:
        # Handle Ctrl+C during build
        logger.info("Build interrupted")
        if dashboard_server:
            dashboard_server.shutdown()
        raise typer.Exit(1)

    # Generate summary
    summary_path = manager.generate_summary()

    failed = [name for name, code in results.items() if code != 0]

    # Report results (don't exit yet if dashboard is running)
    build_exit_code = _report_build_results(
        summary_path=summary_path,
        failed=failed,
        total=len(build_names),
        failed_names=failed,
    )

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

    # Keep dashboard server running after build completes
    if dashboard_server:
        logger.info("Dashboard still available at: %s", dashboard_url)
        logger.info("Press Ctrl+C to stop")
        try:
            # Wait until interrupted (cross-platform)
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down dashboard...")
        finally:
            dashboard_server.shutdown()

    # Exit with appropriate code after dashboard is closed
    if build_exit_code != 0:
        raise typer.Exit(build_exit_code)


def _report_build_results(
    *,
    summary_path: Path,
    failed: list[str],
    total: int,
    failed_names: list[str] | None = None,
) -> int:
    """Report build results and return exit code (0 for success, 1 for failure)."""
    if failed:
        from atopile.cli.excepthook import log_discord_banner

        log_discord_banner()
        logger.info("See summary at: %s", summary_path)
        logger.error("Build failed! %d of %d targets failed", len(failed), total)
        if failed_names:
            for name in failed_names:
                logger.error("  - %s", name)
        remaining = len(failed) - (len(failed_names) if failed_names else 0)
        if remaining > 0:
            logger.error("  ... and %d more", remaining)
        return 1

    if total > 1:
        logger.info("Build successful! 🚀 (%d targets)", total)
    else:
        logger.info("Build successful! 🚀")
    logger.info("See summary at: %s", summary_path)
    return 0
