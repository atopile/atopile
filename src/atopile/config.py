import fnmatch
import functools
import logging
import os
import re
import sys
from abc import ABC, abstractmethod
from contextlib import _GeneratorContextManager, contextmanager
from contextvars import ContextVar
from enum import Enum
from pathlib import Path
from typing import (
    Annotated,
    Any,
    Callable,
    Generator,
    Iterable,
    Literal,
    Self,
    Union,
    override,
)

from more_itertools import first
from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    ValidationInfo,
    field_serializer,
    field_validator,
    model_validator,
)
from pydantic.networks import HttpUrl
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    SettingsError,
    YamlConfigSettingsSource,
)
from ruamel.yaml import YAML

from atopile import address, version
from atopile.address import AddressError, AddrStr
from atopile.errors import (
    UserBadParameterError,
    UserException,
    UserFileNotFoundError,
    UserNoProjectException,
)
from atopile.version import (
    DISTRIBUTION_NAME,
    clean_version,
    get_installed_atopile_version,
)
from faebryk.libs.exceptions import UserResourceException
from faebryk.libs.paths import get_config_dir
from faebryk.libs.test.testutil import in_test
from faebryk.libs.util import indented_container, md_list

logger = logging.getLogger(__name__)
yaml = YAML()


APPLICATION_NAME = "atopile"
ENV_VAR_PREFIX = "ATO_"
PROJECT_CONFIG_FILENAME = "ato.yaml"
GLOBAL_CONFIG_FILENAME = "config.yaml"


def _loc_to_dot_sep(loc: tuple[str | int, ...]) -> str:
    # via https://docs.pydantic.dev/dev/errors/errors/#customize-error-messages
    path = ""
    for i, x in enumerate(loc):
        if isinstance(x, str):
            if i > 0:
                path += "."
            path += x
        elif isinstance(x, int):
            path += f"[{x}]"
        else:
            raise TypeError("Unexpected type")
    return path


def _convert_errors(e: ValidationError) -> list[dict[str, Any]]:
    return [
        {"msg": error["msg"], "loc": _loc_to_dot_sep(error["loc"])}
        for error in e.errors()
    ]


def _try_construct_config[T](
    model: type[T], identifier: str | Path | None = None, **kwargs: Any
) -> T:
    message_prefix = f"`{identifier}`: " if identifier else ""

    try:
        return model(**kwargs)
    except ValidationError as ex:
        excs = ExceptionGroup(
            "Configuration is invalid",
            [
                UserConfigurationError(
                    f"{message_prefix}{error['msg']}: `{error['loc']}`"
                )
                for error in _convert_errors(ex)
            ],
        )
        raise excs from ex
    except SettingsError as ex:
        raise UserConfigurationError(f"Invalid config: {ex}") from ex


class BaseConfigModel(BaseModel):
    model_config = ConfigDict(use_attribute_docstrings=True)


class BuildType(Enum):
    ATO = "ato"
    PYTHON = "python"


class UserConfigurationError(UserException):
    """An error in the config file."""


class UserConfigNotFoundError(UserException):
    """No project config file was found."""


class ConfigFileSettingsSource(YamlConfigSettingsSource, ABC):
    def __init__(self, settings_cls: type[BaseSettings]):
        self.yaml_file_path = self.find_config_file()
        self.yaml_file_encoding = "utf-8"
        self.yaml_data = self._read_files(self.yaml_file_path)

        super(YamlConfigSettingsSource, self).__init__(settings_cls, self.get_data())

    @classmethod
    @abstractmethod
    def find_config_file(cls) -> Path | None: ...

    @abstractmethod
    def get_data(self) -> dict[str, Any]: ...


class GlobalConfigSettingsSource(ConfigFileSettingsSource):
    @classmethod
    def find_config_file(cls) -> Path | None:
        config_file = get_config_dir() / GLOBAL_CONFIG_FILENAME
        return config_file if config_file.exists() else None

    def get_data(self) -> dict[str, Any]:
        return self.yaml_data if self.yaml_data else {}


@functools.cache
def find_project_dir(start: Path) -> Path | None:
    """
    Search parent directories, up to the root, for a directory containing a project
    config file.
    """
    path = start
    while not (path / PROJECT_CONFIG_FILENAME).is_file():
        path = path.parent
        if path == path.parent:
            return None

    return path.resolve().absolute()


def find_project_config_file(start: Path) -> Path | None:
    """Search parent directories, up to the root, for a project config file."""
    if (project_dir := find_project_dir(start)) is not None:
        return project_dir / PROJECT_CONFIG_FILENAME

    return None


class ProjectConfigSettingsSource(ConfigFileSettingsSource):
    @classmethod
    def find_config_file(cls) -> Path | None:
        """
        Find a project config file in the specified directory or any parent directories.
        """
        if _project_dir:
            return _project_dir / PROJECT_CONFIG_FILENAME

        return find_project_config_file(Path.cwd())

    def get_data(self) -> dict[str, Any]:
        return self.yaml_data or {}


class ProjectPaths(BaseConfigModel):
    """
    Project global paths
    """

    root: Path
    """Project root directory (where the ato.yaml file is located)"""

    src: Path
    """Project source code directory"""

    parts: Path
    """Source code directory for parts"""

    layout: Path
    """Project layout directory where KiCAD projects are stored and searched for"""

    build: Path
    """Build artifact output directory"""

    logs: Path
    """Build logs directory"""

    manifest: Path
    """Build manifest file"""

    modules: Path
    """Project modules directory (`.ato/modules` from the project root)"""

    # TODO: remove, deprecated
    footprints: Path | None = None
    """Deprecated: Project footprints directory"""

    # TODO: remove, deprecated
    component_lib: Path | None = None
    """Deprecated: Component library directory for builds"""

    def __init__(self, **data: Any):
        data.setdefault("root", _project_dir or Path.cwd())
        data["src"] = Path(data.get("src", data["root"] / "elec" / "src"))
        data.setdefault("parts", data["src"] / "parts")
        data.setdefault("layout", data["root"] / "elec" / "layout")
        data["build"] = Path(data.get("build", data["root"] / "build"))
        data.setdefault("logs", data["build"] / "logs")
        data.setdefault("manifest", data["build"] / "manifest.json")
        data.setdefault("modules", data["root"] / ".ato" / "modules")

        super().__init__(**data)

    @model_validator(mode="after")
    def make_paths_absolute(model: "ProjectPaths") -> "ProjectPaths":
        """Make all paths absolute relative to the project root."""
        if not model.root.is_absolute():
            model.root = model.root.resolve().absolute()

        for field_name, field_value in model:
            if field_name != "root" and isinstance(field_value, Path):
                if not field_value.is_absolute():
                    setattr(model, field_name, model.root / field_value)
                setattr(
                    model, field_name, getattr(model, field_name).resolve().absolute()
                )
        return model

    @model_validator(mode="before")
    def check_deprecated_fields(cls, data: dict[str, Any]) -> dict[str, Any]:
        if "component_lib" in data and data["component_lib"] is not None:
            raise UserConfigurationError(
                "The 'component_lib' field in your ato.yaml is deprecated. "
                "Delete your component_lib and the entry in the ato.yaml. "
                "Use 'parts' instead."
            )
        if "footprints" in data and data["footprints"] is not None:
            raise UserConfigurationError(
                "The 'footprints' field in your ato.yaml is deprecated. "
                "If you are manually assigning hand-made footprints you "
                "probably want to make atomic parts instead. "
                "Please remove it."
            )
        return data

    def ensure(self) -> None:
        self.build.mkdir(parents=True, exist_ok=True)
        self.layout.mkdir(parents=True, exist_ok=True)


class BuildTargetPaths(BaseConfigModel):
    """
    Build-target specific paths
    """

    layout: Path
    """Build-target layout file"""

    output_base: Path
    """Extension-less filename for build artifacts"""

    netlist: Path
    """Build-target netlist file"""

    fp_lib_table: Path
    """Project footprint library table file"""

    kicad_project: Path
    """Build-target KiCAD project file"""

    def __init__(self, name: str, project_paths: ProjectPaths, **data: Any):
        if layout_data := data.get("layout"):
            data["layout"] = BuildTargetPaths.find_layout(Path(layout_data))
        else:
            data["layout"] = BuildTargetPaths.find_layout(
                project_paths.root / project_paths.layout / name
            )

        if output_base_data := data.get("output_base"):
            data["output_base"] = Path(output_base_data)
        else:
            data["output_base"] = project_paths.build / "builds" / name / name
            data["output_base"].parent.mkdir(parents=True, exist_ok=True)

        data.setdefault("netlist", data["output_base"] / f"{name}.net")
        data.setdefault("fp_lib_table", data["layout"].parent / "fp-lib-table")
        data.setdefault("kicad_project", data["layout"].with_suffix(".kicad_pro"))
        # We deliberately don't set a root for an individual build
        super().__init__(**data)

    @classmethod
    def find_layout(cls, layout_base: Path) -> Path:
        """Find the layout associated with a build."""

        if layout_base.with_suffix(".kicad_pcb").exists():
            return layout_base.with_suffix(".kicad_pcb").resolve().absolute()
        elif layout_base.is_dir():
            layout_candidates = list(
                filter(
                    BuildTargetPaths.match_user_layout, layout_base.glob("*.kicad_pcb")
                )
            )

            if len(layout_candidates) == 1:
                return layout_candidates[0].resolve().absolute()
            elif len(layout_candidates) > 1:
                raise UserException(
                    "Layout directories must contain only 1 layout,"
                    f" but {len(layout_candidates)} found in {layout_base}"
                )

        # default location, to create later
        return layout_base.resolve().absolute() / f"{layout_base.name}.kicad_pcb"

    def ensure_layout(self):
        """Return the layout associated with a build."""
        if not self.layout.exists():
            logger.info("Creating new layout at %s", self.layout)
            self.layout.parent.mkdir(parents=True, exist_ok=True)

            # delayed import to improve startup time
            from faebryk.libs.kicad.fileformats_latest import C_kicad_pcb_file

            C_kicad_pcb_file.skeleton(
                generator=DISTRIBUTION_NAME,
                generator_version=str(get_installed_atopile_version()),
            ).dumps(self.layout)
        elif not self.layout.is_file():
            raise UserResourceException(f"Layout is not a file: {self.layout}")

    @classmethod
    def match_user_layout(cls, path: Path) -> bool:
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


class BuildTargetConfig(BaseConfigModel, validate_assignment=True):
    _project_paths: ProjectPaths

    name: str
    address: str | None = Field(alias="entry")
    """
    Entry point or root node for the build-target.
    Everything that exists within this module will be built as part of this build-target
    """

    targets: list[str] = Field(default=["__default__"])  # TODO: validate
    """A list of targets' names to build after updating the layout"""

    exclude_targets: list[str] = Field(default=[])
    """
    A list of targets' names to exclude.

    Applied after `targets` are specified. This makes it useful to exclude
    targets that aren't relevant to a specific build - especially in CI,
    which typically builds **all** targets.
    """

    exclude_checks: list[str] = Field(default=[])
    """
    A list of checks to exclude.

    Use qualified name of check e.g
        - `PCB.requires_drc_check`
        - `I2C.requires_unique_addresses`
        - `requires_external_usage`
    """
    fail_on_drcs: bool = Field(default=False)
    dont_solve_equations: bool = Field(default=False)
    keep_designators: bool | None = Field(default=True)
    keep_picked_parts: bool | None = Field(default=None)
    keep_net_names: bool | None = Field(default=None)
    frozen: bool = Field(default=False)
    hide_designators: bool | None = Field(default=False)
    paths: BuildTargetPaths

    def __init__(self, **data: Any):
        super().__init__(**data)
        self._project_paths = data.get("_project_paths", ProjectPaths())

    @model_validator(mode="before")
    def init_paths(cls, data: dict) -> dict:
        match data.get("paths"):
            case dict() | None:
                data["paths"] = BuildTargetPaths(
                    name=data["name"],
                    project_paths=data["_project_paths"],
                    **data.get("paths", {}),
                )
            case BuildTargetPaths():
                pass
            case _:
                raise ValueError(f"Invalid build paths: {data.get('paths')}")
        return data

    def _set_frozen(self, frozen: bool):
        if self.keep_designators is None:
            self.keep_designators = frozen
        if self.keep_picked_parts is None:
            self.keep_picked_parts = frozen
        if self.keep_net_names is None:
            self.keep_net_names = frozen
        self.frozen = frozen

    @model_validator(mode="after")
    def validate_frozen_after(self) -> Self:
        if self.frozen:
            if not self.keep_designators:
                raise ValueError(
                    "`keep_designators` must be true when `frozen` is true"
                )
            if not self.keep_picked_parts:
                raise ValueError(
                    "`keep_picked_parts` must be true when `frozen` is true"
                )
            if not self.keep_net_names:
                raise ValueError("`keep_net_names` must be true when `frozen` is true")

        return self

    @property
    def build_type(self) -> BuildType:
        """
        Determine build type from the entry.

        **/*.ato:* -> BuildType.ATO
        **/*.py:* -> BuildType.PYTHON
        """
        suffix = self.entry_file_path.suffix

        match suffix:
            case ".ato":
                return BuildType.ATO
            case ".py":
                return BuildType.PYTHON
            case _:
                raise UserException(
                    f"Unknown entry suffix: {suffix} for {self.entry_section}"
                )

    @property
    def entry_file_path(self) -> Path:
        """An absolute path to the entry file."""
        address = AddrStr(self.address)
        return self._project_paths.root / address.file_path

    @property
    def entry_section(self) -> str:
        """The path to the entry module."""
        address = AddrStr(self.address)
        return address.entry_section

    def ensure(self):
        """Ensure this build config is ready to be used"""
        self.paths.ensure_layout()


class DependencySpec(BaseConfigModel):
    type: str
    # TODO ugly af, because we are mixing specs and config
    # should be config only, not in spec
    identifier: str

    @staticmethod
    def from_str(spec_str: str) -> "DependencySpec":
        if "://" not in spec_str:
            spec_str = "registry://" + spec_str
            # TODO default registry

        type_specifier, _ = spec_str.split("://", 1)

        # TODO dont use hardcoded strings
        if type_specifier.startswith("file"):
            return FileDependencySpec.from_str(spec_str)
        elif type_specifier.startswith("git"):
            return GitDependencySpec.from_str(spec_str)
        elif type_specifier.startswith("registry"):
            return RegistryDependencySpec.from_str(spec_str)
        else:
            raise UserConfigurationError(
                f"Invalid type specifier: {type_specifier} in {spec_str}"
            )

    def matches(self, other: "DependencySpec") -> bool:
        return self.identifier == other.identifier


class FileDependencySpec(DependencySpec):
    type: Literal["file"] = "file"
    path: Path
    identifier: str | None = None

    @field_serializer("path")
    def serialize_path(self, path: Path, _info: Any) -> str:
        return str(path)

    @staticmethod
    @override
    def from_str(spec_str: str) -> "FileDependencySpec":
        _, path = spec_str.split("://", 1)
        return FileDependencySpec(path=Path(path))


class GitDependencySpec(DependencySpec):
    type: Literal["git"] = "git"
    repo_url: str
    path_within_repo: Path | None = None
    ref: str | None = None
    identifier: str | None = None

    @staticmethod
    @override
    def from_str(spec_str: str) -> "GitDependencySpec":
        # Pattern to match git dependency spec format: git://<repo_url>.git[#<ref>][:<path_within_repo>]
        # - repo_url: everything after git:// until # or :
        # - ref: optional, everything between # and : (if present)
        # - path_within_repo: optional, everything after :
        pattern = (
            r"^git://"  # Protocol prefix
            r"(?P<repo_url>.+?\.git)"  # Repository URL (non-greedy match until .git)
            r"(?:#(?!:|$)"  # Optional ref part: '#' not followed by ':' or end
            r"(?P<ref>[^:]+)"  # Reference value (anything not a colon)
            r")?"  # End of optional ref group
            r"(?::(?P<path_within_repo>.*))?"  # Optional path part: ':' followed by
            # the path (colon not captured)
            r"$"  # End of string
        )
        match = re.match(pattern, spec_str)
        if not match:
            raise ValueError(f"Invalid git dependency spec: {spec_str}")

        repo_url = match.group("repo_url")
        ref = match.group("ref")
        path_within_repo = match.group("path_within_repo")
        if path_within_repo is not None:
            path_within_repo = Path(path_within_repo)

        return GitDependencySpec(
            repo_url=repo_url,
            ref=ref,
            path_within_repo=path_within_repo,
        )


class RegistryDependencySpec(DependencySpec):
    type: Literal["registry"] = "registry"
    release: str | None = None

    @property
    @override
    def identifier(self) -> str:
        return self.identifier

    @staticmethod
    @override
    def from_str(spec_str: str) -> "RegistryDependencySpec":
        _, identifier = spec_str.split("://", 1)
        if "@" in identifier:
            identifier, release = identifier.split("@", 1)
        else:
            release = None
        return RegistryDependencySpec(identifier=identifier, release=release)


_DependencySpec = Annotated[
    Union[FileDependencySpec, GitDependencySpec, RegistryDependencySpec],
    Field(discriminator="type"),
]


class ServicesConfig(BaseConfigModel):
    class Components(BaseConfigModel):
        url: str = Field(default="https://components.atopileapi.com")
        """Components URL"""

    class Packages(BaseConfigModel):
        url: str = Field(default="https://packages.atopileapi.com")
        """Packages URL"""

    @field_validator("components", mode="before")
    def validate_components(cls, value: Components | str) -> Components:
        # also accepts a string for backwards compatibility
        if isinstance(value, str):
            return cls.Components(url=value)
        return value

    components: Components = Field(default_factory=Components)
    packages: Packages = Field(default_factory=Packages)


# TODO: expand
RequirementSpec = Annotated[
    str,
    Field(
        pattern=r"^((>|>=|<|<=|\^)?[0-9]+\.[0-9]+\.[0-9]+|(>|>=)[0-9]+\.[0-9]+\.[0-9]+,(<|<=)[0-9]+\.[0-9]+\.[0-9]+)$"
    ),
]


class PackageConfig(BaseConfigModel):
    """Defines a package"""

    class Author(BaseConfigModel):
        name: str
        email: str

    identifier: str = Field(
        pattern=r"^(?P<owner>[a-zA-Z0-9](?:[a-zA-Z0-9]|(-[a-zA-Z0-9])){0,38})/(?P<name>[a-z][a-z0-9\-]+)(/(?P<subpackage>[a-z][a-z0-9\-]+))?$"
    )
    """
    The qualified name of the project, as it'd be installed from a package manager.
    eg. `pepper/my-project` or `pepper/my-project/sub-package`
    May contain numbers and lowercase ASCII letters only. The owner must match the
    GitHub organization from which the project is published (eg. `pepper`).
    Required for publishing.
    """

    version: str = Field(
        # semver subset only
        pattern=r"^(?P<major>[0-9]+)\.(?P<minor>[0-9]+)\.(?P<patch>[0-9]+)$",
        default="0.0.0",
    )
    """
    Project version, formatted according to the SemVer specification. See https://semver.org/.
    Contains MAJOR.MINOR.PATCH only, e.g. 1.0.1
    Required for publishing.
    """

    repository: HttpUrl | None = Field(default=None)
    """
    The repository URL of the project.
    Required for publishing.
    """

    authors: list[Author] | None = Field(default=None)
    """
    List of project authors.
    Required for publishing.
    """

    license: str | None = Field(default=None)
    """
    The project's license, as an SPDX 2.3 license expression.
    Required for publishing.
    """

    summary: str | None = Field(default=None)
    """
    A short blurb about the project.
    Required for publishing.
    """

    homepage: str | None = Field(default=None)
    """
    The project's homepage, if separate from the repository.
    """

    readme: str | None = Field(default="README.md")
    """
    Path to the project's README file, relative to this `ato.yaml`
    """


class ProjectConfig(BaseConfigModel):
    """Project-level config"""

    requires_atopile: RequirementSpec = Field(
        validation_alias=AliasChoices("requires-atopile", "requires_atopile"),
        serialization_alias="requires-atopile",
        default=f"^{clean_version(version.get_installed_atopile_version())}",
    )
    """
    Version required to build this project.
    """

    @model_validator(mode="before")
    def check_deprecated_fields(cls, values: dict[str, Any]) -> dict[str, Any]:
        if "ato-version" in values:
            raise UserConfigurationError(
                "The 'ato-version' field in your ato.yaml is deprecated. "
                "Use 'requires-atopile' instead."
            )
        return values

    package: PackageConfig | None = Field(default=None)
    """
    Defines a package
    """

    paths: ProjectPaths = Field(default_factory=ProjectPaths)
    dependencies: list[_DependencySpec] | None = Field(default=None)
    """
    Represents requirements on other projects.

    Typically, you shouldn't modify this directly.

    Instead, use the `ato add/remove <package>` commands.
    """

    entry: str | None = Field(default=None)
    builds: dict[str, BuildTargetConfig] = Field(default_factory=dict)
    """A map of all the build targets (/ "builds") in this project."""

    services: ServicesConfig = Field(default_factory=ServicesConfig)
    open_layout_on_build: bool = Field(default=False)
    """Automatically open pcbnew when applying netlist"""

    dangerously_skip_ssl_verification: bool = Field(default=True)  # FIXME: SSL
    """Skip SSL verification for all API requests."""

    @classmethod
    def from_path(cls, path: Path | None) -> "ProjectConfig | None":
        if path is None:
            return None

        config_file = path / PROJECT_CONFIG_FILENAME

        if not config_file.exists():
            return None

        try:
            file_contents = yaml.load(config_file)
        except FileNotFoundError as e:
            raise UserFileNotFoundError(f"Failed to load project config: {e}") from e
        except Exception as e:
            raise UserConfigurationError(f"Failed to load project config: {e}") from e

        file_contents.setdefault("paths", {}).setdefault("root", path)
        return _try_construct_config(
            ProjectConfig, identifier=config_file, **file_contents
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "ProjectConfig":
        try:
            file_contents = yaml.load(data)
        except Exception as e:
            raise UserConfigurationError(f"Failed to load project config: {e}") from e

        return _try_construct_config(ProjectConfig, identifier="", **file_contents)

    @field_validator("builds", mode="before")
    def init_builds(
        cls, value: dict[str, dict[str, Any] | BuildTargetConfig], info: ValidationInfo
    ) -> dict[str, Any]:
        for build_name, data in value.items():
            match data:
                case BuildTargetConfig():
                    data.name = build_name
                case dict():
                    data.setdefault("name", build_name)
                    data["_project_paths"] = info.data["paths"]
                case _:
                    raise ValueError(f"Invalid build data: {data}")
        return value

    @field_validator("dependencies", mode="before")
    def validate_dependencies(
        cls, value: list[dict[str, Any]] | None
    ) -> list[DependencySpec]:
        return [
            DependencySpec.from_str(dep)
            if isinstance(dep, str)
            else TypeAdapter(_DependencySpec).validate_python(dep)
            for dep in (value or [])
        ]

    @classmethod
    def skeleton(cls, entry: str, paths: ProjectPaths | None):
        """Creates a minimal ProjectConfig"""
        project_paths = paths or ProjectPaths()
        return _try_construct_config(
            ProjectConfig,
            paths=project_paths,
            entry=entry,
            builds={
                "default": BuildTargetConfig(
                    _project_paths=project_paths,
                    name="default",
                    entry="",
                    paths=BuildTargetPaths(name="default", project_paths=project_paths),
                )
            },
        )

    @staticmethod
    def set_or_add_dependency(config: "Config", dependency: DependencySpec):
        def _add_dependency(config_data, _):
            # validate_dependencies is the validator that loads the dependencies
            # from the config file. It ensures the format of the ato.yaml
            deps = ProjectConfig.validate_dependencies(
                config_data.get("dependencies", [])
            )  # type: ignore (class method)

            serialized = dependency.model_dump(mode="json")

            for i, dep in enumerate(deps):
                if dep.matches(dependency):
                    config_data["dependencies"][i] = serialized
                    break
            else:
                if config_data.get("dependencies") is None:
                    config_data["dependencies"] = []
                config_data["dependencies"].append(serialized)

            return config_data

        config.update_project_settings(_add_dependency, {})

    @staticmethod
    def remove_dependency(config: "Config", dependency: DependencySpec):
        def _remove_dependency(config_data, _):
            deps = ProjectConfig.validate_dependencies(
                config_data.get("dependencies", [])
            )  # type: ignore (class method)

            for i, dep in enumerate(deps):
                if dep.matches(dependency):
                    del config_data["dependencies"][i]
                    break

            return config_data

        config.update_project_settings(_remove_dependency, {})

    def get_relative_to_kicad_project(self, path: Path) -> Path:
        if not self.builds:
            if in_test():
                raise ValueError(
                    "No builds found. Did you forget: "
                    "`@pytest.mark.usefixtures('setup_project_config')`?"
                )
            raise UserConfigurationError("No builds found in project config")

        rel_paths = {
            name: path.relative_to(build.paths.kicad_project.parent, walk_up=True)
            for name, build in self.builds.items()
        }
        # TODO check this
        if len(set(rel_paths.values())) != 1:
            raise ValueError(
                "All builds must have the same common prefix path: "
                f"{indented_container(rel_paths)}"
            )
        return Path("${KIPRJMOD}") / first(rel_paths.values())


class ProjectSettings(ProjectConfig, BaseSettings):  # FIXME
    """
    Project-level config, loaded from
    - global config e.g. ~/.config/atopile/config.yaml
    - ato.yaml
    - environment variables e.g. ATO_SERVICES_COMPONENTS_API_URL
    """

    # TOOD: ignore but warn for extra fields
    model_config = BaseConfigModel.model_config | SettingsConfigDict(
        env_prefix=ENV_VAR_PREFIX,
        env_nested_delimiter="_",
        enable_decoding=False,
        use_attribute_docstrings=True,
        extra="forbid",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            ProjectConfigSettingsSource(settings_cls),
            GlobalConfigSettingsSource(settings_cls),
        )


_current_build_cfg: ContextVar[BuildTargetConfig | None] = ContextVar(
    "current_build_cfg", default=None
)


@contextmanager
def _build_context(config: "Config", build_name: str):
    cfg = config.project.builds[build_name]
    cfg.ensure()
    token = _current_build_cfg.set(cfg)
    try:
        yield
    finally:
        _current_build_cfg.reset(token)


class Config:
    _project: ProjectSettings | ProjectConfig | None
    _entry: str | None
    _selected_builds: list[str] | None
    _project_dir: Path | None
    interactive: bool

    def __init__(self) -> None:
        self._project_dir = _project_dir
        self._project = _try_construct_config(ProjectSettings)
        self._entry = None
        self._selected_builds = None
        # Check if we're in an interactive terminal session (cross-platform)
        try:
            self.interactive = sys.stdout.isatty() and sys.stdin.isatty()
        except (AttributeError, ValueError):
            # If we can't determine, default to True for better user experience
            self.interactive = True

    def __repr__(self) -> str:
        return self._project.__repr__()

    def __rich_repr__(self):
        yield "project", self._project
        yield "entry", self._entry
        yield "selected_builds", self._selected_builds
        yield "project_dir", self._project_dir

    def reload(self):
        self._project = _try_construct_config(ProjectSettings)

    @property
    def project(self) -> ProjectSettings | ProjectConfig:
        if self._project is None:
            # TODO: better message
            raise UserConfigurationError("No project config found")

        return self._project

    @project.setter
    def project(self, value: ProjectSettings | ProjectConfig) -> None:
        self._project = value

    @property
    def project_dir(self) -> Path:
        if not self._project_dir:
            raise ValueError("No project directory found")
        return self._project_dir

    @project_dir.setter
    def project_dir(self, value: os.PathLike) -> None:
        global _project_dir
        _project_dir = Path(value)

        if not (_project_dir / PROJECT_CONFIG_FILENAME).is_file():
            raise UserConfigNotFoundError(
                f"No `{PROJECT_CONFIG_FILENAME}` found in the specified directory"
            )

        self._project_dir = _project_dir
        self._project = _try_construct_config(ProjectSettings)

    def update_project_settings(
        self, transformer: Callable[[dict, dict], dict], new_data: dict
    ) -> None:
        """Apply an update to the project config file."""
        yaml = YAML(typ="rt")  # round-trip
        filename = self.project_dir / PROJECT_CONFIG_FILENAME
        temp_filename = filename.with_suffix(".yaml.tmp")

        try:
            with filename.open("r", encoding="utf-8") as file:
                yaml_data: dict = yaml.load(filename) or {}

            yaml_data = transformer(yaml_data, new_data)

            with temp_filename.open("w", encoding="utf-8") as file:
                yaml.dump(yaml_data, file)

            temp_filename.replace(filename)

            self._project = _try_construct_config(ProjectSettings)

        except Exception as e:
            try:
                temp_filename.unlink(missing_ok=True)
            except Exception:
                pass
            raise e

    @property
    def selected_builds(self) -> Iterable[str]:
        return self._selected_builds or self.project.builds.keys()

    @selected_builds.setter
    def selected_builds(self, value: list[str]) -> None:
        self._selected_builds = value

    @property
    def builds(self) -> Generator[_GeneratorContextManager[None], None, None]:
        """Return an iterable of BuildContext objects for each build."""
        return (_build_context(self, name) for name in self.selected_builds)

    def select_build(self, name: str) -> _GeneratorContextManager[None]:
        return _build_context(self, name)

    @property
    def build(self) -> BuildTargetConfig:
        if current := self._current_build:
            return current
        raise RuntimeError("No build config is currently active")

    @property
    def has_project(self) -> bool:
        try:
            project_dir = self.project_dir
        except ValueError:
            return False
        return (project_dir / PROJECT_CONFIG_FILENAME).exists()

    @property
    def _current_build(self) -> BuildTargetConfig | None:
        return _current_build_cfg.get()

    def _setup_standalone(self, entry: str | None, entry_arg_file_path: Path) -> None:
        if not entry:
            raise UserBadParameterError(
                "You must specify an entry to build with the --standalone option"
            )
        if not entry_arg_file_path.exists():
            raise UserBadParameterError(
                f"The file you have specified does not exist: {entry_arg_file_path}"
            )

        if not entry_arg_file_path.is_file():
            raise UserBadParameterError(
                "The path you're building with the --standalone"
                f" option must be a file {entry_arg_file_path}",
                markdown=False,
            )

        if config.has_project:
            raise UserBadParameterError(
                "Project config must not be present for standalone builds"
            )

        try:
            AddrStr(entry).entry_section
        except AddressError:
            raise UserBadParameterError(
                "You must specify what to build within a file to build with the"
                " --standalone option"
            )

        # don't trigger reload
        self._project_dir = entry_arg_file_path.parent
        root = self._project_dir
        standalone_dir = root / f"standalone_{entry_arg_file_path.stem}"
        self._project = ProjectConfig.skeleton(
            entry=entry,
            paths=ProjectPaths(
                root=root,
                src=root,
                layout=standalone_dir / "layout",
                build=standalone_dir / "build",
                # TODO definitely need option to override this
                parts=standalone_dir / "parts",
            ),
        )

    def _check_entry_arg_file_path(
        self, entry: str | None, entry_arg_file_path: Path
    ) -> AddrStr | None:
        entry_addr_override = None

        if entry:
            if entry_arg_file_path.is_file():
                if entry_section := address.get_entry_section(AddrStr(entry)):
                    entry_addr_override = address.from_parts(
                        str(entry_arg_file_path.absolute()),
                        entry_section,
                    )
                else:
                    raise UserBadParameterError(
                        "If an entry of a file is specified, you must specify"
                        " the node within it you want to build.",
                        title="Bad 'entry' parameter",
                    )

            elif entry_arg_file_path.is_dir():
                pass

            elif not entry_arg_file_path.exists():
                raise UserBadParameterError(
                    "The entry you have specified does not exist.",
                    title="Bad 'entry' parameter",
                )
            else:
                raise ValueError(
                    f"Unexpected entry path type {entry_arg_file_path}"
                    " - this should never happen!"
                )

        return entry_addr_override

    def _get_entry_arg_file_path(
        self, entry: str | None, working_dir: Path | None
    ) -> tuple[AddrStr | None, Path]:
        # basic the entry address if provided, otherwise leave it as None

        if entry is None:
            entry_arg_file_path = working_dir or Path.cwd()
        else:
            entry = AddrStr(entry)

            if address.get_file(entry) is None:
                raise UserBadParameterError(
                    f"Invalid entry address {entry} - entry must specify a file.",
                    title="Bad 'entry' parameter",
                )

            entry_arg_file_path = (
                Path(address.get_file(entry)).expanduser().resolve().absolute()
            )

        return entry, entry_arg_file_path

    def apply_options(
        self,
        entry: str | None,
        standalone: bool = False,
        include_targets: Iterable[str] = (),
        exclude_targets: Iterable[str] = (),
        selected_builds: Iterable[str] = (),
        frozen: bool | None = None,
        working_dir: Path | None = None,
        **kwargs: Any,
    ) -> None:
        if working_dir:
            working_dir = Path(working_dir).expanduser().resolve().absolute()

        entry, entry_arg_file_path = self._get_entry_arg_file_path(entry, working_dir)

        if standalone:
            self._setup_standalone(entry, entry_arg_file_path)
        else:
            if config_file_path := find_project_config_file(entry_arg_file_path):
                self.project_dir = config_file_path.parent
            elif entry is None:
                raise UserNoProjectException(search_path=entry_arg_file_path)

            else:
                raise UserBadParameterError(
                    f"Specified entry path is not a file or directory: "
                    f"{entry_arg_file_path}",
                    markdown=False,
                )

        self.project.entry = entry

        logger.info("Using project %s", self.project_dir)

        # if we set an entry-point, we now need to deal with that
        entry_addr_override = self._check_entry_arg_file_path(
            entry, entry_arg_file_path
        )

        if self.project.paths is not None:
            self.project.paths.ensure()

        if selected_builds:
            self.selected_builds = list(selected_builds)

        for build_name in self.selected_builds:
            try:
                build_cfg = self.project.builds[build_name]
            except KeyError:
                raise UserBadParameterError(
                    f"Build `{build_name}` not found in project config.\n\nAvailable"
                    " builds:\n" + md_list(self.project.builds.keys())
                )

            if entry_addr_override is not None:
                build_cfg.address = entry_addr_override

            if include_targets:
                build_cfg.targets = list(include_targets)

            if exclude_targets:
                build_cfg.exclude_targets = list(exclude_targets)

            # Attach CLI options passed via kwargs
            for key, value in kwargs.items():
                if value is not None:
                    setattr(build_cfg, key, value)

            if frozen is not None:
                try:
                    build_cfg._set_frozen(frozen)
                except ValidationError as e:
                    # TODO: better error message
                    raise UserBadParameterError(
                        f"Invalid value for `frozen`: {e}",
                        title="Bad 'frozen' parameter",
                    )

    def should_open_layout_on_build(self) -> bool:
        """Returns whether atopile should open the layout after building"""
        # If the project config has an explicit setting, use that
        if self.project is not None and self.project.open_layout_on_build is not None:
            return self.project.open_layout_on_build

        # Otherwise, default to opening the layout if we're only building a
        # single target and we're running interactively
        return (
            (self.project is None or self.project.open_layout_on_build is None)
            and len(list(self.selected_builds)) == 1
            and self.interactive
        )


_project_dir: Path | None = None
config: Config = Config()
