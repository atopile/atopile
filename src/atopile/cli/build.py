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
    error_handler = ErrorHandler(handel_mode=HandlerMode.RAISE_ALL)

    search_paths = [
        Path("/Users/mattwildoer/Projects/atopile-workspace/servo-drive/elec/src/"),
    ]

    parser = FileParser()

    scoop = Scoop(error_handler, parser.get_ast_from_file, search_paths)
    dizzy = Dizzy(error_handler, scoop.get_obj_def)
    lofty = Lofty(error_handler, dizzy.get_obj_layer)

    entry_instance_tree = lofty.get_instance_tree(from_parts("/Users/mattwildoer/Projects/atopile-workspace/servo-drive/elec/src/spin_servo_nema17.ato", "SpinServoNEMA17"))

    
