# pylint: disable=too-few-public-methods

"""Schema and utils for atopile config files."""

import collections.abc
import fnmatch
import logging
from pathlib import Path
from typing import Any, Optional

import yaml
from attrs import Factory, define
from omegaconf import MISSING, OmegaConf
from omegaconf.errors import ConfigKeyError

import atopile.errors
from atopile import address

log = logging.getLogger(__name__)


CONFIG_FILENAME = "ato.yaml"
ATO_DIR_NAME = ".ato"
MODULE_DIR_NAME = "modules"
BUILD_DIR_NAME = "build"


@define
class ProjectPaths:
    """Config grouping for all the paths in a project."""

    src: Path = "./"
    layout: Path = "elec/layout"


@define
class ProjectBuildConfig:
    """Config for a build."""

    entry: str = MISSING
    targets: list[str] = ["__default__"]


@define
class ProjectServicesConfig:
    """A config for services used by the project."""
    components: str = "https://atopile-component-server-atsuhzfd5a-uc.a.run.app/jlc"


@define
class ProjectConfig:
    """
    The config object for atopile.
    """

    location: Path = MISSING

    ato_version: str = "0.1.0"
    paths: ProjectPaths = Factory(ProjectPaths)
    builds: dict[str, ProjectBuildConfig] = Factory(dict)
    dependencies: list[str] = []
    services: ProjectServicesConfig = Factory(ProjectServicesConfig)


KEY_CONVERSIONS = {
    "ato-version": "ato_version",
}


def _sanitise_key(key: str) -> str:
    """Sanitize a key."""
    return KEY_CONVERSIONS.get(key, key)


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


def make_config(project_config: Path) -> ProjectConfig:
    """
    Make a config object for a project.

    The typing on this is a little white lie... because they're really OmegaConf objects.
    """
    structure: ProjectConfig = OmegaConf.structured(ProjectConfig())

    with project_config.open() as f:
        config_data = yaml.safe_load(f)
    project_config_data = OmegaConf.create(_sanitise_dict_keys(config_data))

    structure.location = project_config.parent.expanduser().resolve().absolute()

    for _ in range(1000):
        try:
            return OmegaConf.merge(
                structure,
                project_config_data,
            )
        except ConfigKeyError as ex:
            dot_path = ex.full_key.split(".")
            container = project_config_data
            for key in dot_path[:-1]:
                container = container[key]
            del container[dot_path[-1]]

            atopile.errors.AtoError(
                f"Unknown config option in {structure.location}. Ignoring \"{ex.full_key}\".",
                title="Unknown config option",
            ).log(log, logging.WARNING)
    raise atopile.errors.AtoError("Too many config errors")


def get_project_dir_from_path(path: Path) -> Path:
    """
    Resolve the project directory from the specified path.
    """
    #TODO: when provided with the "." path, it doesn't find the config in parent directories
    path = Path(path)
    for p in [path] + list(path.parents):
        clean_path = p.resolve().absolute()
        if (clean_path / CONFIG_FILENAME).exists():
            return clean_path
    raise atopile.errors.AtoFileNotFoundError(
        f"Could not find {CONFIG_FILENAME} in {path} or any parents"
    )


_loaded_configs: dict[Path, str] = {}


def get_project_config_from_path(path: Path) -> ProjectConfig:
    """
    Get the project config from a path.
    """
    project_dir = get_project_dir_from_path(path)
    project_config_file = project_dir / CONFIG_FILENAME
    if project_config_file not in _loaded_configs:
        _loaded_configs[project_config_file] = make_config(project_config_file)
    return _loaded_configs[project_config_file]


def get_project_config_from_addr(addr: str) -> ProjectConfig:
    """
    Get the project config from an address.
    """
    return get_project_config_from_path(Path(address.get_file(addr)))


# FIXME: we need factory constructors for these classes
@define
class ProjectContext:
    """A class to hold the arguments to a project."""

    project_path: Path  # abs path to the project directory
    src_path: Path  # abs path to the source directory
    module_path: Path  # abs path to the module directory
    layout_path: Path  # eg. path/to/project/layouts/default/default.kicad_pcb
    config: ProjectConfig

    @classmethod
    def from_config(cls, config: ProjectConfig) -> "ProjectContext":
        """Create a BuildArgs object from a Config object."""

        return ProjectContext(
            project_path=Path(config.location),
            src_path=Path(config.location) / config.paths.src,
            module_path=Path(config.location) / ATO_DIR_NAME / MODULE_DIR_NAME,
            layout_path=Path(config.location) / config.paths.layout,
            config=config,
        )

    @classmethod
    def from_path(cls, path: Path) -> "ProjectContext":
        """Create a BuildArgs object from a Config object."""
        return cls.from_config(get_project_config_from_path(path))


def match_user_layout(path: Path) -> bool:
    """Check whether a given filename is a KiCAD autosaved layout."""
    autosave_patterns = [
        "_autosave-*",
        "*-save.kicad_pcb",
    ]

    name = path.name

    for pattern in autosave_patterns:
        if fnmatch.fnmatch(name, pattern):
            return False
    return True


def find_layout(layout_base: Path) -> Optional[Path]:
    """Return the layout associated with a build."""
    if layout_base.with_suffix(".kicad_pcb").exists():
        return layout_base.with_suffix(".kicad_pcb").resolve().absolute()
    elif layout_base.is_dir():
        layout_candidates = list(
            filter(
                match_user_layout,
                layout_base.glob("*.kicad_pcb")
            )
        )

        if len(layout_candidates) == 1:
            return layout_candidates[0].resolve().absolute()

        else:
            raise atopile.errors.AtoError(
                "Layout directories must contain only 1 layout,"
                f" but {len(layout_candidates)} found in {layout_base}"
            )


@define
class BuildContext:
    """A class to hold the arguments to a build."""
    project_context: ProjectContext

    name: str

    entry: address.AddrStr  # eg. "path/to/project/src/entry-name.ato:module.path"
    targets: list[str]

    layout_path: Optional[Path]  # eg. path/to/project/layouts/default/default.kicad_pcb
    build_path: Path  # eg. path/to/project/build/<build-name>

    output_base: Path  # eg. path/to/project/build/<build-name>/entry-name

    @classmethod
    def from_config(
        cls,
        config_name: str,
        build_config: ProjectBuildConfig,
        project_context: ProjectContext
    ) -> "BuildContext":
        """Create a BuildArgs object from a Config object."""
        abs_entry = address.AddrStr(project_context.project_path / build_config.entry)

        build_path = Path(project_context.project_path) / BUILD_DIR_NAME

        return BuildContext(
            project_context=project_context,
            name=config_name,
            entry=abs_entry,
            targets=build_config.targets,
            layout_path=find_layout(project_context.project_path / project_context.layout_path / config_name),
            build_path=build_path,
            output_base=build_path / config_name,
        )

    @classmethod
    def from_config_name(cls, config: ProjectConfig, build_name: str) -> "BuildContext":
        """Create a BuildArgs object from a Config object."""
        project_context = ProjectContext.from_config(config)

        try:
            build_config = config.builds[build_name]
        except KeyError as ex:
            raise atopile.errors.AtoError(
                f"Build {build_name} not found for project {config.location}\n"
                f"Available builds: {list(config.builds.keys())}"
            ) from ex

        return cls.from_config(build_name, build_config, project_context)


_project_context: Optional[ProjectContext] = None


def set_project_context(project_context: ProjectContext) -> None:
    """
    Set the project context for the current process.
    """
    global _project_context
    _project_context = project_context


def get_project_context() -> ProjectContext:
    """
    Get the project context for the current process.
    """
    if _project_context is None:
        raise ValueError("Project context not set")
    return _project_context
