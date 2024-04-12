# pylint: disable=too-few-public-methods

"""Schema and utils for atopile config files."""

import copy
import fnmatch
import logging
from pathlib import Path
from typing import Optional

import cattrs
import deepdiff
from attrs import Factory, define
from ruamel.yaml import YAML

import atopile.errors
import atopile.version
from atopile import address

log = logging.getLogger(__name__)
yaml = YAML()


CONFIG_FILENAME = "ato.yaml"
ATO_DIR_NAME = ".ato"
MODULE_DIR_NAME = "modules"
BUILD_DIR_NAME = "build"


_converter = cattrs.Converter()


class AtoConfigError(atopile.errors.AtoError):
    """An error in the config file."""


@define
class ProjectPaths:
    """Config grouping for all the paths in a project."""

    src: Path = "elec/src"
    layout: Path = "elec/layout"


@define
class ProjectBuildConfig:
    """Config for a build."""

    entry: Optional[str] = None
    targets: list[str] = ["__default__"]
    fail_on_drcs: bool = False


@define
class ProjectServicesConfig:
    """A config for services used by the project."""
    components: str = "https://component-server-3033-5335559d-kjaci698.onporter.run/jlc/v1"


@define
class Dependency:
    """A dependency for a project."""

    name: str
    version_spec: Optional[str] = None
    link_broken: bool = False
    path: Optional[Path] = None

    @classmethod
    def from_str(cls, spec_str: str) -> "Dependency":
        """Create a Dependency object from a string."""
        for splitter in atopile.version.OPERATORS + ("@",):
            if splitter in spec_str:
                try:
                    name, version_spec = spec_str.split(splitter)
                    name = name.strip()
                    version_spec = version_spec.strip()
                    version_spec = splitter + version_spec
                except TypeError as ex:
                    raise atopile.errors.AtoTypeError(
                        f"Invalid dependency spec: {spec_str}"
                    ) from ex
                return cls(name, version_spec)
        return cls(name=spec_str)


@define
class ProjectConfig:
    """
    The config object for atopile.
    """

    location: Optional[Path] = None

    ato_version: str = "0.1.0"
    paths: ProjectPaths = Factory(ProjectPaths)
    builds: dict[str, ProjectBuildConfig] = Factory(dict)
    dependencies: list[str | Dependency] = Factory(list)
    services: ProjectServicesConfig = Factory(ProjectServicesConfig)

    @staticmethod
    def _sanitise_dict_keys(d: dict) -> dict:
        """Sanitise the keys of a dictionary to be valid python identifiers."""
        data = copy.deepcopy(d)
        data["ato_version"] = data.pop("ato-version")
        return data

    @staticmethod
    def _unsanitise_dict_keys(d: dict) -> dict:
        """Sanitise the keys of a dictionary to be valid python identifiers."""
        data = copy.deepcopy(d)
        data["ato-version"] = data.pop("ato_version")
        del data["location"]  # The location is saved by the literal location of the file
        return data

    @classmethod
    def structure(cls, data: dict) -> "ProjectConfig":
        """Make a config object from a dictionary."""
        try:
            return _converter.structure(cls._sanitise_dict_keys(data), cls)
        except* KeyError as exs:
            for ex in exs.exceptions:
                # FIXME: make this less shit
                raise AtoConfigError(f"Bad key in config {repr(ex)}") from ex

    def patch_config(self, original: dict) -> dict:
        """Apply a delta between the original and the current config."""
        original_cfg = self.structure(original)

        # Here we need to work around some structural changes
        # FIXME: the ideal behaviour here would be to default back to
        # the new structure whenever there's a conflict, but I can't
        # find a hook to callback to a "conflict-resolver" or the likes
        # and the exceptions don't have sufficient information to easily find them
        original_deps_by_name = {d.name: d for d in original_cfg.dependencies}
        original_dep_indicies = {d.name: i for i, d in enumerate(original_cfg.dependencies)}
        for d in self.dependencies:
            if d.name in original_deps_by_name and d != original_deps_by_name[d.name]:
                del original["dependencies"][original_dep_indicies[d.name]]
        original_cfg = self.structure(original)
        # Kill me... I'm sorry

        diff = deepdiff.DeepDiff(
            self._unsanitise_dict_keys(_converter.unstructure(original_cfg)),
            self._unsanitise_dict_keys(_converter.unstructure(self)),
        )

        delta = deepdiff.Delta(diff)
        return original + delta

    def save_changes(
        self,
        location: Optional[Path] = None
    ) -> None:
        """
        Save the changes to the config object
        """
        if location is None:
            location = self.location / CONFIG_FILENAME

        with location.open() as f:
            original = yaml.load(f)

        patched = self.patch_config(original)

        with location.open("w") as f:
            yaml.dump(patched, f)

    @classmethod
    def load(cls, location: Path) -> "ProjectConfig":
        """
        Make a config object for a project.
        """
        with location.open() as f:
            config_data = yaml.load(f)

        config = cls.structure(config_data)
        config.location = location.parent.expanduser().resolve().absolute()

        return config


## Register hooks for cattrs to handle the custom types

_converter.register_structure_hook(
    str | Dependency,
    lambda d, _: Dependency.from_str(d) if isinstance(d, str) else _converter.structure(d, Dependency),
)

##


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
        _loaded_configs[project_config_file] = ProjectConfig.load(project_config_file)
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
    fail_on_drcs: bool

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
            fail_on_drcs=build_config.fail_on_drcs,
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
