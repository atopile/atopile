import logging
from pathlib import Path
from typing import Any, List, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    # See: https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
    from atopile.project.project import Project

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class Config:
    def __init__(self, config_data: dict, project: "Project") -> None:
        self._config_data = config_data
        self.project = project

    def _return_subconfig(self, key: str, return_type) -> "BaseSubConfig":
        return return_type(self._config_data.get(key, {}), self.project)

    @property
    def paths(self) -> "Paths":
        return self._return_subconfig("paths", Paths)

    @property
    def builds(self) -> "Builds":
        return self._return_subconfig("builds", Builds)

    @property
    def targets(self) -> List["TargetConfig"]:
        configs = self._config_data.get("configs", {})
        if not isinstance(configs, dict):
            log.error("Target configs must be a dict")
            return {}
        return {k: TargetConfig(k, data, self.project) for k, data in configs.items()}

    @property
    def resolvers(self) -> Dict[str, "ResolverConfig"]:
        configs = self._config_data.get("configs", {})
        if not isinstance(configs, dict):
            log.error("Resolver configs must be a dict")
            return {}
        return {k: ResolverConfig(k, data, self.project) for k, data in configs.items()}

class BaseSubConfig:
    def __init__(self, config_data: dict, project: "Project") -> None:
        self._config_data = config_data
        self.project = project

    @property
    def default(self) -> "BaseSubConfig":
        raise NotImplementedError

class Paths(BaseSubConfig):
    @property
    def build(self) -> Path:
        build_dir = self._config_data.get("build")
        if build_dir is None:
            return (self.project.root / "build").resolve().absolute()

        build_dir = Path(build_dir)
        if not build_dir.is_absolute():
            build_dir = self.project.root / build_dir

        return build_dir.resolve().absolute()

class Builds(BaseSubConfig):
    @property
    def configs(self) -> Dict[str, "BuildConfig"]:
        configs = self._config_data.get("configs", {})
        if not isinstance(configs, dict):
            log.error("Build configs must be a map")
            return {}
        return {k: BuildConfig(k, d, self.project) for k, d in configs.items()}

    @property
    def default(self) -> "BuildConfig":
        return DefaultBuildConfig(self._config_data.get("default", {}), self.project)

class BuildConfig(BaseSubConfig):
    def __init__(self, name: str, config_data: dict, project: "Project") -> None:
        self._name = name
        super().__init__(config_data, project)

    @property
    def name(self) -> str:
        return self._name

    @property
    def default(self) -> "BuildConfig":
        return self.project.config.builds.default

    def _get_or_default(self, key: str) -> Any:
        if key not in self._config_data:
            if self.name == "default":
                log.error(f"No value for {key} in default config")
                return None
            return self.default._get_or_default(key)
        return self._config_data[key]

    @property
    def root_file(self) -> Path:
        return self.project.root / self._get_or_default("root-file")

    @property
    def root_node(self) -> str:
        return self._get_or_default("root-node")

    @property
    def targets(self) -> List[str]:
        return self._get_or_default("targets") or ["netlist", "ref-map"]

    @property
    def data_layers(self) -> List[Path]:
        paths = self._config_data.get("data-layers", [])
        return [self.project.root / p for p in paths]

class DefaultBuildConfig(BuildConfig):
    def __init__(self, config_data: dict, project: "Project") -> None:
        super().__init__("default", config_data, project)

class CustomBuildConfig(BuildConfig):
    def __init__(self, root_file, root_node, targets, data_layers) -> None:
        self.name = "custom"
        self.root_file = root_file
        self.root_node = root_node
        self.targets = targets
        self.data_layers = data_layers

    @staticmethod
    def from_build_config(build_config: BuildConfig) -> "CustomBuildConfig":
        return CustomBuildConfig(
            root_file=build_config.root_file,
            root_node=build_config.root_node,
            targets=build_config.targets,
            data_layers=build_config.data_layers,
        )

class TargetConfig(BaseSubConfig):
    def __init__(self, name: str, config_data: dict, project: "Project") -> None:
        self._name = name
        super().__init__(config_data, project)

    @property
    def name(self) -> str:
        return self._name

class ResolverConfig(BaseSubConfig):
    def __init__(self, name: str, config_data: dict, project: "Project") -> None:
        self._name = name
        super().__init__(config_data, project)

    @property
    def name(self) -> str:
        return self._name
