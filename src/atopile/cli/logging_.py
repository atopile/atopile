import io
import logging
import os
import shutil
import threading
import time
from collections.abc import Iterable
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from types import ModuleType, TracebackType
from typing import Literal

import pathvalidate
from rich._null_file import NullFile
from rich.console import Console, ConsoleRenderable, RenderableType
from rich.live import Live
from rich.logging import RichHandler
from rich.markdown import Markdown
from rich.padding import Padding
from rich.progress import (
    MofNCompleteColumn,
    Progress,
    ProgressColumn,
    RenderableColumn,
    SpinnerColumn,
    Task,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Column, Table
from rich.text import Text
from rich.traceback import Traceback

import atopile
import faebryk
import faebryk.libs
import faebryk.libs.logging
from atopile.compiler import DslRichException
from atopile.errors import UserPythonModuleError, _BaseBaseUserException
from faebryk.libs.logging import FLOG_FMT
from faebryk.libs.util import Advancable, ConfigFlag

from . import console

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

COLOR_LOGS = ConfigFlag("COLOR_LOGS", default=False)

# Use parent's timestamp if running as parallel worker, otherwise generate new one
NOW = os.environ.get("ATO_BUILD_TIMESTAMP") or datetime.now().strftime(
    "%Y-%m-%d_%H-%M-%S"
)
_DEFAULT_FORMATTER = logging.Formatter("%(message)s", datefmt="[%X]")
_SHOW_LOG_FILE_PATH_THRESHOLD = 120


# displayed during LoggingStage
ALERT = logging.INFO + 5
logging.addLevelName(ALERT, "ALERT")


class LogHandler(RichHandler):
    """
    A logging handler that renders output with Rich.

    Suppresses frames from tracebacks conditionally depending on the exception type.
    """

    def __init__(
        self,
        *args,
        console: Console,
        rich_tracebacks: bool = True,
        show_path: bool = False,
        tracebacks_suppress: Iterable[str] | None = ["typer"],
        tracebacks_suppress_map: dict[type[BaseException], Iterable[ModuleType]]
        | None = {UserPythonModuleError: [atopile, faebryk]},
        tracebacks_unwrap: list[type[BaseException]] | None = [UserPythonModuleError],
        hide_traceback_types: tuple[type[BaseException], ...] = (
            _BaseBaseUserException,
            DslRichException,
        ),
        always_show_traceback_types: tuple[type[BaseException], ...] = (
            UserPythonModuleError,
        ),
        traceback_level: int = logging.ERROR,
        force_terminal: bool = False,
        **kwargs,
    ):
        super().__init__(
            *args,
            console=console,
            rich_tracebacks=rich_tracebacks,
            show_path=show_path,
            **kwargs,
        )
        self.tracebacks_suppress = tracebacks_suppress or []
        self.tracebacks_suppress_map = tracebacks_suppress_map or {}
        self.tracebacks_unwrap = tracebacks_unwrap or []
        self.hide_traceback_types = hide_traceback_types
        self.always_show_traceback_types = always_show_traceback_types
        self.traceback_level = traceback_level
        self._logged_exceptions = set()
        self._is_terminal = force_terminal or console.is_terminal

        self.addFilter(
            lambda record: record.name.startswith("atopile")
            or record.name.startswith("faebryk")
        )

    def _get_suppress(
        self, exc_type: type[BaseException] | None
    ) -> Iterable[str | ModuleType]:
        """
        Get extended list of modules to suppress from tracebacks.
        """
        suppress: set[str | ModuleType] = set(self.tracebacks_suppress)
        if exc_type is not None:
            for _type in self.tracebacks_suppress_map:
                if issubclass(exc_type, _type) or isinstance(exc_type, _type):
                    suppress.update(self.tracebacks_suppress_map[_type])
        return list(suppress)

    def _unwrap_chained_exceptions(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_traceback: TracebackType | None,
    ) -> tuple[type[BaseException] | None, BaseException | None, TracebackType | None]:
        def unwrap(exc: BaseException, exc_type: type[BaseException]) -> BaseException:
            """
            Unwraps an exception chain until we reach an exception
            that is not an instance of _type.
            """
            while isinstance(exc, exc_type) and exc.__cause__ is not None:
                exc = exc.__cause__
            return exc

        if exc_type is not None and exc_value is not None:
            while any(issubclass(exc_type, _type) for _type in self.tracebacks_unwrap):
                exc_value = unwrap(exc_value, exc_type)
                exc_type = type(exc_value)
                exc_traceback = exc_value.__traceback__

        return exc_type, exc_value, exc_traceback

    def _get_traceback(self, record: logging.LogRecord) -> Traceback | None:
        if not record.exc_info:
            return None

        exc_type, exc_value, exc_traceback = record.exc_info

        suppress = self._get_suppress(exc_type)

        hide_traceback = (
            isinstance(exc_value, self.hide_traceback_types)
            and not isinstance(exc_value, self.always_show_traceback_types)
        ) or record.levelno < self.traceback_level

        if isinstance(exc_value, UserPythonModuleError):
            exc_type, exc_value, exc_traceback = self._unwrap_chained_exceptions(
                exc_type, exc_value, exc_traceback
            )

        if hide_traceback or exc_type is None or exc_value is None:
            return None

        return Traceback.from_exception(
            exc_type,
            exc_value,
            exc_traceback,
            width=self.tracebacks_width,
            extra_lines=self.tracebacks_extra_lines,
            theme=self.tracebacks_theme,
            word_wrap=self.tracebacks_word_wrap,
            show_locals=self.tracebacks_show_locals,
            locals_max_length=self.locals_max_length,
            locals_max_string=self.locals_max_string,
            suppress=suppress,
        )

    def _render_message(
        self, record: logging.LogRecord, message: str
    ) -> "ConsoleRenderable":
        """Render message text in to Text.

        Args:
            record (LogRecord): logging Record.
            message (str): String containing log message.

        Returns:
            ConsoleRenderable: Renderable to display log message.
        """
        if not self._is_terminal:
            return Text(message)

        use_markdown = getattr(record, "markdown", False)
        use_markup = getattr(record, "markup", self.markup)
        highlighter = getattr(record, "highlighter", self.highlighter)

        if use_markdown:
            message_text = Markdown(message)
        else:
            message_text = Text.from_markup(message) if use_markup else Text(message)

            if highlighter:
                message_text = highlighter(message_text)

            if self.keywords is None:
                self.keywords = self.KEYWORDS

            if self.keywords:
                message_text.highlight_words(self.keywords, "logging.keyword")

        return message_text

    def render_message(
        self, record: logging.LogRecord, message: str
    ) -> ConsoleRenderable:
        if record.exc_info is not None and isinstance(
            (exc := record.exc_info[1]), ConsoleRenderable
        ):
            # UserExceptions are already renderables
            return exc

        return self._render_message(record, message)

    def _get_hashable(self, record: logging.LogRecord) -> tuple | None:
        if exc_info := getattr(record, "exc_info", None):
            _, exc_value, _ = exc_info
            if exc_value and isinstance(exc_value, _BaseBaseUserException):
                return exc_value.get_frozen()
        return None

    def _prepare_emit(self, record: logging.LogRecord) -> ConsoleRenderable:
        traceback = self._get_traceback(record)

        if self.formatter:
            record.message = record.getMessage()
            formatter = self.formatter
            if hasattr(formatter, "usesTime") and formatter.usesTime():
                record.asctime = formatter.formatTime(record, formatter.datefmt)
            message = formatter.formatMessage(record)
        else:
            message = record.getMessage()

        message_renderable = self.render_message(record, message)

        log_renderable = self.render(
            record=record, traceback=traceback, message_renderable=message_renderable
        )

        return log_renderable

    def emit(self, record: logging.LogRecord) -> None:
        """Invoked by logging."""
        # In parallel mode, suppress all console output (logs go to files only)
        if get_parallel_display() is not None:
            return

        hashable = self._get_hashable(record)
        if hashable and hashable in self._logged_exceptions:
            return None

        log_renderable = self._prepare_emit(record)

        if isinstance(self.console.file, NullFile):
            # Handles pythonw, where stdout/stderr are null, and we return NullFile
            # instance from Console.file. In this case, we still want to make a log
            # record even though we won't be writing anything to a file.
            self.handleError(record)
        else:
            try:
                self.console.print(log_renderable)
            except Exception:
                self.handleError(record)
            finally:
                if hashable:
                    self._logged_exceptions.add(hashable)


class LiveLogHandler(LogHandler):
    def __init__(self, status: "LoggingStage", *args, **kwargs):
        super().__init__(*args, console=status._console, **kwargs)
        self.status = status
        # In parallel mode, we only count warnings/errors but don't print to console
        self._suppress_output = status._in_parallel_mode

    def emit(self, record: logging.LogRecord) -> None:
        hashable = self._get_hashable(record)
        if hashable and hashable in self._logged_exceptions:
            return

        try:
            if record.levelno >= logging.ERROR:
                self.status._error_count += 1
            elif record.levelno >= logging.WARNING:
                self.status._warning_count += 1

            self.status.refresh()

            # In parallel mode, don't print alerts or other console output
            if self._suppress_output:
                return

            if record.levelno == ALERT:
                self.status.alert(record.getMessage())

        except Exception:
            self.handleError(record)
        finally:
            if hashable:
                self._logged_exceptions.add(hashable)


class CaptureLogHandler(LogHandler):
    def __init__(self, status: "LoggingStage", console: Console, *args, **kwargs):
        super().__init__(*args, console=console, **kwargs)
        self.status = status

    def emit(self, record: logging.LogRecord) -> None:
        hashable = self._get_hashable(record)
        if hashable and hashable in self._logged_exceptions:
            return

        try:
            super().emit(record)
        except Exception:
            self.handleError(record)
        finally:
            if hashable:
                self._logged_exceptions.add(hashable)


class IndentedProgress(Progress):
    def __init__(self, *args, indent: int = 20, **kwargs):
        self.indent = indent
        super().__init__(*args, **kwargs)

    def get_renderable(self):
        return Padding(super().get_renderable(), pad=(0, 0, 0, self.indent))


class ShortTimeElapsedColumn(TimeElapsedColumn):
    """Renders time elapsed."""

    def render(self, task: "Task") -> Text:
        """Show time elapsed."""
        elapsed = task.elapsed or 0
        return Text.from_markup(f"[blue][{elapsed:.1f}s][/blue]")


class StyledMofNCompleteColumn(MofNCompleteColumn):
    def render(self, task: "Task") -> Text:
        return Text.from_markup(
            f"[dim]{task.completed}[/dim]{self.separator}[dim]{task.total}[/dim]"
        )


class SpacerColumn(RenderableColumn):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args, renderable=Text(), table_column=Column(ratio=1), **kwargs
        )


class CompletableSpinnerColumn(SpinnerColumn):
    class Status(StrEnum):
        SUCCESS = "[green]✓[/green]"
        FAILURE = "[red]✗[/red]"
        WARNING = "[yellow]⚠[/yellow]"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status = None

    def complete(self, status: Status) -> None:
        self.status = status

    def render(self, task: "Task") -> RenderableType:
        text = (
            Text.from_markup(self.status)
            if self.status is not None
            else self.spinner.render(task.get_time())
        )
        return text


class StaticIndicatorColumn(ProgressColumn):
    """Non-animated indicator that shows status without spinning."""

    class Status(StrEnum):
        SUCCESS = "[green]✓[/green]"
        FAILURE = "[red]✗[/red]"
        WARNING = "[yellow]⚠[/yellow]"

    def __init__(self):
        super().__init__()
        self.status: str | None = None

    def complete(self, status: Status) -> None:
        self.status = status

    def render(self, task: "Task") -> RenderableType:
        if self.status is not None:
            return Text.from_markup(self.status)
        return Text.from_markup("[blue]●[/blue]")  # Static "in progress" indicator


# =============================================================================
# Parallel Build Display
# =============================================================================

BuildStatus = Literal["pending", "building", "success", "warning", "failed"]


@dataclass
class BuildTargetState:
    """Thread-safe state for a single build target in parallel builds."""

    name: str
    current_stage: str = ""
    stage_start_time: float = 0.0
    stages_completed: int = 0
    stages_total: int = 12  # Default estimate, updated during build
    start_time: float = 0.0
    status: BuildStatus = "pending"
    warnings: int = 0
    errors: int = 0
    log_dir: Path | None = None
    exception: BaseException | None = None

    @property
    def stage_elapsed(self) -> float:
        """Time elapsed in current stage."""
        if self.stage_start_time == 0.0:
            return 0.0
        return time.time() - self.stage_start_time

    @property
    def total_elapsed(self) -> float:
        """Total time elapsed since build started."""
        if self.start_time == 0.0:
            return 0.0
        return time.time() - self.start_time


def _make_hyperlink(path: Path, text: str) -> str:
    """Create an OSC8 terminal hyperlink for clickable paths."""
    url = path.absolute().as_uri()
    return f"\x1b]8;;{url}\x1b\\{text}\x1b]8;;\x1b\\"


# ContextVar to hold the current parallel display (if any)
_parallel_display_var: ContextVar["ParallelBuildDisplay | None"] = ContextVar(
    "parallel_display", default=None
)


class ParallelBuildDisplay:
    """
    A live-updating table display for parallel builds.

    Uses rich.live.Live to render a table showing all build targets
    with their current stage, progress, elapsed time, and status.
    """

    # Status indicators for the table
    _STATUS_ICONS = {
        "pending": "[dim]○[/dim]",
        "building": "[blue]●[/blue]",
        "success": "[green]✓[/green]",
        "warning": "[yellow]⚠[/yellow]",
        "failed": "[red]✗[/red]",
    }

    def __init__(self, build_names: list[str], console: Console | None = None):
        """
        Initialize the parallel build display.

        Args:
            build_names: List of build target names to track
            console: Rich console to use (defaults to error_console)
        """
        from . import console as console_module

        self._console = console or console_module.error_console
        self._lock = threading.Lock()
        self._states: dict[str, BuildTargetState] = {
            name: BuildTargetState(name=name) for name in build_names
        }
        self._live: Live | None = None
        self._token: object | None = None

    def update_target(
        self,
        name: str,
        *,
        current_stage: str | None = None,
        stages_completed: int | None = None,
        stages_total: int | None = None,
        status: BuildStatus | None = None,
        warnings: int | None = None,
        errors: int | None = None,
        log_dir: Path | None = None,
        exception: BaseException | None = None,
        reset_stage_time: bool = False,
        start_build: bool = False,
    ) -> None:
        """
        Thread-safe update of a build target's state.

        Args:
            name: The build target name
            current_stage: Current stage description
            stages_completed: Number of completed stages
            stages_total: Total number of stages
            status: Build status
            warnings: Warning count
            errors: Error count
            log_dir: Path to log directory
            exception: Exception if build failed
            reset_stage_time: Reset the stage start time (for new stages)
            start_build: Set to True to mark the build as started (sets start_time)
        """
        with self._lock:
            if name not in self._states:
                return

            state = self._states[name]

            if current_stage is not None:
                state.current_stage = current_stage
            if stages_completed is not None:
                state.stages_completed = stages_completed
            if stages_total is not None:
                state.stages_total = stages_total
            if status is not None:
                state.status = status
            if start_build or (status == "building" and state.start_time == 0.0):
                state.start_time = time.time()
            if warnings is not None:
                state.warnings = warnings
            if errors is not None:
                state.errors = errors
            if log_dir is not None:
                state.log_dir = log_dir
            if exception is not None:
                state.exception = exception
            if reset_stage_time:
                state.stage_start_time = time.time()

    def increment_warnings(self, name: str) -> None:
        """Thread-safe increment of warning count."""
        with self._lock:
            if name in self._states:
                self._states[name].warnings += 1

    def increment_errors(self, name: str) -> None:
        """Thread-safe increment of error count."""
        with self._lock:
            if name in self._states:
                self._states[name].errors += 1

    def _format_time(self, seconds: float) -> str:
        """Format elapsed time as human-readable string."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"

    # Fixed width for stage column to prevent jumping
    # Longest: "Running post-design checks [12.5s] (1W)" ~40 chars
    _STAGE_COLUMN_WIDTH = 40

    def _render_table(self) -> Table:
        """Render the current state as a rich Table."""
        table = Table(
            show_header=False,  # Cleaner without header
            box=None,
            padding=(0, 1),
            expand=False,
        )

        table.add_column("", width=1)  # Status icon
        table.add_column("", width=12, style="cyan")  # Target (max ~12 chars)
        table.add_column("", width=self._STAGE_COLUMN_WIDTH)  # Stage (fixed width)
        table.add_column("", width=5, justify="right")  # Time

        with self._lock:
            for state in self._states.values():
                status_icon = self._STATUS_ICONS.get(state.status, "○")

                # Format stage with elapsed time
                if state.status == "building" and state.current_stage:
                    stage_text = (
                        f"{state.current_stage} [dim][{state.stage_elapsed:.1f}s][/dim]"
                    )
                elif state.status in ("success", "warning"):
                    stage_text = "[green]Completed[/green]"
                elif state.status == "failed":
                    stage_text = "[red]Failed[/red]"
                else:
                    stage_text = "[dim]Waiting...[/dim]"

                # Add problems indicator
                problems = []
                if state.errors > 0:
                    problems.append(f"[red]{state.errors}E[/red]")
                if state.warnings > 0:
                    problems.append(f"[yellow]{state.warnings}W[/yellow]")
                if problems:
                    stage_text += f" ({', '.join(problems)})"

                # Format total time
                if state.status in ("success", "warning", "failed"):
                    time_text = self._format_time(state.total_elapsed)
                elif state.status == "building":
                    time_text = f"[blue]{self._format_time(state.total_elapsed)}[/blue]"
                else:
                    time_text = "[dim]-[/dim]"

                table.add_row(
                    status_icon,
                    state.name,
                    stage_text,
                    time_text,
                )

        return table

    def _render_summary(self) -> Text:
        """Render a summary line below the table."""
        with self._lock:
            completed = sum(
                1 for s in self._states.values() if s.status in ("success", "warning")
            )
            in_progress = sum(
                1 for s in self._states.values() if s.status == "building"
            )
            failed = sum(1 for s in self._states.values() if s.status == "failed")
            pending = sum(1 for s in self._states.values() if s.status == "pending")
            total_warnings = sum(s.warnings for s in self._states.values())
            total_errors = sum(s.errors for s in self._states.values())

        parts = []
        if completed > 0:
            parts.append(f"[green]Completed: {completed}[/green]")
        if in_progress > 0:
            parts.append(f"[blue]Building: {in_progress}[/blue]")
        if pending > 0:
            parts.append(f"[dim]Pending: {pending}[/dim]")
        if failed > 0:
            parts.append(f"[red]Failed: {failed}[/red]")
        if total_warnings > 0:
            parts.append(f"[yellow]Warnings: {total_warnings}[/yellow]")
        if total_errors > 0:
            parts.append(f"[red]Errors: {total_errors}[/red]")

        return Text.from_markup("  ".join(parts))

    def _render(self) -> RenderableType:
        """Render the full display (table + summary)."""
        from rich.console import Group

        return Group(
            self._render_table(),
            Text(""),  # Spacer
            self._render_summary(),
        )

    def __enter__(self) -> "ParallelBuildDisplay":
        """Start the live display and set as current parallel display."""
        self._live = Live(
            self._render(),
            console=self._console,
            refresh_per_second=10,
            transient=False,
        )
        self._live.start()
        self._token = _parallel_display_var.set(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Stop the live display and clear the context."""
        if self._live:
            # Final render before stopping
            self._live.update(self._render())
            self._live.stop()
            self._live = None
        if self._token is not None:
            _parallel_display_var.reset(self._token)
            self._token = None

    def refresh(self) -> None:
        """Manually refresh the display."""
        if self._live:
            self._live.update(self._render())

    def get_state(self, name: str) -> BuildTargetState | None:
        """Get a copy of the state for a build target."""
        with self._lock:
            return self._states.get(name)

    @property
    def all_completed(self) -> bool:
        """Check if all builds have finished (success, warning, or failed)."""
        with self._lock:
            return all(
                s.status in ("success", "warning", "failed")
                for s in self._states.values()
            )

    @property
    def any_failed(self) -> bool:
        """Check if any build has failed."""
        with self._lock:
            return any(s.status == "failed" for s in self._states.values())

    @property
    def failed_builds(self) -> list[str]:
        """Get list of failed build names."""
        with self._lock:
            return [s.name for s in self._states.values() if s.status == "failed"]

    @property
    def exceptions(self) -> dict[str, BaseException]:
        """Get mapping of build names to their exceptions."""
        with self._lock:
            return {
                s.name: s.exception
                for s in self._states.values()
                if s.exception is not None
            }


def get_parallel_display() -> "ParallelBuildDisplay | None":
    """Get the current parallel build display, if any."""
    return _parallel_display_var.get()


_log_sink_var = ContextVar[io.StringIO | None]("log_sink", default=None)


@contextmanager
def capture_logs():
    log_sink = _log_sink_var.get()
    _log_sink_var.set(io.StringIO())
    _log_sink = _log_sink_var.get()
    assert _log_sink is not None
    yield _log_sink
    _log_sink_var.set(log_sink)


@contextmanager
def log_exceptions(log_sink: io.StringIO):
    from atopile.cli.excepthook import _handle_exception

    exc_log_console = Console(file=log_sink)
    exc_log_handler = LogHandler(console=exc_log_console)
    logger.addHandler(exc_log_handler)

    try:
        yield
    except Exception as e:
        _handle_exception(type(e), e, e.__traceback__)
        raise e
    finally:
        logger.removeHandler(exc_log_handler)


class LoggingStage(Advancable):
    _LOG_LEVELS = {
        logging.DEBUG: "debug",
        logging.INFO: "info",
        logging.WARNING: "warning",
        logging.ERROR: "error",
    }

    def __init__(
        self, name: str, description: str, steps: int | None = None, indent: int = 20
    ):
        self.name = name
        self.description = description
        self.indent = indent
        self.steps = steps
        self._console = console.error_console
        self._warning_count = 0
        self._error_count = 0
        self._info_log_path = None
        self._log_handler = None
        self._capture_log_handler = None
        self._file_handlers = []
        self._original_handlers = {}
        self._sanitized_name = pathvalidate.sanitize_filename(self.name)
        self._result = None
        self._log_dir: Path | None = None

        # Check if we're in parallel mode (skip per-stage progress display)
        self._parallel_display = get_parallel_display()
        self._in_parallel_mode = self._parallel_display is not None

        # Check if animations should be disabled (verbose mode via pipe)
        self._no_animation = os.environ.get("ATO_NO_PROGRESS_ANIMATION") == "1"

        # Only create progress bar if not in parallel mode and not in no-animation mode
        if not self._in_parallel_mode and not self._no_animation:
            self._progress = IndentedProgress(
                *self._get_columns(),
                console=self._console,
                transient=False,
                auto_refresh=True,
                refresh_per_second=10,
                indent=self.indent,
                expand=True,
            )
        else:
            self._progress = None  # type: ignore[assignment]

    def _get_columns(self) -> tuple[ProgressColumn, ...]:
        show_log_file_path = (
            self._info_log_path and self._console.width >= _SHOW_LOG_FILE_PATH_THRESHOLD
        )

        # Use static indicator (no animation) when piped for verbose mode
        if self._no_animation:
            indicator_col = StaticIndicatorColumn()
        else:
            indicator_col = CompletableSpinnerColumn()
        self._indicator_col = indicator_col

        return tuple(
            col
            for col in (
                indicator_col,
                TextColumn("{task.description}"),
                StyledMofNCompleteColumn() if self.steps is not None else None,
                ShortTimeElapsedColumn(),
                SpacerColumn(),
                TextColumn(
                    f"[dim]{self._info_log_path}[/dim]" if show_log_file_path else "",
                    justify="right",
                    table_column=Column(justify="right", overflow="ellipsis"),
                ),
            )
            if col is not None
        )

    def _update_columns(self) -> None:
        if self._progress is not None:
            self._progress.columns = self._get_columns()

    def alert(self, message: str) -> None:
        # In parallel mode, alerts are suppressed (logged to file only)
        if self._in_parallel_mode:
            return

        message = f"[bold][yellow]![/yellow] {message}[/bold]"

        self._console.print(
            Padding(Text.from_markup(message), pad=(0, 0, 0, self.indent)),
            highlight=True,
        )

    def _generate_description(self) -> str:
        problems = []
        if self._error_count > 0:
            plural_e = "s" if self._error_count > 1 else ""
            problems.append(f"[red]{self._error_count} error{plural_e}[/red]")

        if self._warning_count > 0:
            plural_w = "s" if self._warning_count > 1 else ""
            problems.append(f"[yellow]{self._warning_count} warning{plural_w}[/yellow]")

        problems_text = f" ({', '.join(problems)})" if problems else ""
        return f"{self.description}{problems_text}"

    def refresh(self) -> None:
        if self._in_parallel_mode:
            # In parallel mode, refresh the parallel display instead
            if self._parallel_display:
                self._parallel_display.refresh()
            return

        if self._no_animation:
            return  # No progress bar to refresh

        if not hasattr(self, "_task_id"):
            return

        self._progress.update(self._task_id, description=self._generate_description())

    def set_total(self, total: int | None) -> None:
        self.steps = total
        self._current_progress = 0

        # Write progress to status file if in worker mode
        self._write_status_file()

        if self._in_parallel_mode or self._no_animation:
            # In parallel/no-animation mode, don't update progress bar
            return

        self._update_columns()
        self._progress.update(self._task_id, total=total)
        self.refresh()

    def advance(self, advance: int = 1) -> None:
        self._current_progress = getattr(self, "_current_progress", 0) + advance

        # Write progress to status file if in worker mode
        self._write_status_file()

        if self._in_parallel_mode or self._no_animation:
            return  # Progress tracking handled differently
        assert self.steps is not None
        self._progress.advance(self._task_id, advance)

    def _write_status_file(self) -> None:
        """Write current stage and progress to status file for IPC."""
        status_file = os.environ.get("ATO_BUILD_STATUS_FILE")
        if not status_file:
            return

        try:
            progress = getattr(self, "_current_progress", 0)
            total = self.steps
            if total and total > 1:
                status = f"{self.description} {progress}/{total}"
            else:
                status = self.description
            Path(status_file).write_text(status)
        except Exception:
            pass  # Don't fail if we can't write status

    def _get_build_name(self) -> str:
        """Get the current build name from config."""
        try:
            from atopile.config import config

            return config.build.name
        except (RuntimeError, ImportError):
            return "unknown"

    def __enter__(self) -> "LoggingStage":
        self._setup_logging()
        self._current_progress = 0

        # Write status to file if in worker mode (subprocess parallelism)
        self._write_status_file()

        if self._in_parallel_mode:
            # Update parallel display with new stage
            if self._parallel_display:
                self._parallel_display.update_target(
                    self._get_build_name(),
                    current_stage=self.description,
                    log_dir=self._log_dir,
                    reset_stage_time=True,
                )
        elif self._no_animation:
            # No-animation mode: no progress bar, just track internally
            self._stage_start_time = time.time()
        else:
            self._update_columns()
            self._progress.start()
            self._task_id = self._progress.add_task(
                self.description, total=self.steps if self.steps is not None else 1
            )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._restore_logging()

        if exc_type is not None or self._error_count > 0:
            status = CompletableSpinnerColumn.Status.FAILURE
        elif self._warning_count > 0:
            status = CompletableSpinnerColumn.Status.WARNING
        else:
            status = CompletableSpinnerColumn.Status.SUCCESS

        if self._in_parallel_mode:
            # Update parallel display with stage completion
            if self._parallel_display:
                build_name = self._get_build_name()
                state = self._parallel_display.get_state(build_name)
                if state:
                    self._parallel_display.update_target(
                        build_name,
                        stages_completed=state.stages_completed + 1,
                        warnings=state.warnings + self._warning_count,
                        errors=state.errors + self._error_count,
                    )
        elif self._no_animation:
            # No-animation mode: print single completion line
            elapsed = time.time() - getattr(self, "_stage_start_time", time.time())
            status_icon = {
                CompletableSpinnerColumn.Status.SUCCESS: "[green]✓[/green]",
                CompletableSpinnerColumn.Status.WARNING: "[yellow]⚠[/yellow]",
                CompletableSpinnerColumn.Status.FAILURE: "[red]✗[/red]",
            }.get(status, "●")

            # Build description with warning count if any
            desc = self.description
            if self._warning_count > 0:
                desc = f"{desc} ({self._warning_count} warning)"

            # Print completion line
            log_path = self._info_log_path or ""
            self._console.print(
                f"{'':>{self.indent}}{status_icon} {desc} [{elapsed:.1f}s]"
                f"{'':>10}{log_path}"
            )
        else:
            for column in self._progress.columns:
                if isinstance(column, CompletableSpinnerColumn):
                    column.complete(status)

            self.refresh()
            self._progress.stop()

    def _create_log_dir(self) -> Path:
        from atopile.config import config

        base_log_dir = Path(config.project.paths.logs) / "archive" / NOW

        try:
            build_cfg = config.build
            log_dir = base_log_dir / pathvalidate.sanitize_filename(build_cfg.name)
        except RuntimeError:
            log_dir = base_log_dir

        log_dir.mkdir(parents=True, exist_ok=True)

        # Store log directory for parallel display
        self._log_dir = log_dir

        # Skip symlink update in parallel mode - it's handled by the summary generator
        if self._in_parallel_mode:
            return log_dir

        # Update the latest symlink (single-threaded mode only)
        latest_link = Path(config.project.paths.logs) / "latest"
        try:
            if latest_link.is_symlink():
                latest_link.unlink()
            elif latest_link.exists():
                shutil.rmtree(latest_link)
            latest_link.symlink_to(base_log_dir, target_is_directory=True)
        except OSError:
            # If we can't symlink, just don't symlink
            # Logs are still written to the dated directory
            # Seems to happen on Windows if 'Developer Mode' is not enabled
            pass

        return log_dir

    def _setup_logging(self) -> None:
        root_logger = logging.getLogger()

        self._original_level = root_logger.level
        self._original_handlers = {"root": root_logger.handlers.copy()}

        # log all messages to at least one handler
        root_logger.setLevel(logging.DEBUG)

        self._log_handler = LiveLogHandler(self)
        self._log_handler.setFormatter(_DEFAULT_FORMATTER)
        self._log_handler.setLevel(self._original_level)

        if _log_sink_var.get() is not None:
            capture_console = Console(file=_log_sink_var.get())
            self._capture_log_handler = CaptureLogHandler(self, console=capture_console)
            self._capture_log_handler.setFormatter(_DEFAULT_FORMATTER)
            self._capture_log_handler.setLevel(logging.INFO)

        log_dir = self._create_log_dir()

        for handler in root_logger.handlers.copy():
            root_logger.removeHandler(handler)

        root_logger.addHandler(self._log_handler)
        if self._capture_log_handler is not None:
            root_logger.addHandler(self._capture_log_handler)

        self._file_handlers = []
        self._file_handles = {}

        for level, level_name in self._LOG_LEVELS.items():
            log_file = log_dir / f"{self._sanitized_name}.{level_name}.log"

            self._file_handles[level_name] = log_file.open("w", encoding="utf-8")
            file_console = Console(
                file=self._file_handles[level_name],
                width=500,
                force_terminal=COLOR_LOGS.get(),
            )
            file_handler = LogHandler(
                console=file_console,
                force_terminal=COLOR_LOGS.get(),
                markup=False,
            )
            file_handler.setFormatter(_DEFAULT_FORMATTER)
            file_handler.setLevel(level)
            self._file_handlers.append(file_handler)
            root_logger.addHandler(file_handler)

            if level_name == "info":
                try:
                    info_log_path = log_file.relative_to(Path.cwd())
                except ValueError:
                    info_log_path = log_file

                self._info_log_path = info_log_path

    def _restore_logging(self) -> None:
        if not self._log_handler and not self._file_handlers:
            return

        root_logger = logging.getLogger()
        root_logger.setLevel(self._original_level)

        if self._log_handler in root_logger.handlers:
            root_logger.removeHandler(self._log_handler)

        if self._capture_log_handler in root_logger.handlers:
            root_logger.removeHandler(self._capture_log_handler)

        for file_handler in self._file_handlers:
            if file_handler in root_logger.handlers:
                root_logger.removeHandler(file_handler)
                file_handler.close()

        for file_handle in self._file_handles.values():
            file_handle.close()

        for handler in root_logger.handlers.copy():
            root_logger.removeHandler(handler)

        for handler in self._original_handlers.get("root", []):
            root_logger.addHandler(handler)

        self._original_handlers = {}
        self._original_level = logging.INFO
        self._log_handler = None
        self._capture_log_handler = None
        self._file_handlers = []


handler = LogHandler(console=console.error_console)
handler.setFormatter(_DEFAULT_FORMATTER)

if FLOG_FMT:
    faebryk.libs.logging.setup_basic_logging()
else:
    logging.basicConfig(level=logging.INFO, handlers=[handler])

logger = logging.getLogger(__name__)
