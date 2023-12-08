"""CLI command definition for `ato build`."""

import logging
import shutil
from pathlib import Path

import click

from atopile.bom import generate_bom, generate_designator_map
from atopile.cli.common import project_options
from atopile.config import ATO_DIR_NAME, MODULE_DIR_NAME, Config
from atopile.front_end import set_search_paths
from atopile.netlist import get_netlist_as_str

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

    search_paths = [config.paths.abs_src]

    try:
        ato_module_dir = get_ato_modules_dir(config.paths.project)
    except FileNotFoundError:
        log.warning(f"Could not find {ATO_DIR_NAME}/{MODULE_DIR_NAME}")
    else:
        search_paths.append(ato_module_dir)

    set_search_paths(search_paths)

    output_base_name = Path(config.selected_build.abs_entry).with_suffix("").name

    with open(
        config.paths.abs_build / f"{output_base_name}.net", "w", encoding="utf-8"
    ) as f:
        f.write(get_netlist_as_str(config.selected_build.abs_entry))

    with open(
        config.paths.abs_build / f"{output_base_name}.csv", "w", encoding="utf-8"
    ) as f:
        f.write(generate_bom(config.selected_build.abs_entry))

    generate_designator_map(config.selected_build.abs_entry)
    consolidate_footprints(config)


# TODO: move this to somewhere more generic
def get_ato_modules_dir(path: Path) -> Path:
    """
    Find the .ato/modules dir
    """
    if (path / ATO_DIR_NAME / MODULE_DIR_NAME).exists():
        return path / ATO_DIR_NAME / MODULE_DIR_NAME
    raise FileNotFoundError


def consolidate_footprints(project_config: Config) -> None:
    """Consolidate all the project's footprints into a single directory."""
    fp_target = project_config.paths.abs_build / "footprints" / "footprints.pretty"
    fp_target.mkdir(exist_ok=True, parents=True)

    for fp in project_config.paths.project.glob("**/*.kicad_mod"):
        try:
            shutil.copy(fp, fp_target)
        except shutil.SameFileError:
            log.warning("Footprint %s already exists in the target directory", fp)
