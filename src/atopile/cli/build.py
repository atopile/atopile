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
from typing import Callable

import typer
from rich.console import Console
from typing_extensions import Annotated

from atopile.buildutil import generate_build_id
from atopile.dataclasses import (
    Build,
    BuildReport,
    BuildStatus,
    ProjectState,
    StageCompleteEvent,
    StageStatus,
)
from atopile.logging import NOW, get_logger
from atopile.logging_utils import status_rich_icon, status_rich_text
from atopile.telemetry import capture

logger = get_logger(__name__)

# Constants
DEFAULT_WORKER_COUNT = os.cpu_count() or 4


# status_rich_icon and status_rich_text are imported from atopile.logging_utils


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
    StageStatus.SUCCESS: ("✓", "green"),
    StageStatus.WARNING: ("⚠", "yellow"),
    StageStatus.FAILED: ("✗", "red"),
    StageStatus.ERROR: ("✗", "red"),  # Error is similar to failed
    StageStatus.RUNNING: ("●", "blue"),
    StageStatus.PENDING: ("○", "dim"),
    StageStatus.SKIPPED: ("⊘", "dim"),
}


def _format_stage_entry(entry: StageCompleteEvent) -> str:
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
    label = f"{icon}{counts} {entry.description} [{entry.duration:.1f}s]"
    return f"[{color}]{label}[/{color}]"


class BuildProcess:
    """Manages a single build subprocess."""

    def __init__(
        self,
        build_name: str,
        project_root: Path,
        project_name: str | None = None,
        targets: list[str] | None = None,
        exclude_targets: list[str] | None = None,
        frozen: bool | None = None,
        keep_picked_parts: bool | None = None,
        keep_net_names: bool | None = None,
        keep_designators: bool | None = None,
        verbose: bool = False,
    ):
        self.name = build_name
        self.project_name = project_name  # For multi-project builds
        if project_name:
            self.display_name = f"{project_name}/{build_name}"
        else:
            self.display_name = build_name
        self.project_root = project_root
        self.targets = targets or []
        self.exclude_targets = exclude_targets or []
        self.frozen = frozen
        self.keep_picked_parts = keep_picked_parts
        self.keep_net_names = keep_net_names
        self.keep_designators = keep_designators
        self.verbose = verbose
        self.process: subprocess.Popen | None = None
        self.start_time: float = 0.0
        self.end_time: float = 0.0
        self.return_code: int | None = None
        self.current_stage: str = "Queued"
        self.warnings: int = 0
        self.errors: int = 0
        self._error_reported: bool = False  # Track if error was already printed
        self._stage_history: list[StageCompleteEvent] = []
        self._stage_finalized: bool = False
        self._stage_printer: (
            Callable[[StageCompleteEvent, Path | None], None] | None
        ) = None
        self.build_id: str | None = None

    def start(self) -> None:
        """Start the build subprocess."""
        # Build the command - run ato build for just this target
        cmd = [
            sys.executable,
            "-m",
            "atopile",
            "build",
            "-b",
            self.name,
        ]

        # Copy environment and set worker mode
        env = os.environ.copy()
        env["ATO_BUILD_WORKER"] = "1"

        # Use existing timestamp/build_id if passed from server, otherwise generate
        # This ensures server-triggered builds use consistent IDs across workers
        if "ATO_BUILD_TIMESTAMP" not in env:
            env["ATO_BUILD_TIMESTAMP"] = NOW
        if "ATO_BUILD_ID" not in env:
            # Use pre-generated build_id if available (from ParallelBuildManager)
            if self.build_id:
                env["ATO_BUILD_ID"] = self.build_id
            else:
                project_path = str(self.project_root.resolve())
                timestamp = env["ATO_BUILD_TIMESTAMP"]
                build_id = generate_build_id(project_path, self.name, timestamp)
                env["ATO_BUILD_ID"] = build_id
                self.build_id = build_id
        else:
            # Store build_id from environment for display purposes
            self.build_id = env["ATO_BUILD_ID"]

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
        if self.verbose:
            env["ATO_VERBOSE"] = "1"
        self.start_time = time.time()

        # Enable faulthandler in workers for crash debugging
        # ATO_SAFE is set by --safe flag or can be set explicitly
        preexec_fn = None
        if os.environ.get("ATO_SAFE"):
            env["ATO_SAFE"] = "1"

            def enable_core_dumps():
                import resource

                try:
                    resource.setrlimit(
                        resource.RLIMIT_CORE,
                        (resource.RLIM_INFINITY, resource.RLIM_INFINITY),
                    )
                except (ValueError, OSError):
                    pass

            preexec_fn = enable_core_dumps

        # Keep stdout/stderr so worker exceptions are visible immediately.
        self.process = subprocess.Popen(
            cmd,
            cwd=self.project_root,
            env=env,
            preexec_fn=preexec_fn,
        )

    def poll(self) -> int | None:
        """Check if process has finished. Returns exit code or None if still running."""
        if self.process is None:
            return None

        # Read stage progress from the build history DB
        self._read_stages_from_db()

        ret = self.process.poll()
        if ret is not None and self.return_code is None:
            self.return_code = ret
            self.end_time = time.time()
            self._finalize_stage_history()
        return ret

    def _finalize_stage_history(self) -> None:
        if self._stage_finalized:
            return
        self._read_stages_from_db()
        self._stage_finalized = True

    def _read_stages_from_db(self) -> None:
        """Read stage data from the build history database."""
        if not self.build_id:
            return
        try:
            from atopile.model.build_history import get_build_info_by_id

            build_info = get_build_info_by_id(self.build_id)
            if not build_info:
                return
            stages = build_info.stages or []
            if len(stages) <= len(self._stage_history):
                return  # No new stages

            # Convert new DB stages to StageCompleteEvent objects
            for stage_dict in stages[len(self._stage_history) :]:
                event = StageCompleteEvent(
                    duration=stage_dict.get("elapsed_seconds", 0.0),
                    status=StageStatus(stage_dict.get("status", "success")),
                    infos=stage_dict.get("infos", 0),
                    warnings=stage_dict.get("warnings", 0),
                    errors=stage_dict.get("errors", 0),
                    alerts=stage_dict.get("alerts", 0),
                    log_name=stage_dict.get("stage_id", ""),
                    description=stage_dict.get("name", ""),
                )
                self.warnings += event.warnings
                self.errors += event.errors
                self._stage_history.append(event)
                if self._stage_printer:
                    self._stage_printer(
                        event,
                        self._stage_info_log_path(event.log_name),
                    )
        except Exception:
            pass  # Don't fail polling if DB read fails

    def _stage_info_log_path(self, stage_name: str) -> Path | None:
        """Return the log path for a build (central SQLite database)."""
        from atopile.logging import BuildLogger

        return BuildLogger.get_log_db()

    def set_stage_printer(
        self, printer: Callable[[StageCompleteEvent, Path | None], None] | None
    ) -> None:
        """Set a callback invoked for each completed stage."""
        self._stage_printer = printer

    def report(self) -> BuildReport:
        return BuildReport(
            name=self.display_name,
            status=self.status,
            warnings=self.warnings,
            errors=self.errors,
            stages=self._stage_history,
        )

    def format_stage_history(self, max_width: int, include_current: bool) -> str:
        """Return a multi-line stage history string, wrapped on step boundaries."""
        from rich.text import Text

        parts = [_format_stage_entry(e) for e in self._stage_history]
        if include_current and self.is_running and self.current_stage:
            # Approximate current stage time from total elapsed minus completed
            completed_time = sum(e.duration for e in self._stage_history)
            elapsed = max(0.0, self.elapsed - completed_time)
            icon, color = _STATUS_STYLE[StageStatus.RUNNING]
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
    def status(self) -> BuildStatus:
        """Get current status."""
        if self.process is None:
            return BuildStatus.QUEUED
        elif self.return_code is None:
            return BuildStatus.BUILDING
        else:
            return BuildStatus.from_return_code(self.return_code, self.warnings)

    def terminate(self) -> None:
        """Terminate the build process."""
        if self.process and self.return_code is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()


class ParallelBuildManager:
    """Manages multiple build processes with job queue."""

    _STAGE_WIDTH = 22  # "Building... [123.4s]" fits in ~22 chars

    def __init__(
        self,
        # (build_name, project_root, project_name)
        build_tasks: list[tuple[str, Path, str | None]],
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

        self._now = NOW

        for build_name, project_root, project_name in build_tasks:
            if project_name:
                display_name = f"{project_name}/{build_name}"
            else:
                display_name = build_name
            bp = BuildProcess(
                build_name,
                project_root,
                project_name,
                targets=self.targets,
                exclude_targets=self.exclude_targets,
                frozen=self.frozen,
                keep_picked_parts=self.keep_picked_parts,
                keep_net_names=self.keep_net_names,
                keep_designators=self.keep_designators,
                verbose=self.verbose,
            )
            # Pre-generate build_id so it's available for display before start()
            project_path = str(project_root.resolve())
            bp.build_id = generate_build_id(project_path, build_name, self._now)
            self.processes[display_name] = bp
            self._task_queue.put(display_name)

        self._lock = threading.Lock()
        self._active_workers: set[str] = set()

        # Import rich for display
        from rich.console import Console
        from rich.table import Table

        self._console = Console()
        self._Table = Table

        # Write initial summary immediately so UI shows builds as "queued" right away
        # This reduces delay between when a build is requested and when the UI updates
        self._write_live_summary()

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

            status = bp.status
            if status == BuildStatus.BUILDING:
                p.building += 1
                p.current_build = bp.name
                p.current_stage = bp.current_stage
            elif status == BuildStatus.FAILED:
                p.failed += 1
                p.completed += 1
            elif status in (BuildStatus.SUCCESS, BuildStatus.WARNING):
                p.completed += 1
                if status == BuildStatus.WARNING:
                    p.warnings += 1
            elif status == BuildStatus.QUEUED:
                p.queued += 1

        # Determine aggregate status for each project
        for p in projects.values():
            if p.failed > 0:
                p.status = BuildStatus.FAILED
            elif p.building > 0:
                p.status = BuildStatus.BUILDING
            elif p.queued == p.total:
                p.status = BuildStatus.QUEUED
            elif p.warnings > 0:
                p.status = BuildStatus.WARNING
            else:
                p.status = BuildStatus.SUCCESS

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
                    if status == BuildStatus.QUEUED:
                        hidden_queued += 1
                        continue
                    # Always show non-queued items (building/failed/completed)

                icon = status_rich_icon(status)

                # Format stage text with colors
                if status == BuildStatus.BUILDING:
                    stage_name = bp.format_stage_history(
                        status_width, include_current=True
                    )
                    if not stage_name:
                        stage_name = bp.current_stage or "Building..."
                        stage_text = status_rich_text(status, stage_name)
                    else:
                        stage_text = stage_name
                elif status in (BuildStatus.SUCCESS, BuildStatus.WARNING):
                    stage_name = bp.format_stage_history(
                        status_width, include_current=False
                    )
                    if stage_name:
                        stage_text = stage_name
                    else:
                        stage_text = status_rich_text(BuildStatus.SUCCESS, "Completed")
                elif status == BuildStatus.FAILED:
                    stage_name = bp.format_stage_history(
                        status_width, include_current=False
                    )
                    if stage_name:
                        stage_text = stage_name
                    else:
                        stage_text = status_rich_text(status, "Failed")
                elif status == BuildStatus.QUEUED:
                    stage_text = status_rich_text(status, "Queued")
                else:
                    stage_text = status_rich_text(BuildStatus.QUEUED, "Waiting...")

                # Format time
                if status == BuildStatus.QUEUED:
                    time_text = status_rich_text(status, "-")
                else:
                    time_text = status_rich_text(status, f"{int(bp.elapsed)}s")

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
                if status == BuildStatus.QUEUED:
                    hidden_queued += 1
                    continue

            icon = status_rich_icon(status)

            # Build status text showing progress and current activity
            if status == BuildStatus.BUILDING:
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

                colored_name = status_rich_text(status, build_name)
                status_text = f"{colored_name} {progress} {stage}"
            elif status == BuildStatus.FAILED:
                failed_text = status_rich_text(status, f"{p.failed} failed")
                status_text = f"{failed_text}, {p.completed - p.failed}/{p.total} done"
            elif status == BuildStatus.WARNING:
                progress_text = f"{p.completed}/{p.total} done"
                status_text = status_rich_text(status, progress_text)
            elif status == BuildStatus.SUCCESS:
                progress_text = f"{p.completed}/{p.total} done"
                status_text = status_rich_text(status, progress_text)
            elif status == BuildStatus.QUEUED:
                status_text = status_rich_text(status, f"Queued ({p.total} builds)")
            else:
                status_text = f"{p.completed}/{p.total}"

            # Time
            if status == BuildStatus.QUEUED:
                time_text = status_rich_text(status, "-")
            else:
                time_text = status_rich_text(status, f"{int(p.elapsed)}s")

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
                1 for bp in self.processes.values() if bp.status == BuildStatus.QUEUED
            )
            building = sum(
                1 for bp in self.processes.values() if bp.status == BuildStatus.BUILDING
            )
            completed = sum(
                1
                for bp in self.processes.values()
                if bp.status in (BuildStatus.SUCCESS, BuildStatus.WARNING)
            )
            failed = sum(
                1 for bp in self.processes.values() if bp.status == BuildStatus.FAILED
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

    _VERBOSE_INDENT = 10

    def _print_verbose_stage(
        self, entry: StageCompleteEvent, log_path: Path | None
    ) -> None:
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

    def _write_live_summary(self) -> None:
        """Write per-target build status to the build history database."""
        from atopile.model.sqlite import BuildHistory

        _FINISHED = {
            BuildStatus.SUCCESS,
            BuildStatus.FAILED,
            BuildStatus.CANCELLED,
            BuildStatus.WARNING,
        }

        for bp in self.processes.values():
            if not bp.build_id:
                continue

            data = self._get_build_data(bp)

            row = Build(
                build_id=bp.build_id,
                name=bp.name,
                display_name=bp.display_name,
                project_root=str(bp.project_root.resolve()),
                target=bp.name,
                status=bp.status,
                started_at=bp.start_time or time.time(),
                stages=data.get("stages", []),
                warnings=data.get("warnings", 0),
                errors=data.get("errors", 0),
                completed_at=time.time() if bp.status in _FINISHED else None,
            )

            BuildHistory.set(row)

    def run_until_complete(self) -> dict[str, int]:
        """
        Run all builds until complete.

        Uses a queue to limit concurrent builds to max_workers.
        In verbose mode, runs sequentially with full output.

        Returns dict of display_name -> exit_code.
        """
        # Write initial summary with all builds queued
        self._write_live_summary()

        if self.verbose:
            return self._run_verbose()

        results = self._run_parallel()

        return results

    def _print_build_logs(
        self,
        bp: "BuildProcess",
        console: "Console",
        levels: list[str] | None = None,
    ) -> None:
        """Print logs from the SQLite database for a build."""
        import sqlite3

        from atopile.logging import BuildLogger

        if not bp.build_id:
            return
        build_id = bp.build_id

        try:
            db_path = BuildLogger.get_log_db()
            if not db_path.exists():
                return

            conn = sqlite3.connect(str(db_path), timeout=5.0)
            conn.row_factory = sqlite3.Row

            # Build query with filters
            conditions = ["build_id = ?"]
            params: list = [build_id]

            if levels:
                placeholders = ",".join("?" * len(levels))
                conditions.append(f"level IN ({placeholders})")
                params.extend(levels)

            where_clause = " AND ".join(conditions)
            query = f"""
                SELECT timestamp, stage, level, message, ato_traceback, python_traceback
                FROM logs
                WHERE {where_clause}
                ORDER BY id
            """

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            # Print logs with color coding
            for row in rows:
                level = row["level"]
                message = row["message"]
                stage = row["stage"]

                # Color code by level
                if level == "ERROR" or level == "ALERT":
                    color = "red"
                elif level == "WARNING":
                    color = "yellow"
                elif level == "INFO":
                    color = "cyan"
                else:
                    color = "white"

                # Format: [STAGE] LEVEL: message
                console.print(f"[{color}][{stage}] {level}: {message}[/{color}]")

                # Print tracebacks if present
                if row["ato_traceback"]:
                    console.print(f"[dim]{row['ato_traceback']}[/dim]")
                if row["python_traceback"]:
                    console.print(f"[dim]{row['python_traceback']}[/dim]")

        except Exception as e:
            logger.debug(f"Failed to query logs for {build_id}: {e}")

    def _print_build_result(
        self,
        display_name: str,
        bp: "BuildProcess",
        ret: int,
        console: "Console",
    ) -> None:
        """Print per-build success/failure summary with details."""
        if ret == 0:
            if bp.warnings > 0:
                console.print(
                    f"[yellow]⚠ {display_name} completed with "
                    f"{bp.warnings} warning(s)[/yellow]"
                )
                # In verbose mode, print the actual warnings
                if self.verbose:
                    console.print("\n[bold yellow]Warnings:[/bold yellow]")
                    self._print_build_logs(bp, console, levels=["WARNING"])
                    console.print()
            else:
                console.print(f"[green]✓ {display_name} completed[/green]")
        else:
            console.print(f"[red]✗ {display_name} failed[/red]")
            # In verbose mode, print the actual errors
            if self.verbose:
                console.print("\n[bold red]Errors:[/bold red]")
                self._print_build_logs(bp, console, levels=["ERROR", "ALERT"])
                console.print()

    def _run_verbose(self) -> dict[str, int]:
        """Run builds sequentially without live display."""
        console = self._get_full_width_console()
        return self._run_parallel(
            max_workers=1,
            print_headers=True,
            print_results=True,
            stage_printer=self._print_verbose_stage,
            console=console,
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
        max_workers: int | None = None,
        print_headers: bool = False,
        print_results: bool = False,
        stage_printer: Callable[[StageCompleteEvent, Path | None], None] | None = None,
        console: Console | None = None,
    ) -> dict[str, int]:
        """Run builds."""

        results: dict[str, int] = {}
        console = console or self._console

        def start_next_build() -> bool:
            try:
                display_name = self._task_queue.get_nowait()
            except queue.Empty:
                return False

            bp = self.processes[display_name]
            build_id_str = f" (build_id= {bp.build_id})" if bp.build_id else ""
            # Add newline after header in verbose mode for cleaner stage output
            newline = "\n" if print_headers else ""
            console.print(
                f"[bold cyan]▶ Building {display_name}{build_id_str}[/bold cyan]{newline}"
            )
            if stage_printer is not None:
                bp.set_stage_printer(stage_printer)
            bp.start()
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
                                    )
                                    bp._error_reported = True
                                elif ret != 0 and not bp._error_reported:
                                    console.print(
                                        f"[red bold]✗ {display_name}[/red bold]\n"
                                    )
                                    bp._error_reported = True
                                elif ret == 0 and bp.warnings > 0:
                                    console.print(
                                        f"[yellow bold]⚠ {display_name}[/yellow bold]\n"
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

                    # Update JSON summary
                    self._write_live_summary()

                    time.sleep(0.5)

            except KeyboardInterrupt:
                # Terminate all processes on interrupt
                for bp in self.processes.values():
                    bp.terminate()
                raise

            return results

        run_loop(console)

        return results

    def _get_build_data(self, bp: "BuildProcess") -> dict:
        """Collect minimal data for a single build as a dictionary."""
        # Use pre-generated build_id from BuildProcess, or generate if not available
        if bp.build_id:
            build_id = bp.build_id
        else:
            project_path = (
                str(bp.project_root.resolve()) if bp.project_root else "unknown"
            )
            build_id = generate_build_id(project_path, bp.name, self._now)

        data = {
            "name": bp.name,  # Target name for matching
            "display_name": bp.display_name,
            "build_id": build_id,
            "status": bp.status.value,
            "elapsed_seconds": round(bp.elapsed, 2),
            "warnings": bp.warnings,
            "errors": bp.errors,
        }

        # Add timing data from stage history
        if bp._stage_history:
            data["stages"] = [
                {
                    "name": entry.description,
                    "stage_id": entry.log_name,
                    # Serialize StageStatus enum to string value for JSON
                    "status": entry.status.value
                    if hasattr(entry.status, "value")
                    else str(entry.status),
                    "elapsed_seconds": round(entry.duration, 2),
                    "infos": entry.infos,
                    "warnings": entry.warnings,
                    "errors": entry.errors,
                    "alerts": entry.alerts,
                }
                for entry in bp._stage_history
            ]

        return data

    def generate_summary(self) -> None:
        """Generate final per-target build summaries."""
        self._write_live_summary()


def _run_single_build() -> None:
    """
    Run a single build target (worker mode).

    This is called when ATO_BUILD_WORKER is set by the parent process.
    Stages are written to the build history DB as they complete.
    """
    from atopile import buildutil
    from atopile.buildutil import BuildStepContext
    from atopile.config import config
    from atopile.model.sqlite import BuildHistory

    # Get the single build target from config
    build_names = list(config.selected_builds)
    if len(build_names) != 1:
        raise RuntimeError(
            f"Worker mode expects exactly 1 build, got {len(build_names)}"
        )

    build_name = build_names[0]

    from atopile.cli.excepthook import install_worker_excepthook

    # Read build_id from environment (passed by parent process)
    build_id = os.environ.get("ATO_BUILD_ID")

    # Initialize build history DB so the worker can write stages
    BuildHistory.init_db()

    # Create build context to track completed stages
    ctx = BuildStepContext(build=None, build_id=build_id)

    with config.select_build(build_name):
        install_worker_excepthook()
        buildutil.build(ctx=ctx)

    # Note: BuildLogger.close_all() is registered as an atexit handler,
    # so logs will be flushed during process shutdown. We don't call it
    # explicitly here because the excepthook needs to log errors AFTER
    # any exceptions occur, and close_all() would close the writer too early.


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

    # Initialize build history database
    from atopile.model.sqlite import BuildHistory

    BuildHistory.init_db()

    # Create and run parallel build manager
    manager = ParallelBuildManager(
        build_tasks,
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

    # Generate per-target summaries
    manager.generate_summary()

    failed = [name for name, code in results.items() if code != 0]
    exit_code = _report_build_results(
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
            help="Run sequentially without live display",
        ),
    ] = False,
):
    """
    Build the specified --target(s) or the targets specified by the build config.
    Optionally specify a different entrypoint with the argument ENTRY.

    Use --all to build all projects in a directory (e.g., `ato build --all`).

    eg. `ato build --target my_target path/to/source.ato:module.path`
    """
    from atopile.config import config
    from faebryk.libs.app.pcb import open_pcb
    from faebryk.libs.kicad.ipc import reload_pcb
    from faebryk.libs.project.dependencies import ProjectDependencies

    # Check for verbose mode from CLI flag or environment variable (for workers)
    if verbose or os.environ.get("ATO_VERBOSE") == "1":
        logging.getLogger().setLevel(logging.DEBUG)

    # Enable faulthandler for crash debugging in workers
    if os.environ.get("ATO_SAFE"):
        import faulthandler

        faulthandler.enable()

    # Worker mode - run single build directly (no config needed yet)
    if os.environ.get("ATO_BUILD_WORKER"):
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
    project_root = config.project.paths.root

    # Create build tasks: (build_name, project_root, project_name)
    build_tasks: list[tuple[str, Path, str | None]] = [
        (name, project_root, None) for name in build_names
    ]

    # Initialize build history database
    from atopile.model.sqlite import BuildHistory

    BuildHistory.init_db()

    # Create and run parallel build manager
    manager = ParallelBuildManager(
        build_tasks,
        max_workers=jobs,
        verbose=verbose,
        targets=target,
        exclude_targets=exclude_target,
        frozen=frozen,
        keep_picked_parts=keep_picked_parts,
        keep_net_names=keep_net_names,
        keep_designators=keep_designators,
    )

    try:
        results = manager.run_until_complete()
    except KeyboardInterrupt:
        logger.info("Build interrupted")
        raise typer.Exit(1)

    # Generate per-target summaries
    manager.generate_summary()

    # Flush and close all build loggers to ensure logs are written to SQLite
    from atopile.logging import BuildLogger

    BuildLogger.close_all()

    failed = [name for name, code in results.items() if code != 0]

    build_exit_code = _report_build_results(
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

    if build_exit_code != 0:
        raise typer.Exit(build_exit_code)


def _report_build_results(
    *,
    failed: list[str],
    total: int,
    failed_names: list[str] | None = None,
) -> int:
    """Report build results and return exit code (0 for success, 1 for failure)."""
    if failed:
        from atopile.cli.excepthook import log_discord_banner

        log_discord_banner()
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
    return 0
