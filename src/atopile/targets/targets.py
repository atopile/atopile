from typing import List

from atopile.model.model import Model
from atopile.project.config import BuildConfig, TargetConfig
from atopile.project.project import Project


class TargetNotFoundError(Exception):
    """
    The target you are looking for does not exist.
    """

def find_target(target_name: str) -> "Target":
    """Find a target by name."""
    #TODO: fix this entire function
    if target_name == "netlist-kicad6":
        import atopile.targets.netlist.kicad6
        return atopile.targets.netlist.kicad6.Kicad6NetlistTarget
    if target_name == "ref-map":
        import atopile.targets.ref_map
        return atopile.targets.ref_map.RefMapTarget
    raise TargetNotFoundError(target_name)

class Target:
    def __init__(self, project: Project, model: Model, build_config: BuildConfig) -> None:
        self.project = project
        self.model = model
        self.build_config = build_config

    @property
    def required_resolvers(self) -> List[str]:
        return []

    @property
    def name(self) -> str:
        raise NotImplementedError

    @property
    def target_config(self) -> TargetConfig:
        return self.build_config.targets[self.name]

    def generate(self) -> None:
        raise NotImplementedError
