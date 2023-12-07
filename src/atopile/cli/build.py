"""CLI command definition for `ato build`."""

import logging
from itertools import chain
from pathlib import Path

import click

from atopile import address
from atopile.address import AddrStr
from atopile.cli.common import project_options
from atopile.config import Config

from atopile.netlist import get_netlist_as_str
from atopile.bom import generate_bom
from atopile.front_end import set_search_paths


log = logging.getLogger("build")
log.setLevel(logging.INFO)


@click.command()
@project_options
@click.option("--debug/--no-debug", default=None)
def build(config: Config, debug: bool):
    """
    Build the specified --target(s) or the targets specified by the build config.
    Specify the root source file with the argument SOURCE.
    eg. `ato build --target my_target path/to/source.ato:module.path`
    """
    if debug:
        log.setLevel(logging.DEBUG)


    log.info("Writing build output to %s", config.paths.abs_build)
    config.paths.abs_build.mkdir(parents=True, exist_ok=True)

    set_search_paths([config.paths.abs_src])

    output_base_name = Path(config.selected_build.abs_entry).with_suffix("").name

    with open(config.paths.abs_build / f"{output_base_name}.net", "w", encoding="utf-8") as f:
        f.write(get_netlist_as_str(config.selected_build.abs_entry))

    with open(config.paths.abs_build / f"{output_base_name}.csv", "w", encoding="utf-8") as f:
        f.write(generate_bom(config.selected_build.abs_entry))
