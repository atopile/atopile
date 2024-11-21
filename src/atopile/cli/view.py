# pylint: disable=logging-fstring-interpolation

"""
`ato view`
"""

import logging
from typing import Annotated

import typer

from atopile import errors
from atopile.cli.common import create_build_contexts

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def view(
    entry: Annotated[str | None, typer.Argument()] = None,
    build: Annotated[list[str], typer.Option("--build", "-b", envvar="ATO_BUILD")] = [],
    target: Annotated[
        list[str], typer.Option("--target", "-t", envvar="ATO_TARGET")
    ] = [],
    option: Annotated[
        list[str], typer.Option("--option", "-o", envvar="ATO_OPTION")
    ] = [],
):
    """
    View a block diagram or schematic of your project.
    """
    build_ctxs = create_build_contexts(entry, build, target, option)

    raise errors.AtoNotImplementedError("View is not yet implemented.")
