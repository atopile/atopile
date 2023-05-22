import logging
from pathlib import Path

import click

from atopile.netlist.kicad6 import KicadNetlist, export_reference_to_path_map
from atopile.parser.parser import build as build_model
from atopile.project.project import Project

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


@click.command()
@click.argument("path", type=click.Path(exists=True))
@click.argument("entrypoint", type=str, required=False)
@click.option("--output", type=click.Path(exists=False))
@click.option("--debug/--no-debug", default=False)
@click.option("--references/--no-references", default=True)
def build(path, entrypoint, output, debug: bool, references: bool):
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
        project.ensure_build_dir()
        output = (project.build_dir / path.name).with_suffix(".net")
    else:
        output = Path(output)

    netlist.to_file(output)
    log.info(f"Wrote netlist to {output}")

    if references:
        reference_path = output.with_suffix(".reference_map.txt")
        export_reference_to_path_map(netlist, reference_path)
        log.info(f"Wrote reference map to {reference_path}")
