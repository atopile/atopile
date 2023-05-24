import logging
from pathlib import Path
from typing import List, Any

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class Config:
    def __init__(self, config_data: dict, project) -> None:
        self.config_data = config_data
        self.project = project

    def _return_subconfig(self, key: str, return_type) -> "BaseSubConfig":
        return return_type(self.config_data.get(key, {}), self.project, self)

    @property
    def paths(self) -> "Paths":
        return self._return_subconfig("paths", Paths)

    @property
    def build(self) -> "Build":
        return self._return_subconfig("build", Build)

class BaseSubConfig:
    def __init__(self, config_data: dict, project, parent: "BaseSubConfig") -> None:
        self._config_data = config_data
        self.project = project
        self.parent = parent

class Paths(BaseSubConfig):
    @property
    def build_dir(self) -> Path:
        build_dir = self._config_data.get("build-dir")
        if build_dir is None:
            return (self.project.root / "build").resolve().absolute()

        build_dir = Path(build_dir)
        if not build_dir.is_absolute():
            build_dir = self.project.root / build_dir

        return build_dir.resolve().absolute()

class Build(BaseSubConfig):
    @property
    def configs(self) -> List["BuildConfig"]:
        configs = self._config_data.get("configs", [])
        if not isinstance(configs, list):
            log.error("Build configs must be a list")
            return []
        return [BuildConfig(c, self.project, self) for c in configs]

    @property
    def default_config(self) -> "BuildConfig":
        return DefaultBuildConfig(self._config_data.get("default", {}), self.project, self)

class BuildConfig(BaseSubConfig):
    def _get_or_default(self, key: str) -> Any:
        if key not in self._config_data:
            if self.name == "default":
                log.warning(f"No value for {key} in default config")
                return None
            return self.parent.default_config._get_or_default(key)
        return self._config_data[key]

    @property
    def name(self) -> str:
        return self._get_or_default("name")

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
        paths = self.config_data.get("data-layers", [])
        return [self.project.root / p for p in paths]

class DefaultBuildConfig(BuildConfig):
    @property
    def name(self) -> str:
        return "default"
