# pylint: disable=logging-fstring-interpolation

"""
`ato view`
"""

import itertools
import logging
from typing import Optional

import click
import rich
from rich.table import Table
from rich.tree import Tree

from atopile import address, errors
from atopile.address import AddrStr, add_instance, get_name
from atopile.cli.common import project_options
from atopile.config import BuildContext
from atopile.front_end import Link, lofty
from atopile.instance_methods import (
    all_descendants,
    get_links,
    get_parent,
    get_children,
    iter_parents,
    match_interfaces,
    match_modules,
    match_pins,
    match_pins_and_signals,
    match_signals,
)

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


@click.command()
@project_options
def view(build_ctxs: list[BuildContext]):
    log.info(f"View? nothing to view here")