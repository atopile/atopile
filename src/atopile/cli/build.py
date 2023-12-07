"""CLI command definition for `ato build`."""

import logging
import sys
from itertools import chain
from pathlib import Path
from textwrap import dedent

import click
import rich
import rich.tree
from omegaconf import OmegaConf

from atopile import address
from atopile.address import AddrStr
from atopile.cli.common import project_options
from atopile.config import Config
from atopile.errors import ErrorHandler, HandlerMode
from atopile.front_end import Dizzy, Instance, Lofty, Scoop
from atopile.parse import FileParser
import logging
from collections import ChainMap, defaultdict
from pathlib import Path
from typing import Any, Callable, Hashable, Iterable, Iterator, List, Optional, Tuple

from attrs import define, frozen
from toolz import groupby
from pathlib import Path

from atopile.datatypes import Ref
from atopile.loop_soup import LoopSoup 

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


@click.command()
@project_options
@click.option("--debug/--no-debug", default=None)
@click.option("--strict/--no-strict", default=None)
def build(
    config: Config,
    debug: bool,
    strict: bool,
):
    """
    Build the specified --target(s) or the targets specified by the build config.
    Specify the root source file with the argument SOURCE.
    eg. `ato build --target my_target path/to/source.ato:module.path`
    """
    # input sanitisation
    # if debug:
    #     import atopile.parser.parser  # pylint: disable=import-outside-toplevel
    #     atopile.parser.parser.log.setLevel(logging.DEBUG)

    if strict is None:
        strict = False


    log.info("Writing build output to %s", config.paths.abs_build)
    config.paths.abs_build.mkdir(parents=True, exist_ok=True)

    # Do the build