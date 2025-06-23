# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import io
import logging
import os
import sys

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


def setup_basic_logging():
    if FLOG_FMT:
        logging.basicConfig(
            format="%(message)s",
            level=logging.INFO,
            datefmt="[%H:%M:%S]",
            handlers=[
                RichHandler(
                    console=Console(
                        safe_box=False,
                        theme=theme,
                        force_terminal=True,
                        width=int(TERMINAL_WIDTH),
                    ),
                    highlighter=NodeHighlighter(),
                )
            ],
        )

    if PLOG:
        from faebryk.libs.picker.picker import logger as plog

        plog.setLevel(logging.DEBUG)


class NodeHighlighter(RegexHighlighter):
    """
    Apply style to anything that looks like an faebryk Node\n
    <*|XOR_with_NANDS.nands[2]|NAND.inputs[0]|Logic> with
      <*|TI_CD4011BE.nands[2]|ElectricNAND.inputs[0]|ElectricLogic>\n
    \t<> = Node\n
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
