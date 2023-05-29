from typing import List

from atopile.model.model import Model
from atopile.project.config import BuildConfig
from atopile.project.project import Project


class ResolverNotFoundError(Exception):
    """
    The resovler you are looking for does not exist.
    """

def find_resolver(resolver_name: str) -> "Resolver":
    """Find a resolver by name."""
    #TODO: fix this entire function
    if resolver_name == "designators":
        import atopile.resolvers.designators
        return atopile.resolvers.designators.DesignatorResolver
    if resolver_name == "bom-jlcpcb":
        import atopile.resolvers.bom_jlcpcb
        return atopile.resolvers.bom_jlcpcb.BomJlcPcbResolver
    raise ResolverNotFoundError(resolver_name)

class MissingReolversError(Exception):
    """
    Required resolvers haven't yet been run on the model. Consider changing the execution order to make sure they run before this resolver.
    """

class Resolver:
    # The resolvers this resolver depends on
    @property
    def depends_on(self) -> List[str]:
        return []

    @property
    def name(self) -> str:
        raise NotImplementedError

    def __init__(self, project: Project, model: Model, build_config: BuildConfig) -> None:
        self.project = project
        self.model = model
        self.build_config = build_config

    def run(self) -> None:
        raise NotImplementedError
