# pylint: disable=too-few-public-methods

"""Schema and utils for atopile config files."""

import collections.abc
import logging
from pathlib import Path
from typing import Any, Optional

import yaml
from attrs import Factory, define
from omegaconf import MISSING, OmegaConf


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


USER_CONFIG_PATH = Path("~/.atopile/config.yaml").expanduser().resolve().absolute()


@define
class Paths:
    """Config grouping for all the paths in a project."""
    project: Path = MISSING  # should be the absolute path to the project root

    src: Path = "./"
    abs_src: Path = "${.project}/${.src}"

    build: Path = "build"
    abs_build: Path = "${.project}/${.build}"

    footprints: Path = "elec/lib/lib.pretty"
    abs_footprints: Path = "${.project}/${.footprints}"

    kicad_project: Path = "elec/layout"
    abs_kicad_project: Path = "${.project}/${.kicad_project}"

    selected_build_path: Path = "${.abs_build}/${selected_build_name}"


@define
class BuildConfig:
    """Config for a build."""
    entry: str = MISSING
    abs_entry: str = "${paths.abs_src}/${.entry}"

    targets: list[str] = [
        "designators",
        "netlist-kicad6",
        "bom-jlcpcb",
        "kicad-lib-paths",
    ]


@define
class Config:
    """
    The config object for atopile.
    NOTE: this is the config for both the project, and the user.
    Project settings take precedent over user settings.
    """
    ato_version: str = "^0.0.0"

    paths: Paths = Factory(Paths)

    builds: dict[str, BuildConfig] = Factory(lambda: {"default": BuildConfig()})
    default_build: BuildConfig = "${.builds[default]}"

    selected_build_name: str = "default"
    selected_build: BuildConfig = "${.builds[${.selected_build_name}]}"


def _sanitise_key(s: str) -> str:
    """Sanitise a string to be a valid python identifier."""
    return s.replace("-", "_")


def _sanitise_item(item: tuple[Any, Any]) -> tuple[Any, Any]:
    """Sanitise the key of a dictionary item to be a valid python identifier."""
    k, v = item
    if isinstance(v, collections.abc.Mapping):
        return _sanitise_key(k), _sanitise_dict_keys(v)
    return _sanitise_key(k), v


def _sanitise_dict_keys(d: collections.abc.Mapping) -> collections.abc.Mapping:
    """Sanitise the keys of a dictionary to be valid python identifiers."""
    if d is None:
        return {}
    return dict(_sanitise_item(item) for item in d.items())


def make_config(project_config: Path, build: Optional[str] = None) -> Config:
    """
    Make a config object for a project.

    The typing on this is a little white lie... because they're really OmegaConf objects.
    """
    structure = Config()
    structure.paths.project = project_config.parent  # pylint: disable=assigning-non-slot
    if build is not None:
        structure.selected_build_name = build

    if USER_CONFIG_PATH.exists():
        user_config = OmegaConf.load(USER_CONFIG_PATH)
    else:
        user_config = OmegaConf.create()  # empty config

    with project_config.open() as f:
        config_data = yaml.safe_load(f)

    return OmegaConf.merge(
        OmegaConf.structured(structure),  # structure
        user_config,  # user config
        OmegaConf.create(_sanitise_dict_keys(config_data)),  # project config
    )
