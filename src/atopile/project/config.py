import collections.abc
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import yaml
from attrs import Factory, define
from omegaconf import MISSING, OmegaConf

if TYPE_CHECKING:
    # See: https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
    from atopile.project.project import Project

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


USER_CONFIG_PATH = Path("~/.atopile/config.yaml").expanduser().resolve().absolute()


def _sanitise_key(s: str) -> str:
    return s.replace("-", "_")


def _sanitise_item(item: tuple[Any, Any]) -> tuple[Any, Any]:
    k, v = item
    if isinstance(v, collections.abc.Mapping):
        return _sanitise_key(k), _sanitise_dict_keys(v)
    return _sanitise_key(k), v


def _sanitise_dict_keys(d: collections.abc.Mapping) -> collections.abc.Mapping:
    return dict(_sanitise_item(item) for item in d.items())


@define
class Paths:
    project: Path = MISSING  # should be the absolute path to the project root

    build: Path = "build"
    abs_build: Path = "${.project}/${.build}"

    footprints: Path = "../lib/lib.pretty"
    abs_footprints: Path = "${.project}/${.footprints}"


@define
class BuildConfig:
    entry: str = MISSING

    targets: list[str] = [
        "designators",
        "netlist-kicad6",
        "bom-jlcpcb",
        "kicad-lib-paths",
    ]
    build_path: Path = "${..paths.abs_build}/${.name}"


@define
class Config:
    paths: Paths = Factory(Paths)

    ato_version: str = "^0.0.0"

    builds: dict[str, BuildConfig] = Factory(lambda: {"default": BuildConfig()})
    default_build: BuildConfig = "${.builds[default]}"

    selected_build_name: str = "default"
    selected_build: BuildConfig = "${.builds[${.selected_build_name}]}"


def make_config(project_config: Path, build: Optional[str] = None) -> Config:
    """
    Make a config object for a project.

    The typing on this is a little white lie... because they're really OmegaConf objects.
    """
    structure = Config()
    structure.paths.project = project_config
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
