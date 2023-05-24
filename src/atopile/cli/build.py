import logging
from pathlib import Path
from typing import Dict, List

import click

from atopile.netlist.kicad6 import KicadNetlist, export_reference_to_path_map
from atopile.parser.parser import build_model as build_model
from atopile.project.config import BuildConfig
from atopile.project.project import Project

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


@click.command()
@click.argument("project", required=False, default=None)
@click.option("--config", type=str, default="default")
@click.option("--root-file", default=None)
@click.option("--root-node", default=None)
@click.option("--output", default=None)
@click.option("--targets", default=None)
@click.option("--debug/--no-debug", default=None)
def build(project: str, config: str, root_file, root_node, output: str, targets: str, debug: bool):
    if debug:
        import atopile.parser.parser
        atopile.parser.parser.log.setLevel(logging.DEBUG)

    # load the project config
    if project is None:
        project = Path.cwd()
    else:
        project = Path(project)
    try:
        project: Project = Project.from_path(project)
    except FileNotFoundError as e:
        raise click.ClickException(f"Could not find project at {project}.") from e

    # get project configs
    configs_by_name: Dict[str, BuildConfig] = {bc.name: bc for bc in project.config.build.configs}
    configs_by_name["default"] = project.config.build.default_config
    if config not in configs_by_name:
        raise click.ClickException(f"Unknown build config: {config}")
    config: BuildConfig = configs_by_name[config]
    log.info(f"Using build config {config.name}")

    # root-file
    if root_file is None:
        root_file = config.root_file
    if root_file is None:
        raise click.ClickException(f"No root-file specified by options or config \"{config.name}\"")
    if not root_file.exists():
        raise click.ClickException(f"root-file {root_file} does not exist")
    root_file  = Path(root_file)
    log.info(f"Using root-file {root_file}")

    model = build_model(project, root_file)

    # root-node
    if root_node is None:
        root_node = config.root_node
    if root_node is None:
        raise click.ClickException(f"No root-node specified by options or config \"{config.name}\"")
    if root_node not in model.graph.vs["path"]:
        raise click.ClickException(f"Unknown root node: {root_node}")
    log.info(f"Using root node {root_node}")

    # figure out where to put everything
    if output is None:
        output: Path = project.config.paths.build_dir
    else:
        output: Path = Path(output)
    if output.exists():
        if not output.is_dir():
            raise click.ClickException(f"{output} exists, but is not a directory")
    else:
        output.mkdir(parents=True, exist_ok=True)
    log.info(f"Writing build output to {output}")

    # get targets
    if targets is None:
        targets: List[str] = config.targets
    else:
        targets: List[str] = targets.split(",")

    # generate targets
    if "netlist" in targets:
        targets.remove("netlist")
        netlist = KicadNetlist.from_model(model, root_node)
        netlist_output = output.with_name(root_file.name).with_suffix(".net")
        netlist.to_file(netlist_output)
        log.info(f"Wrote netlist to {output}")

    if "ref-map" in targets:
        reference_path = output.with_name(root_file.name).with_suffix(".reference_map.txt")
        export_reference_to_path_map(netlist, reference_path)
        log.info(f"Wrote reference map to {reference_path}")
