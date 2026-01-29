"""
Shared logging and Rich console utilities for atopile.

Provides:
- Global console singletons (console, error_console)
- Shared styling constants (LEVEL_STYLES, STATUS_ICONS, etc.)
- Helper functions (safe_markdown, format_stage_status, rich_to_string, etc.)
- Progress bar components
"""

from __future__ import annotations

import io
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

import rich
from rich.console import Console, ConsoleOptions, ConsoleRenderable
from rich.highlighter import RegexHighlighter, ReprHighlighter
from rich.logging import RichHandler
from rich.markdown import Markdown
from rich.padding import Padding
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    RenderableColumn,
    SpinnerColumn,
    Task,
    TextColumn,
    TimeElapsedColumn,
)
from rich.syntax import Syntax
from rich.table import Column, Table
from rich.text import Text
from rich.theme import Theme
from rich.traceback import Traceback

from faebryk.libs.util import ConfigFlag, ConfigFlagInt

from atopile.dataclasses import BuildStatus

if TYPE_CHECKING:
    from rich.console import RenderableType

    from atopile.dataclasses import StageStatus

# =============================================================================
# Shared Style Constants
# =============================================================================

# Canonical log level styles - use these everywhere for consistency
LEVEL_STYLES: dict[str, str] = {
    "DEBUG": "bright_black",
    "INFO": "green",
    "ALERT": "cyan bold",
    "WARNING": "yellow",
    "ERROR": "red",
    "CRITICAL": "red bold reverse",
}

# Abbreviated level names with Rich markup (for compact displays)
LEVEL_ABBREV: dict[str, str] = {
    "DEBUG": f"[{LEVEL_STYLES['DEBUG']}]D[/{LEVEL_STYLES['DEBUG']}]",
    "INFO": f"[{LEVEL_STYLES['INFO']}]I[/{LEVEL_STYLES['INFO']}]",
    "WARNING": f"[{LEVEL_STYLES['WARNING']}]W[/{LEVEL_STYLES['WARNING']}]",
    "ERROR": f"[{LEVEL_STYLES['ERROR']}]E[/{LEVEL_STYLES['ERROR']}]",
    "CRITICAL": f"[{LEVEL_STYLES['CRITICAL']}]C[/{LEVEL_STYLES['CRITICAL']}]",
}

# Canonical status icons and colors for build/stage status
STATUS_ICONS: dict[str, str] = {
    "queued": "○",
    "pending": "○",
    "building": "●",
    "running": "●",
    "success": "✓",
    "warning": "⚠",
    "failed": "✗",
    "error": "✗",
    "cancelled": "⊘",
    "skipped": "⊘",
}

STATUS_COLORS: dict[str, str] = {
    "queued": "dim",
    "pending": "dim",
    "building": "blue",
    "running": "blue",
    "success": "green",
    "warning": "yellow",
    "failed": "red",
    "error": "red",
    "cancelled": "dim",
    "skipped": "dim",
}


def get_status_style(status: str | BuildStatus) -> tuple[str, str]:
    """Get (icon, color) tuple for a status value."""
    if hasattr(status, "value"):
        status = status.value
    status_key = status.lower()
    icon = STATUS_ICONS.get(status_key, "○")
    color = STATUS_COLORS.get(status_key, "dim")
    return icon, color


# =============================================================================
# Rich Console Configuration
# =============================================================================

# Theme for faebryk-style node highlighting (includes log level styles)
faebryk_theme = Theme(
    {
        # Node highlighting
        "node.Node": "bold magenta",
        "node.Type": "bright_cyan",
        "node.Parent": "bright_red",
        "node.Child": "bright_yellow",
        "node.Root": "bold yellow",
        "node.Number": "bright_green",
        "node.Quantity": "bright_yellow",
        "node.IsSubset": "bright_blue",
        "node.Predicate": "bright_magenta",
        "node.Op": "red",
        # Log level styles (used by Rich's built-in logging)
        "logging.level.debug": LEVEL_STYLES["DEBUG"],
        "logging.level.info": LEVEL_STYLES["INFO"],
        "logging.level.warning": LEVEL_STYLES["WARNING"],
        "logging.level.error": LEVEL_STYLES["ERROR"],
        "logging.level.critical": LEVEL_STYLES["CRITICAL"],
    }
)

rich.reconfigure(theme=faebryk_theme)

# Console singletons - use these to avoid intermixing logging with other output
console = rich.get_console()
error_console = Console(theme=faebryk_theme, stderr=True)


def safe_markdown(message: str, console: Console | None = None) -> ConsoleRenderable:
    """
    Render message as Markdown if in a terminal, otherwise as plain Text.

    Use this when you want Markdown formatting but need graceful fallback
    for non-terminal output (e.g., piped to file, CI logs).

    Args:
        message: The message to render
        console: Optional console to check is_terminal. If None, checks stdout.

    Returns:
        Markdown or Text renderable
    """
    if console is None:
        is_terminal = sys.stdout.isatty()
    else:
        is_terminal = console.is_terminal

    if is_terminal:
        return Markdown(message)
    return Text(message)

def _get_terminal_width() -> int:
    """Get terminal width from the global console singleton."""
    if not sys.stdout.isatty():
        if "COLUMNS" in os.environ:
            return int(os.environ["COLUMNS"])
        return 240
    return console.size.width

# =============================================================================
# Progress Bar Components
# =============================================================================


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
        SUCCESS = f"[{STATUS_COLORS['success']}]{STATUS_ICONS['success']}[/{STATUS_COLORS['success']}]"
        FAILURE = f"[{STATUS_COLORS['failed']}]{STATUS_ICONS['failed']}[/{STATUS_COLORS['failed']}]"
        WARNING = f"[{STATUS_COLORS['warning']}]{STATUS_ICONS['warning']}[/{STATUS_COLORS['warning']}]"

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


# =============================================================================
# Faebryk Logging Utilities (formerly faebryk.libs.logging)
# =============================================================================

PLOG = ConfigFlag("PLOG", descr="Enable picker debug log")
TERMINAL_WIDTH = ConfigFlagInt(
    "TERMINAL_WIDTH",
    default=_get_terminal_width(),
    descr="Width of the terminal",
)


LOG_TIME = ConfigFlag("LOG_TIME", default=True, descr="Enable logging of time")
LOG_FILEINFO = ConfigFlag(
    "LOG_FILEINFO", default=True, descr="Enable logging of file info"
)

TIME_LEN = 5 + 2 if LOG_TIME else 0
LEVEL_LEN = 1
FILE_LEN = 12 + 4 if LOG_FILEINFO else 0
FMT_HEADER_LEN = TIME_LEN + 1 + LEVEL_LEN + 1 + FILE_LEN + 1

NET_LINE_WIDTH = min(120, int(TERMINAL_WIDTH) - FMT_HEADER_LEN)


def format_line(line: str) -> str:
    """Format a line with proper wrapping based on NET_LINE_WIDTH."""
    stripped_line = line.lstrip(" ")
    prefix = " " * ((len(line) - len(stripped_line)) + 2)
    chunk_size = NET_LINE_WIDTH - len(prefix)
    stripped_line = stripped_line.rstrip()
    lines = []
    for i in range(0, len(stripped_line), chunk_size):
        chunk = stripped_line[i : i + chunk_size]
        lines.append(f"{prefix}{chunk}")

    return "\n".join(lines).removeprefix(" " * 2)


def rich_print_robust(message: str, markdown: bool = False) -> None:
    """
    Print a message with Rich, falling back to ASCII and plain text on errors.
    """
    try:
        rich.print(Markdown(message) if markdown else message)
    except UnicodeEncodeError:
        message = message.encode("ascii", errors="ignore").decode("ascii")
        rich.print(Markdown(message) if markdown else message)
    except Exception:
        if markdown:
            plain_message = re.sub(r"```\w*\n", "", message)
            plain_message = re.sub(r"```$", "", plain_message, flags=re.MULTILINE)
            rich.print(plain_message)
        else:
            rich.print(message)


def is_piped_to_file() -> bool:
    """Check if stdout is piped to a file."""
    return not sys.stdout.isatty()


def get_terminal_width() -> int:
    """Get the terminal width, with fallback for piped output."""
    if is_piped_to_file():
        if "COLUMNS" in os.environ:
            return int(os.environ["COLUMNS"])
        return 240
    return console.size.width


def rich_to_string(rich_obj: Table | Tree) -> str:
    """Convert a Rich Table or Tree to a string."""
    nested_console = NestedConsole()
    nested_console.print(rich_obj)
    return str(nested_console)


class NestedConsole(Console):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            record=True,
            width=NET_LINE_WIDTH - 1,
            file=io.StringIO(),
            force_terminal=True,  # Enable ANSI colors for frontend rendering
            **kwargs,
        )

    def __str__(self):
        return self.export_text(styles=True)


# Legacy alias - use LEVEL_ABBREV instead
_LEVEL_ABBREV = LEVEL_ABBREV


class RelativeTimeFormatter(logging.Formatter):
    """Custom formatter with ms-since-start timestamp and abbreviated colored levels."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_time = time.perf_counter()

    def format(self, record: logging.LogRecord) -> str:
        # Calculate ms since logging started
        elapsed_s = time.perf_counter() - self.start_time
        record.elapsed_ms = f"{elapsed_s:>3.2f}s".rjust(7)

        # Replace level name with abbreviated colored version
        record.level_abbrev = _LEVEL_ABBREV.get(record.levelname, record.levelname)

        INDENT = " " * (FMT_HEADER_LEN + 1)
        message = record.getMessage()
        message = message.replace("\n", f"\n{INDENT}")
        if "\x1b" not in message:
            # If any line is longer than NET_LINE_WIDTH, wrap into chunks.
            if NET_LINE_WIDTH > 0 and len(message) > NET_LINE_WIDTH:
                message = "\n".join(
                    format_line(line) for line in message.splitlines()
                )

        record.nmessage = message

        # fileinfo
        filename, ext = record.filename.rsplit(".", 1)
        if len(filename) > 12:
            filename = filename[:5] + "..." + filename[-4:]
        lineno = record.lineno
        fileinfo = f"{filename}:{lineno}"
        record.fileinfo = f"{fileinfo:16s}"

        return super().format(record)


class NodeHighlighter(RegexHighlighter):
    """
    Apply style to anything that looks like an faebryk fabll.Node\n
    <*|XOR_with_NANDS.nands[2]|NAND.inputs[0]|Logic> with
      <*|TI_CD4011BE.nands[2]|ElectricNAND.inputs[0]|ElectricLogic>\n
    \t<> = fabll.Node\n
    \t|  = Type\n
    \t.  = Parent\n
    \t*  = Root
    """

    base_style = "node."
    highlights = [
        #  r"(?P<Rest>(.*))",
        r"(?P<Node>([/</>]))",
        r"[?=\|](?P<Type>([a-zA-Z_0-9]+))[?=\>]",
        r"[\.](?P<Child>([a-zA-Z_0-9]+))[?=\[]",
        r"[\|](?P<Parent>([a-zA-Z_0-9]+))[?=\.]",
        r"[?<=*.](?P<Root>(\*))",
        r"[?=\[](?P<Number>([0-9]+))[?=\]]",
        # Solver/Parameter stuff -------------------------------------------------------
        # Literals
        r"(?P<Quantity>Quantity_Interval(_Disjoint)?\([^)]*\))",
        r"(?P<Quantity>\(\[[^)]*\]\))",
        r"(?P<Quantity>\[(True|False)+\])",
        # Predicates / Expressions
        r"(?P<Op> (\+|\*|/))[ {]",
        r"(?P<Predicate> (is|⊆|≥|≤|)!?!?[✓✗]?) ",
        # Literal Is/IsSubset
        r"(?P<IsSubset>{(I|S)\|[^}]+})",
    ]


class ReprHighlighter(RegexHighlighter):
    """Highlights the text typically produced from ``__repr__`` methods."""

    base_style = "repr."
    highlights = [
        r"(?P<tag_start><)(?P<tag_name>[-\w.:|]*)(?P<tag_contents>[\w\W]*)(?P<tag_end>>)",
        r'(?P<attrib_name>[\w_]{1,50})=(?P<attrib_value>"?[\w_]+"?)?',
        r"(?P<brace>[][{}()])",
        "|".join(
            [
                r"(?P<ipv4>[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})",
                r"(?P<ipv6>([A-Fa-f0-9]{1,4}::?){1,7}[A-Fa-f0-9]{1,4})",
                r"(?P<eui64>(?:[0-9A-Fa-f]{1,2}-){7}[0-9A-Fa-f]{1,2}|(?:[0-9A-Fa-f]{1,2}:){7}[0-9A-Fa-f]{1,2}|(?:[0-9A-Fa-f]{4}\.){3}[0-9A-Fa-f]{4})",
                r"(?P<eui48>(?:[0-9A-Fa-f]{1,2}-){5}[0-9A-Fa-f]{1,2}|(?:[0-9A-Fa-f]{1,2}:){5}[0-9A-Fa-f]{1,2}|(?:[0-9A-Fa-f]{4}\.){2}[0-9A-Fa-f]{4})",
                r"(?P<call>[\w.]*?)\(",
                r"\b(?P<bool_true>True)\b|\b(?P<bool_false>False)\b|\b(?P<none>None)\b",
                r"(?P<ellipsis>\.\.\.)",
                r"(?P<number_complex>(?<!\w)(?:\-?[0-9]+\.?[0-9]*(?:e[-+]?\d+?)?)(?:[-+](?:[0-9]+\.?[0-9]*(?:e[-+]?\d+)?))?j)",
                r"(?P<number>(?<!\w)\-?[0-9]+\.?[0-9]*(e[-+]?\d+?)?\b|0x[0-9a-fA-F]*)",
                # matches paths with or without leading / (@windows)
                r"(?P<path>(\b|/)([-\w._+]+)(/[-\w._+]+)*/)(?P<filename>[-\w._+]*)?",
                r"(?<![\\\w])(?P<str>b?'''.*?(?<!\\)'''|b?'.*?(?<!\\)'|b?\"\"\".*?(?<!\\)\"\"\"|b?\".*?(?<!\\)\")",
                r"(?P<url>(file|https|http|ws|wss)://[-0-9a-zA-Z$_+!`(),.?/;:&=%#~@]*)",
            ]
        ),
    ]


logging.getLogger("httpx").setLevel(logging.WARNING)


# =============================================================================
# Status Formatting Utilities
# =============================================================================


def status_rich_icon(status: BuildStatus | str) -> str:
    """Get Rich-formatted icon for status (for terminal display)."""
    icon, color = get_status_style(status)
    return f"[{color}]{icon}[/{color}]"


def status_rich_text(status: BuildStatus | str, text: str) -> str:
    """Format text with Rich color markup for status."""
    _, color = get_status_style(status)
    return f"[{color}]{text}[/{color}]" if color else text


def format_stage_status(
    status: "StageStatus | str",
    description: str,
    duration: float,
    errors: int = 0,
    warnings: int = 0,
) -> str:
    """
    Format a stage entry with status icon, counts, and duration.

    Returns Rich markup string like: "[green]✓ Stage name [1.2s][/green]"
    """
    icon, color = get_status_style(status)

    # Build counts suffix
    counts = ""
    if errors > 0:
        counts = f"({errors}E"
        if warnings > 0:
            counts += f",{warnings}W"
        counts += ")"
    elif warnings > 0:
        counts = f"({warnings})"

    label = f"{icon}{counts} {description} [{duration:.1f}s]"
    return f"[{color}]{label}[/{color}]"


# =============================================================================
# Build Printer (unified CLI output for ato build)
# =============================================================================


@dataclass
class _BuildState:
    """Track state for a single build."""

    display_name: str
    stages: list[dict] = field(default_factory=list)
    total_stages: int = 15  # Default estimate
    status: "BuildStatus" = field(default_factory=lambda: BuildStatus.QUEUED)
    started: bool = False
    reported: bool = False
    last_printed_stage: int = 0  # for verbose mode


class BuildPrinter:
    """
    Unified build output for CLI - handles both live and verbose modes.

    Non-verbose mode (Rich Live):
    - Shows animated spinners for active builds
    - Displays progress as [completed/total] stage count
    - Shows current stage name

    Verbose mode (sequential prints):
    - Prints header when build starts
    - Prints each stage as it completes
    - Prints completion summary with warnings/errors

    Usage:
        with BuildPrinter(verbose=False) as printer:
            printer.build_started(build_id, "my-build")
            printer.stage_update(build_id, stages_list)
            printer.build_completed(build_id, BuildStatus.SUCCESS)
    """

    # Estimated stage count for progress display
    DEFAULT_STAGE_COUNT = 15
    _VERBOSE_INDENT = 10

    def __init__(self, verbose: bool = False, console_: "Console | None" = None):
        self.verbose = verbose
        self._console = console_ or console
        self._progress: Progress | None = None
        self._tasks: dict[str, int] = {}  # build_id -> Progress TaskID
        self._builds: dict[str, _BuildState] = {}

    def __enter__(self) -> "BuildPrinter":
        if not self.verbose:
            self._progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold]{task.description}"),
                BarColumn(bar_width=20),
                StyledMofNCompleteColumn(),
                TextColumn("{task.fields[stage]}"),
                ShortTimeElapsedColumn(),
                console=self._console,
                transient=True,  # Remove progress display when done
            )
            self._progress.__enter__()
        return self

    def __exit__(self, *args) -> None:
        if self._progress:
            self._progress.__exit__(*args)

    def build_started(
        self, build_id: str, display_name: str, total: int | None = None
    ) -> None:
        """Called when a build begins."""
        total_stages = total if total is not None else self.DEFAULT_STAGE_COUNT
        self._builds[build_id] = _BuildState(
            display_name=display_name,
            total_stages=total_stages,
            status=BuildStatus.BUILDING,
            started=True,
        )

        if self.verbose:
            # Print header for verbose mode
            self._console.print(
                f"[bold cyan]▶ Building {display_name} (build_id={build_id})[/bold cyan]"
            )
        else:
            # Add task to progress display
            if self._progress:
                task_id = self._progress.add_task(
                    description=display_name,
                    total=total_stages,
                    stage="",
                )
                self._tasks[build_id] = task_id

    def stage_update(self, build_id: str, stages: list[dict]) -> None:
        """Called when stages change - updates progress or prints new stages."""
        state = self._builds.get(build_id)
        if not state:
            return

        state.stages = stages

        # Terminal statuses indicate a stage is done
        terminal_statuses = {"success", "warning", "failed", "error", "cancelled", "skipped"}

        if self.verbose:
            # Print only completed stages that haven't been printed yet
            for i, stage in enumerate(stages):
                if i < state.last_printed_stage:
                    continue
                status = stage.get("status", "").lower()
                if status in terminal_statuses:
                    self._print_verbose_stage(stage)
                    state.last_printed_stage = i + 1
        else:
            # Count completed stages for progress bar
            completed_count = sum(
                1 for s in stages if s.get("status", "").lower() in terminal_statuses
            )
            # Update progress bar
            if self._progress and build_id in self._tasks:
                task_id = self._tasks[build_id]
                # Show current running stage name
                current_stage = ""
                for stage in reversed(stages):
                    status = stage.get("status", "").lower()
                    if status not in terminal_statuses:
                        current_stage = stage.get("name", "")
                        break
                # Update total if we've exceeded our estimate
                new_total = max(state.total_stages, completed_count + 1)
                self._progress.update(
                    task_id,
                    completed=completed_count,
                    total=new_total,
                    stage=f"[dim]{current_stage}[/dim]" if current_stage else "",
                )

    def build_completed(
        self,
        build_id: str,
        status: "BuildStatus",
        warnings: int = 0,
        errors: int = 0,
    ) -> None:
        """Called when build finishes."""
        state = self._builds.get(build_id)
        if not state or state.reported:
            return

        state.status = status
        state.reported = True
        display_name = state.display_name

        if self.verbose:
            self._print_verbose_result(display_name, status, warnings, errors)
        else:
            # Remove from progress display
            if self._progress and build_id in self._tasks:
                task_id = self._tasks[build_id]
                self._progress.update(task_id, visible=False)

            # Print final status line
            self._print_compact_result(display_name, status, warnings)

    def _print_verbose_stage(self, stage: dict) -> None:
        """Print a single verbose stage line."""
        from atopile.dataclasses import StageStatus

        status_raw = stage.get("status", StageStatus.SUCCESS.value)
        try:
            status = StageStatus(status_raw)
        except ValueError:
            status = StageStatus.SUCCESS

        elapsed = stage.get("elapsedSeconds", 0.0)

        formatted = format_stage_status(
            status=status,
            description=stage.get("name", ""),
            duration=elapsed,
            errors=stage.get("errors", 0),
            warnings=stage.get("warnings", 0),
        )
        self._console.print(f"{'':>{self._VERBOSE_INDENT}}{formatted}")

    def _print_verbose_result(
        self,
        display_name: str,
        status: "BuildStatus",
        warnings: int,
        errors: int,
    ) -> None:
        """Print verbose mode completion message."""
        if status in (BuildStatus.SUCCESS, BuildStatus.WARNING):
            if warnings > 0:
                self._console.print(
                    f"[yellow]⚠ {display_name} completed with "
                    f"{warnings} warning(s)[/yellow]"
                )
            else:
                self._console.print(f"[green]✓ {display_name} completed[/green]")
        else:
            self._console.print(f"[red]✗ {display_name} failed[/red]")

    def _print_compact_result(
        self,
        display_name: str,
        status: "BuildStatus",
        warnings: int,
    ) -> None:
        """Print compact mode completion message."""
        if status == BuildStatus.FAILED:
            self._console.print(f"[red bold]✗ {display_name}[/red bold]")
        elif status == BuildStatus.WARNING or warnings > 0:
            self._console.print(f"[yellow bold]⚠ {display_name}[/yellow bold]")
        # Success is silent in compact mode
