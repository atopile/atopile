import fnmatch
import logging
import os
import platform
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import (
    AliasChoices,
    BaseModel,
    Field,
    ValidationError,
)
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)
from ruamel.yaml import YAML

from atopile import version
from atopile.address import AddrStr
from atopile.errors import UserException
from atopile.version import DISTRIBUTION_NAME, get_installed_atopile_version

logger = logging.getLogger(__name__)
yaml = YAML()


APPLICATION_NAME = "atopile"
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


class BuildType(Enum):
    ATO = "ato"
    PYTHON = "python"


class UserConfigurationError(UserException):
    """An error in the config file."""


class GlobalConfigSettingsSource(YamlConfigSettingsSource):
    def __init__(
        self,
        settings_cls: type[BaseSettings],
    ):
        yaml_file = GlobalConfigSettingsSource._find_config_file()
        super().__init__(settings_cls, yaml_file, yaml_file_encoding="utf-8")

    @classmethod
    def _find_config_file(cls) -> Path | None:
        """
        Find the global config file in the user's home directory.
        """
        match platform.system():
            case "Darwin" | "Linux":
                config_dir = (
                    Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
                    / APPLICATION_NAME
                )
            case "Windows":
                # TODO: @windows
                raise UserException(f"Unsupported platform: {platform.system()}")
            case _:
                raise UserException(f"Unsupported platform: {platform.system()}")

        config_file = config_dir / GLOBAL_CONFIG_FILENAME
        return config_file if config_file.exists() else None


class ProjectConfigSettingsSource(YamlConfigSettingsSource):
    def __init__(self, settings_cls: type[BaseSettings]):
        project_dir = (
            _project_dir or ProjectConfigSettingsSource._find_project() or Path.cwd()
        )
        yaml_file = project_dir / PROJECT_CONFIG_FILENAME

        self.yaml_file_encoding = "utf-8"
        self.yaml_data = self._read_files(yaml_file)

        super(YamlConfigSettingsSource, self).__init__(
            settings_cls, {"project": self.yaml_data if self.yaml_data else None}
        )

    @classmethod
    def _find_project(cls, dir: Path = Path.cwd()) -> Path | None:
        """
        Find a project config file in the specified directory or any parent directories.
        """
        path = dir
        while not (path / PROJECT_CONFIG_FILENAME).exists():
            path = path.parent
            if path == Path("/"):
                return None
        return path.resolve().absolute()


class ProjectPaths(BaseModel):
    root: Path = Field(default=Path.cwd())
    src: Path | None = Field(default=None)
    layout: Path | None = Field(default=None)
    footprints: Path | None = Field(default=None)
    manifest: Path | None = Field(default=None)
    build: Path | None = Field(default=None)
    component_lib: Path | None = Field(default=None)

    def apply_layout(self, location: Path) -> None:
        """Apply default project layout if not already specified."""
        if self.root is None:
            self.root = location

        if self.src is None:
            self.src = self.root / "elec" / "src"

        if self.layout is None:
            self.layout = self.root / "elec" / "layout"

        if self.footprints is None:
            self.footprints = self.root / "elec" / "footprints"

        if self.build is None:
            self.build = self.root / "build"

        if self.manifest is None:
            self.manifest = self.build / "manifest.json"

        if self.component_lib is None:
            self.component_lib = self.build / "kicad" / "libs"

        self.root.mkdir(parents=True, exist_ok=True)
        self.build.mkdir(parents=True, exist_ok=True)
        self.layout.mkdir(parents=True, exist_ok=True)
        self.footprints.mkdir(parents=True, exist_ok=True)
        self.src.mkdir(parents=True, exist_ok=True)


class BuildPaths(BaseModel):
    layout: Path | None = Field(default=None)
    output_base: Path | None = Field(default=None)
    netlist: Path | None = Field(default=None)
    fp_lib_table: Path | None = Field(default=None)
    kicad_project: Path | None = Field(default=None)

    def apply_layout(self, name: str, project_paths: ProjectPaths) -> None:
        assert project_paths.layout is not None
        assert project_paths.build is not None

        if self.layout is None:
            self.layout = BuildPaths.find_layout(project_paths.layout / name)

        if self.output_base is None:
            self.output_base = project_paths.build / name

        if self.netlist is None:
            self.netlist = self.output_base / f"{name}.net"

        if self.fp_lib_table is None:
            self.fp_lib_table = self.layout.parent / "fp-lib-table"

        if self.kicad_project is None:
            self.kicad_project = self.layout.with_suffix(".kicad_pro")

    @classmethod
    def find_layout(cls, layout_base: Path) -> Path:
        """Return the layout associated with a build."""

        if layout_base.with_suffix(".kicad_pcb").exists():
            return layout_base.with_suffix(".kicad_pcb").resolve().absolute()

        elif layout_base.is_dir():
            layout_candidates = list(
                filter(BuildPaths.match_user_layout, layout_base.glob("*.kicad_pcb"))
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


class BuildEntry(BaseModel):
    file_path: Path | None = Field(default=None)
    entry_section: str | None = Field(default=None)


class BuildConfig(BaseModel):
    address: str = Field(alias="entry")
    targets: list[str] = Field(default=["__default__"])  # TODO: validate
    exclude_targets: list[str] = Field(default=[])
    fail_on_drcs: bool = Field(default=False)
    dont_solve_equations: bool = Field(default=False)
    keep_picked_parts: bool = Field(default=False)
    paths: BuildPaths = Field(default_factory=BuildPaths)
    keep_net_names: bool = Field(default=False)
    frozen: bool = Field(default=False)

    @property
    def build_type(self) -> BuildType:
        """
        Determine build type from the entry.

        **/*.ato:* -> BuildType.ATO
        **/*.py:* -> BuildType.PYTHON
        """
        suffix = self.file_path.suffix

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
    def file_path(self) -> Path:
        address = AddrStr(self.address)
        return address.file_path

    @property
    def entry_section(self) -> str:
        address = AddrStr(self.address)
        return address.entry_section


class Dependency(BaseModel):
    name: str
    version_spec: str | None = None
    link_broken: bool = False
    path: Path | None = None

    project_config: "ProjectConfig | None" = Field(
        default_factory=lambda data: Dependency._load_project_config(data["path"])
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

    @classmethod
    def _load_project_config(cls, project_path: Path | None) -> "ProjectConfig | None":
        if project_path is None:
            return None

        config_file = project_path / PROJECT_CONFIG_FILENAME

        if not config_file.exists():
            return None

        file_contents = yaml.load(config_file)
        return _try_construct_config(
            ProjectConfig,
            identifier=config_file,
            location=project_path,
            **file_contents,
        )


class ProjectConfig(BaseModel):
    """
    Project-level configuration, loaded from an `ato.yaml` file.
    """

    ato_version: str = Field(
        validation_alias="ato-version", serialization_alias="ato-version"
    )
    paths: ProjectPaths = Field(default_factory=ProjectPaths)
    builds: dict[str, BuildConfig] | None = Field(default=None)
    dependencies: list[Dependency | str] | None = Field(default=None)
    entry: str | None = Field(default=None)

    def model_post_init(self, __context: Any) -> None:
        self.dependencies = [
            Dependency.from_str(dep) if isinstance(dep, str) else dep
            for dep in self.dependencies or []
        ]

    def apply_layout(self, location: Path) -> None:
        """Determine project paths from the project directory and configured values."""
        self.paths.apply_layout(location)
        for build in self.builds:
            self.builds[build].paths.apply_layout(build, self.paths)


class ServicesConfig(BaseModel):
    components_api_url: str = Field(
        default="https://components.atopileapi.com/legacy/jlc",
        validation_alias=AliasChoices("components_api_url", "components"),
    )


class Settings(BaseSettings):
    services: ServicesConfig = Field(default_factory=ServicesConfig)
    entry: str | None = Field(default=None)
    project_dir: Path | None
    project: ProjectConfig | None = Field(default=None)

    model_config = SettingsConfigDict(env_prefix="ATO_")

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

    def model_post_init(self, __context: Any) -> None:
        if self.project_dir is not None and self.project is not None:
            self.project.apply_layout(self.project_dir)


class Config:
    _settings: Settings

    def __init__(self) -> None:
        self._settings = _try_construct_config(Settings, project_dir=_project_dir)

    def __rich_repr__(self):
        return self._settings

    @property
    def project(self) -> ProjectConfig:
        if self._settings.project is None:
            # TODO: better message
            raise UserConfigurationError("No project config found")

        return self._settings.project

    @project.setter
    def project(self, value: ProjectConfig) -> None:
        self._settings.project = value

    @property
    def project_dir(self) -> Path:
        assert self._settings.project_dir is not None
        return self._settings.project_dir

    @project_dir.setter
    def project_dir(self, value: Path) -> None:
        global _project_dir
        _project_dir = value
        self._settings = _try_construct_config(Settings, project_dir=value)


_project_dir: Path | None = None
config: Config = Config()
