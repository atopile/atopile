"""CLI command definition for `ato build`."""

import logging
import sys
from pathlib import Path
from omegaconf import OmegaConf
from atopile.config import Config

import click

from atopile.cli.common import project_options

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
    log.info("Writing build output to %s", config)
    # input sanitisation
    # if debug:
    #     import atopile.parser.parser  # pylint: disable=import-outside-toplevel

    #     atopile.parser.parser.log.setLevel(logging.DEBUG)

    if strict is None:
        strict = False

    # build core model
    #model = build_model(project) #TODO: initate the build process
    exit_code = 0


    # generate targets
    log.info("Writing build output to %s", config.abs_build)
    config.paths.abs_build.mkdir(parents=True, exist_ok=True)

    
