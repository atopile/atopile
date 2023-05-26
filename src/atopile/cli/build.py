import logging
from pathlib import Path
from typing import List, Tuple

import click

from atopile.netlist.kicad6 import KicadNetlist, export_reference_to_path_map
from atopile.parser.parser import build_model as build_model
from atopile.project.config import BuildConfig
from atopile.project.project import Project

from .common import ingest_config_hat

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


@click.command()
@ingest_config_hat
@click.option("--output", default=None)
@click.option("--target", multiple=True, default=None)
@click.option("--debug/--no-debug", default=None)
def build(project: Project, build_config: BuildConfig, output: str, target: Tuple[str], debug: bool):
    if debug:
        import atopile.parser.parser
        atopile.parser.parser.log.setLevel(logging.DEBUG)

    model = build_model(project, build_config)

    # figure out where to put everything
    if output is None:
        output: Path = project.config.paths.build
    else:
        output: Path = Path(output)
    if output.exists():
        if not output.is_dir():
            raise click.ClickException(f"{output} exists, but is not a directory")
    else:
        output.mkdir(parents=True, exist_ok=True)
    log.info(f"Writing build output to {output}")

    # ensure targets
    if not target:
        target: List[str] = build_config.targets
    targets_string = ", ".join(target)
    log.info(f"Generating targets {targets_string}")

    # generate targets
    output_base = (output / build_config.root_file.name).with_suffix('')
    if "netlist" in target:
        target.remove("netlist")
        netlist = KicadNetlist.from_model(model, build_config.root_node)
        netlist_output = output_base.with_suffix(".net")
        netlist.to_file(netlist_output)
        log.info(f"Wrote netlist to {netlist_output}")

    if "ref-map" in target:
        reference_path = output_base.with_suffix(".reference_map.txt")
        export_reference_to_path_map(netlist, reference_path)
        log.info(f"Wrote reference map to {reference_path}")
