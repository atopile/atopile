import fnmatch
import itertools
import logging
import os
from abc import ABC, abstractmethod
from contextlib import _GeneratorContextManager, contextmanager
from contextvars import ContextVar
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Generator, Iterable, Self

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    field_serializer,
    field_validator,
    model_validator,
)
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
    UserNotImplementedError,
)
from atopile.version import DISTRIBUTION_NAME, get_installed_atopile_version
from faebryk.libs.exceptions import iter_through_errors

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
        """Find the global config file in the user's home directory."""

        # note deliberate use of ~/.config on all platforms
        # (rather than e.g. platformdirs)
        config_dir = (
            Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
            / APPLICATION_NAME
        )
        config_file = config_dir / GLOBAL_CONFIG_FILENAME
        return config_file if config_file.exists() else None

    def get_data(self) -> dict[str, Any]:
        return self.yaml_data if self.yaml_data else {}


class ProjectConfigSettingsSource(ConfigFileSettingsSource):
    @classmethod
    def find_config_file(cls) -> Path | None:
        """
        Find a project config file in the specified directory or any parent directories.
        """
        if _project_dir:
            return _project_dir / PROJECT_CONFIG_FILENAME

        path = Path.cwd()
        while not (path / PROJECT_CONFIG_FILENAME).exists():
            path = path.parent
            if path == Path("/"):
                return None

        return path.resolve().absolute() / PROJECT_CONFIG_FILENAME

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

    layout: Path
    """Project layout directory"""

    footprints: Path
    """Project footprints directory"""

    build: Path
    """Build artifact output directory"""

    manifest: Path
    """Build manifest file"""

    component_lib: Path
    """Component library directory for builds"""

    modules: Path
    """Project modules directory (`.ato/modules` from the project root)"""

    def __init__(self, **data: Any):
        data.setdefault("root", _project_dir or Path.cwd())
        data.setdefault("src", data["root"] / "elec" / "src")
        data.setdefault("layout", data["root"] / "elec" / "layout")
        data.setdefault("footprints", data["root"] / "elec" / "footprints")
        data.setdefault("build", data["root"] / "build")
        data.setdefault("manifest", data["build"] / "manifest.json")
        data.setdefault("component_lib", data["build"] / "kicad" / "libs")
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

    def ensure(self) -> None:
        self.build.mkdir(parents=True, exist_ok=True)
        self.layout.mkdir(parents=True, exist_ok=True)

    def get_footprint_lib(self, lib_name: str) -> Path:
        return self.component_lib / "footprints" / f"{lib_name}.pretty"


class BuildTargetPaths(BaseConfigModel):
    """
    Build-target specific paths
    """

    root: Path
    """Build-target root directory"""

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
        data.setdefault(
            "layout",
            BuildTargetPaths.find_layout(
                project_paths.root / project_paths.layout / name
            ),
        )
        data.setdefault("output_base", project_paths.build / name)
        data.setdefault("netlist", data["output_base"] / f"{name}.net")
        data.setdefault("fp_lib_table", data["layout"].parent / "fp-lib-table")
        data.setdefault("kicad_project", data["layout"].with_suffix(".kicad_pro"))
        data.setdefault("root", data["layout"].parent)
        super().__init__(**data)

    @classmethod
    def find_layout(cls, layout_base: Path) -> Path:
        """Return the layout associated with a build."""

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

            else:
                raise UserException(
                    "Layout directories must contain only 1 layout,"
                    f" but {len(layout_candidates)} found in {layout_base}"
                )

        else:
            layout_path = layout_base.with_suffix(".kicad_pcb")

            logger.warning("Creating new layout at %s", layout_path)
            layout_path.parent.mkdir(parents=True, exist_ok=True)

            # delayed import to improve startup time
            from faebryk.libs.kicad.fileformats import C_kicad_pcb_file

            C_kicad_pcb_file.skeleton(
                generator=DISTRIBUTION_NAME,
                generator_version=str(get_installed_atopile_version()),
            ).dumps(layout_path)

            return layout_path

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


class BuildTargetConfig(BaseConfigModel):
    _project_paths: ProjectPaths

    name: str
    address: str | None = Field(alias="entry")
    targets: list[str] = Field(default=["__default__"])  # TODO: validate
    exclude_targets: list[str] = Field(default=[])
    fail_on_drcs: bool = Field(default=False)
    dont_solve_equations: bool = Field(default=False)
    keep_picked_parts: bool = Field(default=False)
    keep_net_names: bool = Field(default=False)
    frozen: bool = Field(default=False)
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
        address = AddrStr(self.address)
        return self._project_paths.root / address.file_path

    @property
    def entry_section(self) -> str:
        address = AddrStr(self.address)
        return address.entry_section


class Dependency(BaseConfigModel):
    name: str
    version_spec: str | None = None
    link_broken: bool = False
    path: Path | None = None

    project_config: "ProjectConfig | None" = Field(
        default_factory=lambda data: ProjectConfig.from_path(data["path"]), exclude=True
    )

    @classmethod
    def from_str(cls, spec_str: str) -> "Dependency":
        for splitter in version.OPERATORS + ("@",):
            if splitter in spec_str:
                try:
                    name, version_spec = spec_str.rsplit(splitter, 1)
                    name = name.strip()
                    version_spec = splitter + version_spec
                except TypeError as ex:
                    raise UserConfigurationError(
                        f"Invalid dependency spec: {spec_str}"
                    ) from ex
                return cls(name=name, version_spec=version_spec)
        return cls(name=spec_str)

    @field_serializer("path")
    def serialize_path(self, path: Path | None, _info: Any) -> str | None:
        return str(path) if path else None


class ServicesConfig(BaseConfigModel):
    class Components(BaseConfigModel):
        url: str = Field(default="https://components.atopileapi.com")
        """Components URL"""

    class Packages(BaseConfigModel):
        url: str = Field(default="https://get-package-atsuhzfd5a-uc.a.run.app")
        """Packages URL"""

    @field_validator("components", mode="before")
    def validate_components(cls, value: Components | str) -> Components:
        # also accepts a string for backwards compatibility
        if isinstance(value, str):
            return cls.Components(url=value)
        return value

    components: Components = Field(default_factory=Components)
    packages: Packages = Field(default_factory=Packages)


class ProjectConfig(BaseConfigModel):
    """Project-level config"""

    ato_version: str = Field(
        validation_alias=AliasChoices("ato-version", "ato_version"),
        serialization_alias="ato-version",
        default=f"^{version.get_installed_atopile_version()}",
    )
    paths: ProjectPaths = Field(default_factory=ProjectPaths)
    dependencies: list[Dependency] | None = Field(default=None)
    entry: str | None = Field(default=None)
    builds: dict[str, BuildTargetConfig] = Field(default_factory=dict)
    services: ServicesConfig = Field(default_factory=ServicesConfig)
    pcbnew_auto: bool = Field(default=False)
    """Automatically open pcbnew when applying netlist"""

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

        file_contents["paths"].setdefault("root", path)
        return _try_construct_config(
            ProjectConfig, identifier=config_file, **file_contents
        )

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
    def add_dependencies(cls, value: list[dict[str, Any]] | None) -> list[Dependency]:
        return [
            Dependency.from_str(dep) if isinstance(dep, str) else Dependency(**dep)
            for dep in (value or [])
        ]

    @model_validator(mode="after")
    def validate_compiler_versions(self) -> Self:
        """
        Check that the compiler version is compatible with the version
        used to build the project.
        """
        dependency_cfgs = (
            (dep.project_config for dep in self.dependencies)
            if self.dependencies is not None
            else ()
        )

        for cltr, cfg in iter_through_errors(itertools.chain([self], dependency_cfgs)):
            if cfg is None:
                continue

            with cltr():
                semver_str = cfg.ato_version
                # FIXME: this is a hack to the moment to get around us breaking
                # the versioning scheme in the ato.yaml files
                for operator in version.OPERATORS:
                    semver_str = semver_str.replace(operator, "")

                built_with_version = version.parse(semver_str)

                if not version.match_compiler_compatability(built_with_version):
                    raise version.VersionMismatchError(
                        f"{cfg.paths.root} ({cfg.ato_version}) can't be"
                        " built with this version of atopile "
                        f"({version.get_installed_atopile_version()})."
                    )
        return self

    @classmethod
    def skeleton(cls, entry: str, paths: ProjectPaths | None):
        """Creates a minimal ProjectConfig"""
        project_paths = paths or ProjectPaths()
        return _try_construct_config(
            ProjectConfig,
            ato_version=f"^{version.get_installed_atopile_version()}",
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

    def model_post_init(self, __context: Any) -> None:
        if self.paths is not None:
            self.paths.ensure()


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

    def __init__(self) -> None:
        self._project_dir = _project_dir
        self._project = _try_construct_config(ProjectSettings)
        self._entry = None
        self._selected_builds = None

    def __repr__(self) -> str:
        return self._project.__repr__()

    def __rich_repr__(self):
        yield "project", self._project
        yield "entry", self._entry
        yield "selected_builds", self._selected_builds
        yield "project_dir", self._project_dir

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
    def project_dir(self, value: Path) -> None:
        global _project_dir
        _project_dir = value
        self._project_dir = value
        self._project = _try_construct_config(ProjectSettings)

    def update_project_config(
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
        return self._selected_builds or self.project.builds.keys() or ["default"]

    @selected_builds.setter
    def selected_builds(self, value: list[str]) -> None:
        self._selected_builds = value

    @property
    def builds(self) -> Generator[_GeneratorContextManager[None], None, None]:
        """Return an iterable of BuildContext objects for each build."""
        return (_build_context(self, name) for name in self.selected_builds)

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
        self._project_dir = entry_arg_file_path.parent or Path.cwd()
        self._project = ProjectConfig.skeleton(
            entry=entry,
            paths=ProjectPaths(
                root=self._project_dir,
                src=self._project_dir,
                layout=self._project_dir / "standalone",
                footprints=self._project_dir / "standalone",
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
        self, entry: str | None
    ) -> tuple[AddrStr | None, Path]:
        # basic the entry address if provided, otherwise leave it as None

        if entry is None:
            entry_arg_file_path = Path.cwd()
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
        entry_arg_file_path: Path = Path.cwd(),
        standalone: bool = False,
        option: Iterable[str] = (),
        target: Iterable[str] = (),
        selected_builds: Iterable[str] = (),
    ) -> None:
        entry, entry_arg_file_path = self._get_entry_arg_file_path(entry)

        if standalone:
            self._setup_standalone(entry, entry_arg_file_path)
        else:
            if entry_arg_file_path.is_dir():
                self.project_dir = entry_arg_file_path
            elif entry_arg_file_path.is_file():
                self.project_dir = entry_arg_file_path.parent
            else:
                raise UserBadParameterError(
                    f"Specified entry path is not a file or directory: "
                    f"{entry_arg_file_path}",
                    markdown=False,
                )

        self.project.entry = entry

        logger.info("Using project %s", self.project_dir)

        # add custom config overrides
        if option:
            raise UserNotImplementedError(
                "Custom config overrides have been removed in a refactor. "
                "It's planned to re-add them in a future release. "
                "If this is a blocker for you, please raise an issue. "
                "In the meantime, you can use the `ato.yaml` file to set these options."
            )

        # if we set an entry-point, we now need to deal with that
        entry_addr_override = self._check_entry_arg_file_path(
            entry, entry_arg_file_path
        )

        if selected_builds:
            self.selected_builds = list(selected_builds)

        for build_name in self.selected_builds:
            if build_name not in self.project.builds:
                raise UserBadParameterError(
                    f"Build `{build_name}` not found in project config"
                )

            if entry_addr_override is not None:
                self.project.builds[build_name].address = entry_addr_override
            if target:
                self.project.builds[build_name].targets = list(target)


_project_dir: Path | None = None
config: Config = Config()
