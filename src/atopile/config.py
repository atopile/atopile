import logging
import os
import platform
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, Field, ValidationError, computed_field
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from ruamel.yaml import YAML

from atopile.address import AddrStr
import atopile.version
from atopile.errors import UserException, UserFileNotFoundError

logger = logging.getLogger(__name__)
yaml = YAML()


APPLICATION_NAME = "atopile"
PROJECT_CONFIG_FILENAME = "ato.yaml"
GLOBAL_CONFIG_FILENAME = "config.yaml"

DEFAULT_PROJECT_SRC_PATH = Path("elec/src")
DEFAULT_PROJECT_LAYOUT_PATH = Path("elec/layout")
DEFAULT_PROJECT_FOOTPRINTS_PATH = Path("elec/footprints/footprints")
DEFAULT_PROJECT_MANIFEST_PATH = Path("build/manifest.json")


def _path_or_fallback(path: Path, fallback: Path = Path(".")) -> Path:
    return path if path.exists() else fallback


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


def _find_project(dir: Path = Path.cwd()) -> Path | None:
    """
    Find a project config file in the specified directory or any parent directories.
    """
    path = dir
    while not (path / PROJECT_CONFIG_FILENAME).exists():
        path = path.parent
        if path == Path("/"):
            return None
    return (path / PROJECT_CONFIG_FILENAME).resolve().absolute()


class BuildType(Enum):
    ATO = "ato"
    PYTHON = "python"


class UserConfigurationError(UserException):
    """An error in the config file."""


class YamlConfigSettingsSource(PydanticBaseSettingsSource, ABC):
    context: Literal["project", "global"]

    @abstractmethod
    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        pass

    def prepare_field_value(
        self, field_name: str, field: FieldInfo, value: Any, value_is_complex: bool
    ) -> Any:
        return value

    def __call__(self) -> dict[str, Any]:
        d: dict[str, Any] = {}

        for field_name, field in self.settings_cls.model_fields.items():
            field_value, field_key, value_is_complex = self.get_field_value(
                field, field_name
            )
            field_value = self.prepare_field_value(
                field_name, field, field_value, value_is_complex
            )
            if field_value is not None:
                d[field_key] = field_value

        return d


class GlobalConfigSettingsSource(YamlConfigSettingsSource):
    def _find_config_file(self) -> Path | None:
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

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        config_file = self._find_config_file()
        if not config_file:
            return None, field_name, False

        file_contents = yaml.load(config_file)
        field_value = file_contents.get(field_name)

        return field_value, field_name, False


class ProjectConfigSettingsSource(YamlConfigSettingsSource):
    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        config_file = self.current_state.get("project_path")
        match field_name:
            case "project":
                if not config_file:
                    return None, field_name, False

                # config file contains only the project key
                field_value = yaml.load(config_file)
                field_value.setdefault("location", config_file.parent)
                return field_value, field_name, False
            case _:
                return None, field_name, False


class ProjectPaths(BaseModel):
    # TODO: relative to project_path, not CWD
    src: Path = Field(
        default_factory=lambda: _path_or_fallback(DEFAULT_PROJECT_SRC_PATH)
    )
    layout: Path = Field(
        default_factory=lambda: _path_or_fallback(DEFAULT_PROJECT_LAYOUT_PATH)
    )
    footprints: Path = Field(
        default_factory=lambda: _path_or_fallback(DEFAULT_PROJECT_FOOTPRINTS_PATH)
    )
    manifest: Path = Field(
        default_factory=lambda: _path_or_fallback(DEFAULT_PROJECT_MANIFEST_PATH)
    )


class BuildPaths(BaseModel):
    # TODO: fix these
    name: str = Field(default="build")  # FIXME
    output_base: Path = Field(default=Path("build"))
    build: Path = Field(default_factory=lambda data: data["output_base"] / "build")
    layout: Path = Field(default_factory=lambda data: data["output_base"] / "layout")
    manifest: Path = Field(
        default_factory=lambda data: data["output_base"] / "manifest.json"
    )
    fp_lib_table: Path = Field(
        default_factory=lambda data: data["output_base"] / "fp_lib_table.json"
    )
    root: Path = Field(default=Path("."))
    component_lib: Path = Field(default=Path("."))

    def ensure_paths(self) -> None:
        self.build.mkdir(parents=True, exist_ok=True)
        self.layout.mkdir(parents=True, exist_ok=True)


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

    @computed_field
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
                raise UserException(f"Unknown entry suffix: {suffix} for {self.entry}")

    @computed_field
    @property
    def file_path(self) -> Path:
        address = AddrStr(self.address)
        return address.file_path

    @computed_field
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

    # TODO
    # @classmethod
    # def from_str(cls, spec_str: str) -> "Dependency":
    #     for splitter in atopile.version.OPERATORS + ("@",):
    #         if splitter in spec_str:
    #             try:
    #                 name, version_spec = spec_str.rsplit(splitter, 1)
    #                 name = name.strip()
    #                 version_spec = splitter + version_spec
    #             except TypeError as ex:
    #                 raise UserConfigurationError(
    #                     f"Invalid dependency spec: {spec_str}"
    #                 ) from ex
    #             return cls(name=name, version_spec=version_spec)
    #     return cls(name=spec_str)

    @classmethod
    def _load_project_config(cls, project_path: Path) -> "ProjectConfig | None":
        if not project_path.exists():
            return None

        config_file = project_path / PROJECT_CONFIG_FILENAME
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

    location: Path
    ato_version: str = Field(
        validation_alias="ato-version", serialization_alias="ato-version"
    )
    paths: ProjectPaths = Field(default=ProjectPaths())
    builds: dict[str, BuildConfig]
    dependencies: list[Dependency] | None = Field(default=None)


class ServicesConfig(BaseModel):
    components_api_url: str = Field(
        default="https://components.atopileapi.com/legacy/jlc",
        validation_alias=AliasChoices("components_api_url", "components"),
    )


class Config(BaseSettings):
    services: ServicesConfig = Field(default=ServicesConfig())
    entry: str | None = Field(default=None)
    project_path: Path | None
    project: ProjectConfig | None = Field(
        default=None
    )  # TODO: can we make this not None?

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

    def get_project_config(
        self, entry_arg_file_path: Path | None = None
    ) -> ProjectConfig:
        #     def get_project_config(entry_arg_file_path: Path) -> ProjectConfig:
        # try:
        #     project_config = get_project_config_from_path(str(entry_arg_file_path))
        # except FileNotFoundError as ex:
        #     # FIXME: this raises an exception when the entry is not in a project
        #     raise errors.UserBadParameterError(
        #         f"Could not find project from path {str(entry_arg_file_path)}. "
        #         "Is this file path within a project?"
        #     ) from ex

        # return project_config
        # TODO: handle entry arg file path
        # entry_arg_file_path = get_entry_arg_file_path(self.entry)

        if self.project is None:
            raise UserFileNotFoundError(
                f"Could not find {PROJECT_CONFIG_FILENAME} in "
                f"{Path.cwd()} or any parents",
                markdown=False,
            )
        return self.project


def load_config() -> Config:
    return _try_construct_config(Config, project_path=_find_project())


config = load_config()
