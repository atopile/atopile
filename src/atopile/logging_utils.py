"""
Logging utilities for atopile builds.

This module provides:
- Progress bar components
- Rich console utilities
- Formatters and highlighters
"""

from __future__ import annotations

import io
import logging
import os
import re
import sys
import time
from enum import StrEnum

import rich
from rich.console import Console, RenderableType
from rich.highlighter import RegexHighlighter
from rich.markdown import Markdown
from rich.padding import Padding
from rich.progress import (
    MofNCompleteColumn,
    Progress,
    RenderableColumn,
    SpinnerColumn,
    Task,
    TimeElapsedColumn,
)
from rich.table import Column, Table
from rich.text import Text
from rich.theme import Theme
from rich.tree import Tree

from faebryk.libs.util import ConfigFlag, ConfigFlagInt

# =============================================================================
# Rich Console Configuration (formerly cli/console.py)
# =============================================================================

# Theme for faebryk-style node highlighting
faebryk_theme = Theme(
    {
        "node.Node": "bold magenta",
        "node.Type": "bright_cyan",
        "node.Parent": "bright_red",
        "node.Child": "bright_yellow",
        "node.Root": "bold yellow",
        "node.Number": "bright_green",
        "logging.level.warning": "yellow",
        "node.Quantity": "bright_yellow",
        "node.IsSubset": "bright_blue",
        "node.Predicate": "bright_magenta",
        "node.Op": "red",
    }
)

rich.reconfigure(theme=faebryk_theme)

# Console should be a singleton to avoid intermixing logging w/ other output
console = rich.get_console()
error_console = rich.console.Console(theme=faebryk_theme, stderr=True)

# Lazy import to avoid circular dependency
def _get_terminal_width() -> int:
    """Get terminal width, avoiding circular import."""
    import os
    import sys
    from rich.console import Console
    
    if not sys.stdout.isatty():
        if "COLUMNS" in os.environ:
            return int(os.environ["COLUMNS"])
        return 240
    return Console().size.width

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
    return Console().size.width


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


# Abbreviated level names with Rich color markup
_LEVEL_ABBREV = {
    "DEBUG": "[cyan]D[/cyan]",
    "INFO": "[green]I[/green]",
    "WARNING": "[yellow]W[/yellow]",
    "ERROR": "[red]E[/red]",
    "CRITICAL": "[bold red]C[/bold red]",
}


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
