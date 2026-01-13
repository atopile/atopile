# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import io
import logging
import os
import re
import sys
import time

import rich
from rich.console import Console
from rich.highlighter import RegexHighlighter
from rich.logging import RichHandler
from rich.markdown import Markdown
from rich.table import Table
from rich.theme import Theme
from rich.tree import Tree

from faebryk.libs.util import ConfigFlag, ConfigFlagInt


def rich_print_robust(message: str, markdown: bool = False):
    """
    Hack for terminals that don't support unicode
    There is probably a better way to do this, but this is a quick fix for now.
    """
    try:
        rich.print(Markdown(message) if markdown else message)
    except UnicodeEncodeError:
        message = message.encode("ascii", errors="ignore").decode("ascii")
        rich.print(Markdown(message) if markdown else message)
    except Exception:
        # Handle errors from Pygments plugin loading (e.g., old entry points)
        # or other rendering issues - fall back to plain text
        if markdown:
            # Try to extract plain text from markdown code blocks
            # Remove markdown code block syntax but keep content
            plain_message = re.sub(r"```\w*\n", "", message)
            plain_message = re.sub(r"```$", "", plain_message, flags=re.MULTILINE)
            rich.print(plain_message)
        else:
            rich.print(message)


def is_piped_to_file() -> bool:
    return not sys.stdout.isatty()


def get_terminal_width() -> int:
    if is_piped_to_file():
        if "COLUMNS" in os.environ:
            return int(os.environ["COLUMNS"])
        else:
            return 240
    else:
        return Console().size.width


PLOG = ConfigFlag("PLOG", descr="Enable picker debug log")
FLOG_FMT = ConfigFlag("LOG_FMT", descr="Enable (old) log formatting")
TERMINAL_WIDTH = ConfigFlagInt(
    "TERMINAL_WIDTH",
    default=get_terminal_width(),
    descr="Width of the terminal",
)
NET_LINE_WIDTH = int(TERMINAL_WIDTH) - 40


LOG_TIME = ConfigFlag("LOG_TIME", default=True, descr="Enable logging of time")
LOG_FILEINFO = ConfigFlag(
    "LOG_FILEINFO", default=True, descr="Enable logging of file info"
)


class NestedConsole(Console):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args, record=True, width=NET_LINE_WIDTH, file=io.StringIO(), **kwargs
        )

    def __str__(self):
        return self.export_text(styles=True)


def rich_to_string(rich_obj: Table | Tree) -> str:
    console = NestedConsole()
    console.print(rich_obj)
    return str(console)


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
        record.elapsed_ms = f"{elapsed_s:3.2f}s"

        # Replace level name with abbreviated colored version
        record.level_abbrev = _LEVEL_ABBREV.get(record.levelname, record.levelname)

        TIME_LEN = 5 + 2 if LOG_TIME else 0
        LEVEL_LEN = 1
        FILE_LEN = 12 + 4 if LOG_FILEINFO else 0
        FMT_HEADER_LEN = TIME_LEN + 1 + LEVEL_LEN + 1 + FILE_LEN + 1
        INDENT = " " * (FMT_HEADER_LEN + 1)
        record.nmessage = record.getMessage().replace("\n", f"\n{INDENT}")

        # fileinfo
        filename, ext = record.filename.rsplit(".", 1)
        if len(filename) > 12:
            filename = filename[:5] + "..." + filename[-4:]
        lineno = record.lineno
        fileinfo = f"{filename}:{lineno}"
        record.fileinfo = f"{fileinfo:16s}"

        return super().format(record)


def setup_basic_logging():
    if FLOG_FMT:
        handler = RichHandler(
            console=Console(
                safe_box=False,
                theme=theme,
                force_terminal=True,
                width=int(TERMINAL_WIDTH),
            ),
            highlighter=NodeHighlighter(),
            show_path=False,  # Disable path column, we include it in format
            show_level=False,  # Disable level column, we include it in format
            show_time=False,  # Disable time column, we include it in format
            markup=True,  # Enable Rich markup in format string
        )
        handler.setFormatter(
            RelativeTimeFormatter(
                ("[dim]%(fileinfo)s[/dim] " if LOG_FILEINFO else "")
                + ("[dim]%(elapsed_ms)s[/dim] " if LOG_TIME else "")
                + "%(level_abbrev)s %(nmessage)s"
            )
        )
        # force=True clears existing handlers so our formatter is used
        logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)

    if PLOG:
        from faebryk.libs.picker.picker import logger as plog

        plog.setLevel(logging.DEBUG)

    logging.getLogger("httpx").setLevel(logging.WARNING)


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


theme = Theme(
    {
        "node.Node": "bold magenta",
        "node.Type": "bright_cyan",
        "node.Parent": "bright_red",
        "node.Child": "bright_yellow",
        "node.Root": "bold yellow",
        "node.Number": "bright_green",
        #   "node.Rest": "bright_black",
        "logging.level.warning": "yellow",
        "node.Quantity": "bright_yellow",
        "node.IsSubset": "bright_blue",
        "node.Predicate": "bright_magenta",
        "node.Op": "red",
    }
)
