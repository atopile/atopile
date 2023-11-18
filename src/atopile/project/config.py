import logging
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List

if TYPE_CHECKING:
    # See: https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
    from atopile.project.project import Project

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class BaseConfig:
    def __init__(self, config_data: dict, project: "Project", name=None) -> None:
        self._config_data = config_data
        self.project = project
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @classmethod
    def from_config(cls, config: "BaseConfig") -> "BaseConfig":
        return cls(config._config_data, config.project, config.name)

    def _return_subconfig(self, key: str, return_type) -> "BaseConfig":
        return return_type(self._config_data.get(key, {}), self.project, name=key)

    def _return_list_of(self, list_key: str, return_type) -> list:
        return [
            return_type(d, self.project) for d in self._config_data.get(list_key, [])
        ]

    def _return_dict_of(self, dict_key: str, return_type) -> dict:
        return {
            k: return_type(v, self.project, name=k)
            for k, v in self._config_data.get(dict_key, {}).items()
        }


class Config(BaseConfig):
    @property
    def paths(self) -> "Paths":
        return self._return_subconfig("paths", Paths)

    @property
    def atopile_version(self) -> str:
        return self._config_data.get("ato-version")

    @property
    def builds(self) -> Dict[str, "BuildConfig"]:
        build_dict = self._return_dict_of("builds", BuildConfig)
        if "default" not in build_dict:
            build_dict["default"] = BuildConfig("default", {}, self.project)
        return build_dict

    @property
    def targets(self) -> Dict[str, "BaseConfig"]:
        return self._return_dict_of("targets", BaseConfig)


class Paths(BaseConfig):
    @property
    def build(self) -> Path:
        build_dir = self._config_data.get("build")
        if build_dir is None:
            return (self.project.root / "build").resolve().absolute()

        build_dir = Path(build_dir)
        if not build_dir.is_absolute():
            build_dir = self.project.root / build_dir

        return build_dir.resolve().absolute()

    @property
    def lib_path(self) -> Path:
        lib_path: str = self._config_data.get("lib-path", "../lib/lib.pretty")
        return (self.project.root / lib_path).resolve().absolute()

class BuildConfig(BaseConfig):
    @property
    def default(self) -> "BuildConfig":
        return self.project.config.builds["default"]

    @property
    def root_file(self) -> Path:
        if "root-file" not in self._config_data:
            return
        return self.project.root / self._config_data["root-file"]

    @property
    def root_node(self) -> str:
        return self._config_data.get("root-node", self._config_data.get("root-file"))

    @property
    def targets(self) -> List[str]:
        return self._config_data.get("targets") or [
            "designators",
            "netlist-kicad6",
            "bom-jlcpcb",
            "kicad-lib-paths"
        ]

    @property
    def build_path(self) -> Path:
        return self.project.config.paths.build / self.name


class CustomBuildConfig:
    def __init__(
        self, name: str, project: "Project", root_file, root_node, targets, config_data
    ) -> None:
        self._name = name
        self.project = project
        self.root_file = root_file
        self.root_node = root_node
        self.targets = targets
        self._config_data = config_data


    @property
    def name(self) -> str:
        return self._name

    @staticmethod
    def from_build_config(build_config: BuildConfig) -> "CustomBuildConfig":
        return CustomBuildConfig(
            name=build_config.name,
            project=build_config.project,
            root_file=build_config.root_file,
            root_node=build_config.root_node,
            targets=build_config.targets,
            config_data=build_config._config_data,
        )

    @property
    def build_path(self) -> Path:
        return self.project.config.paths.build / self.name
