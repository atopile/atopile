# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from rich.console import Console
from rich.highlighter import RegexHighlighter
from rich.logging import RichHandler
from rich.theme import Theme

from faebryk.libs.util import ConfigFlag

PLOG = ConfigFlag("PLOG", descr="Enable picker debug log")
JLOG = ConfigFlag("JLOG", descr="Enable jlcpcb picker debug log")
FLOG_FMT = ConfigFlag("LOG_FMT", descr="Enable (old) log formatting")


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
                    ),
                    highlighter=NodeHighlighter(),
                )
            ],
        )
    else:
        logging.basicConfig(level=logging.INFO)

    if PLOG:
        from faebryk.library.has_multi_picker import logger as plog

        plog.setLevel(logging.DEBUG)
        from faebryk.libs.picker.picker import logger as rlog

        rlog.setLevel(logging.DEBUG)
    if JLOG:
        from faebryk.libs.picker.jlcpcb.jlcpcb import logger as jlog

        jlog.setLevel(logging.DEBUG)


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
        r"(?P<Predicate>(is|⊆|≥|≤|)!?!?[✓✗]?)",
        # Literal Is/IsSubset
        r"(?P<IsSubset>{(I|S)\|[^}]+})",
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
