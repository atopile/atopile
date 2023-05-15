import click
from atopile.netlist.kicad6 import KicadNetlist
from pathlib import Path

from atopile.parser.parser import Builder
from atopile.project.project import Project
from atopile.utils import get_project_root

project = Project.from_path(get_project_root() / "sandbox/example_project")
model = Builder(project).build(Path(get_project_root() / "sandbox/example_project/toy.ato"))

netlist = KicadNetlist.from_model(model, "toy.ato/vdiv1")
netlist.to_file(project.root / "toy.net")

@click.command()
@click.argument("path", type=click.Path(exists=True))
@click.argument("entrypoint", type=str, required=False)
@click.option("--output", type=click.Path(exists=False))
def build(path, entrypoint, output):
    path  = Path(path)
    project = Project.from_path(path)
    model = Builder(project).build(path)

    if not entrypoint:
        entrypoint = str(project.standardise_import_path(path))

    netlist = KicadNetlist.from_model(model, entrypoint)

    if not output:
        output = path.with_suffix(".net")

    netlist.to_file(output)
