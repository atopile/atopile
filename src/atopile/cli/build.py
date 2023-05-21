import logging
from pathlib import Path

import click

from atopile.netlist.kicad6 import KicadNetlist
from atopile.parser.parser import build as build_model
from atopile.project.project import Project

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


@click.command()
@click.argument("path", type=click.Path(exists=True))
@click.argument("entrypoint", type=str, required=False)
@click.option("--output", type=click.Path(exists=False))
@click.option("--debug/--no-debug", default=False)
def build(path, entrypoint, output, debug: bool):
    if debug:
        import atopile.parser.parser
        atopile.parser.parser.log.setLevel(logging.DEBUG)

    path  = Path(path)
    project = Project.from_path(path)
    model = build_model(project, path)

    if not entrypoint:
        entrypoint = str(project.standardise_import_path(path))

    netlist = KicadNetlist.from_model(model, entrypoint)

    if not output:
        output = path.with_suffix(".net")

    netlist.to_file(output)
    log.info(f"Wrote netlist to {output}")
