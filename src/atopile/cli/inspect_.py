# pylint: disable=logging-fstring-interpolation

"""
`ato inspect`
"""

import logging
from typing import Annotated

import typer

from atopile import errors
from atopile.address import AddrStr

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class DisplayEntry:
    """
    This class represents the nets that are below the inspected module,
    the equivalent net that is below the context module and
    the individual connections that are made to the inspect net and the context net.
    """

    def __init__(self, net: list[list[AddrStr]]):
        self.inspect_net: list[AddrStr] = net
        self.inspect_consumer: list[AddrStr] = []
        self.context_net: list[AddrStr] = []
        self.context_consumer: list[AddrStr] = []


odd_row = "on grey11 cornflower_blue"
even_row = "on grey15 cornflower_blue"
odd_greyed_row = "on grey11 grey0"
even_greyed_row = "on grey15 grey0"


def inspect(
    entry: Annotated[str | None, typer.Argument()] = None,
    build: Annotated[list[str], typer.Option("--build", "-b", envvar="ATO_BUILD")] = [],
    target: Annotated[
        list[str], typer.Option("--target", "-t", envvar="ATO_TARGET")
    ] = [],
    option: Annotated[
        list[str], typer.Option("--option", "-o", envvar="ATO_OPTION")
    ] = [],
    inspect: str | None = None,
    context: Annotated[
        str | None,
        typer.Option(
            "--context", "-c", help="The context from which to inspect the module"
        ),
    ] = None,
    dump_csv: Annotated[
        str | None,
        typer.Option("--dump-csv", "-d", help="Output the inspection to a CSV file"),
    ] = None,
):
    """
    Utility to inspect what is connected to a component.
    The context sets the boundary where something is considered connected.
    For example: `--inspect rp2040_micro --context rp2040_micro_ki`
    """
    raise errors.UserNotImplementedError("Inspect is not yet implemented.")
