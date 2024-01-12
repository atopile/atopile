# pylint: disable=too-few-public-methods

"""Schema and utils for atopile config files."""

import collections.abc
from pathlib import Path
from typing import Any

import yaml
from attrs import Factory, define
from omegaconf import MISSING, OmegaConf

from atopile import address
import atopile.errors

CONFIG_FILENAME = "ato.yaml"
ATO_DIR_NAME = ".ato"
MODULE_DIR_NAME = "modules"
BUILD_DIR_NAME = "build"


@define
class UserPaths:
    """Config grouping for all the paths in a project."""

    src: Path = "./"
    layout: Path = "elec/layout"


@define
class UserBuildConfig:
    """Config for a build."""

    entry: str = MISSING
    targets: list[str] = ["*"]


@define
class UserConfig:
    """
    The config object for atopile.
    """

    location: Path = MISSING

    ato_version: str = "0.1.0"
    paths: UserPaths = Factory(UserPaths)
    builds: dict[str, UserBuildConfig] = Factory(dict)
    dependencies: list[str] = []


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


def make_config(project_config: Path) -> UserConfig:
    """
    Make a config object for a project.

    The typing on this is a little white lie... because they're really OmegaConf objects.
    """
    structure = UserConfig()

    with project_config.open() as f:
        config_data = yaml.safe_load(f)

    structure.location = project_config.parent.expanduser().resolve().absolute()

    return OmegaConf.merge(
        OmegaConf.structured(structure),  # structure
        OmegaConf.create(_sanitise_dict_keys(config_data)),  # project config
    )


def get_project_dir_from_path(path: Path) -> Path:
    """
    Resolve the project directory from the specified path.
    """
    for p in [path] + list(path.parents):
        clean_path = p.resolve().absolute()
        if (clean_path / CONFIG_FILENAME).exists():
            return clean_path
    raise FileNotFoundError(
        f"Could not find {CONFIG_FILENAME} in {path} or any parents"
    )


_loaded_configs: dict[Path, str] = {}


def get_project_config_from_path(path: Path) -> UserConfig:
    """
    Get the project config from an address.
    """
    project_dir = get_project_dir_from_path(path)
    project_config_file = project_dir / CONFIG_FILENAME
    if project_config_file not in _loaded_configs:
        _loaded_configs[project_config_file] = make_config(project_config_file)
    return _loaded_configs[project_config_file]


def get_project_config_from_addr(addr: str) -> UserConfig:
    """
    Get the project config from an address.
    """
    return get_project_config_from_path(Path(address.get_file(addr)))


# FIXME: we need factory constructors for these classes
@define
class ProjectContext:
    """A class to hold the arguments to a project."""

    layout_path: Path  # eg. path/to/project/layouts/default/default.kicad_pcb
    project_path: Path  # abs path to the project directory
    src_path: Path  # abs path to the source directory
    module_path: Path  # abs path to the module directory

    @classmethod
    def from_config(cls, config: UserConfig) -> "ProjectContext":
        """Create a BuildArgs object from a Config object."""

        return ProjectContext(
            layout_path=Path(config.location) / config.paths.layout,
            project_path=Path(config.location),
            src_path=Path(config.location) / config.paths.src,
            module_path=Path(config.location) / ATO_DIR_NAME / MODULE_DIR_NAME,
        )

    @classmethod
    def from_path(cls, path: Path) -> "ProjectContext":
        """Create a BuildArgs object from a Config object."""
        return cls.from_config(get_project_config_from_path(path))


@define
class BuildContext:
    """A class to hold the arguments to a build."""

    name: str

    entry: address.AddrStr  # eg. "path/to/project/src/entry-name.ato:module.path"
    targets: list[str]
    layout_path: Path  # eg. path/to/project/layouts/default/default.kicad_pcb

    layout_path: Path  # eg. path/to/project/layouts/default/default.kicad_pcb
    project_path: Path  # abs path to the project directory
    src_path: Path  # abs path to the source directory
    module_path: Path  # abs path to the module directory
    build_path: Path  # eg. path/to/project/build/<build-name>

    output_base: Path  # eg. path/to/project/build/<build-name>/entry-name

    @classmethod
    def from_config(cls, config: UserConfig, build_name: str) -> "BuildContext":
        """Create a BuildArgs object from a Config object."""
        build_config = config.builds[build_name]

        abs_entry = address.AddrStr(config.location / build_config.entry)

        build_path = Path(config.location) / BUILD_DIR_NAME

        layout_base = config.location / config.paths.layout / build_name
        if layout_base.with_suffix(".kicad_pcb").exists():
            layout_path = layout_base.with_suffix(".kicad_pcb")
        elif layout_base.is_dir():
            layout_candidates = list(layout_base.glob("*.kicad_pcb"))
            if len(layout_candidates) == 1:
                layout_path = layout_candidates[0]
            else:
                raise atopile.errors.AtoError(
                    "Layout directories must contain exactly 1 layout,"
                    f" but {len(layout_path)} found in {layout_base}"
                )
        else:
            raise atopile.errors.AtoError("Layout file not found")

        return BuildContext(
            name=build_name,
            entry=abs_entry,
            targets=build_config.targets,
            layout_path=layout_path,
            project_path=Path(config.location),
            src_path=Path(config.location) / config.paths.src,
            module_path=Path(config.location) / ATO_DIR_NAME / MODULE_DIR_NAME,
            build_path=build_path,
            output_base=build_path / build_name,
        )
