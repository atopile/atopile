from pathlib import Path
from typing import List


class Config:
    def __init__(self, config_data: dict, project) -> None:
        self.config_data = config_data
        self.project = project

    @property
    def paths(self) -> "Paths":
        return Paths(self.config_data.get("paths", {}), self.project)

    @property
    def data_layers(self) -> List[str]:
        return self.config_data.get("data_layers", [])

class BaseSubConfig:
    def __init__(self, config_data: dict, project) -> None:
        self._config_data = config_data
        self.project = project

class Paths(BaseSubConfig):
    @property
    def build_dir(self) -> Path:
        build_dir = self._config_data.get("build_dir")
        if build_dir is None:
            return (self.project.root / "build").resolve().absolute()

        build_dir = Path(build_dir)
        if not build_dir.is_absolute():
            build_dir = self.project.root / build_dir

        return build_dir.resolve().absolute()

