# pylint: disable=logging-fstring-interpolation

"""
`ato inspect`
"""

import logging
from typing import Annotated

import typer

log = logging.getLogger(__name__)


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
    from atopile import errors

    raise errors.UserNotImplementedError("Inspect is not yet implemented.")
