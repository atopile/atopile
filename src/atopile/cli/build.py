"""CLI command definition for `ato build`."""

import logging
import shutil
from functools import wraps
from pathlib import Path
from typing import Callable, Optional

import click
from attrs import frozen

from atopile import address
from atopile.bom import generate_bom as _generate_bom
from atopile.bom import generate_designator_map as _generate_designator_map
from atopile.cli.common import project_options, check_compiler_versions
from atopile.config import Config
from atopile.errors import (
    handle_ato_errors,
    iter_through_errors,
    muffle_fatalities,
)
from atopile.front_end import set_search_paths
from atopile.netlist import get_netlist_as_str

log = logging.getLogger(__name__)


@click.command()
@project_options
@click.option("--debug/--no-debug", default=None)
@muffle_fatalities
def build(config: Config, debug: bool):
    """
    Build the specified --target(s) or the targets specified by the build config.
    Specify the root source file with the argument SOURCE.
    eg. `ato build --target my_target path/to/source.ato:module.path`
    """
    # Set the log level
    if debug:
        logging.root.setLevel(logging.DEBUG)

    # Make sure I an all my sub-configs have appropriate versions
    check_compiler_versions(config)

    # Set the search paths for the front end
    set_search_paths([config.paths.abs_src, config.paths.abs_module_path])

    # Create a BuildArgs object to pass to all the targets
    build_args = BuildArgs.from_config(config)

    # Ensure the build directory exists
    log.info("Writing outputs to %s", build_args.build_path)
    build_args.build_path.mkdir(parents=True, exist_ok=True)

    targets = (
        muster.targets.keys()
        if config.selected_build.targets == ["*"]
        else config.selected_build.targets
    )
    for err_cltr, target_name in iter_through_errors(targets):
        log.info("Building %s", target_name)
        with err_cltr():
            muster.targets[target_name](build_args)


@frozen
class BuildArgs:
    """A class to hold the arguments to a build."""

    # FIXME: this object exists only because the Config is a bit of a mess

    entry: address.AddrStr  # eg. "path/to/project/src/entry-name.ato:module.path"
    build_path: Path  # eg. path/to/project/build/<build-name>
    output_name: str  # eg. "entry-name.ato" -> "entry-name"
    output_base: Path  # eg. path/to/project/build/<build-name>/entry-name

    config: Config

    @classmethod
    def from_config(cls, config: Config) -> "BuildArgs":
        """Create a BuildArgs object from a Config object."""
        build_path = Path(config.paths.abs_selected_build_path)
        output_name = address.get_entry_section(config.selected_build.abs_entry)
        output_base = build_path / output_name
        return cls(
            address.AddrStr(config.selected_build.abs_entry),
            build_path,
            output_name,
            output_base,
            config,
        )


TargetType = Callable[[BuildArgs], None]


class Muster:
    """A class to register targets to."""

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self.targets = {}
        self.log = logger or logging.getLogger(__name__)

    def add_target(self, func: TargetType, name: Optional[str] = None):
        """Register a function as a target."""
        self.targets[name or func.__name__] = func
        return func

    def register(self, name: Optional[str] = None):
        """Register a target under a given name."""

        def decorator(func: TargetType):
            @wraps(func)
            def wrapper(build_args: BuildArgs):
                with handle_ato_errors():
                    return func(build_args)

            self.add_target(wrapper, name)
            return wrapper

        return decorator


muster = Muster()


@muster.register("copy-footprints")
def consolidate_footprints(build_args: BuildArgs) -> None:
    """Consolidate all the project's footprints into a single directory."""
    fp_target = build_args.config.paths.abs_build / "footprints" / "footprints.pretty"
    fp_target.mkdir(exist_ok=True, parents=True)

    for fp in build_args.config.paths.project.glob("**/*.kicad_mod"):
        try:
            shutil.copy(fp, fp_target)
        except shutil.SameFileError:
            log.debug("Footprint %s already exists in the target directory", fp)


@muster.register("netlist")
def generate_netlist(build_args: BuildArgs) -> None:
    """Generate a netlist for the project."""
    with open(build_args.output_base.with_suffix(".net"), "w", encoding="utf-8") as f:
        f.write(get_netlist_as_str(build_args.entry))


@muster.register("bom")
def generate_bom(build_args: BuildArgs) -> None:
    """Generate a BOM for the project."""
    with open(build_args.output_base.with_suffix(".csv"), "w", encoding="utf-8") as f:
        f.write(_generate_bom(build_args.entry))


@muster.register("designator-map")
def generate_designator_map(build_args: BuildArgs) -> None:
    """Generate a designator map for the project."""
    with open(build_args.output_base.with_suffix(".csv"), "w", encoding="utf-8") as f:
        f.write(_generate_designator_map(build_args.entry))