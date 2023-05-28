from atopile.model.model import Model
from atopile.project.config import BuildConfig, ResolverConfig
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
    raise ResolverNotFoundError(resolver_name)

class Resolver:
    def __init__(self, project: Project, model: Model, build_config: BuildConfig) -> None:
        self.project = project
        self.model = model
        self.build_config = build_config

    def run(self) -> None:
        raise NotImplementedError
