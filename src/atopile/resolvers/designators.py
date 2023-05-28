import enum
import logging
from pathlib import Path
from typing import Dict, List

import yaml

from atopile.model.accessors import ComponentVertexView as BaseComponentView
from atopile.model.accessors import get_all_as
from atopile.model.model import VertexType
from atopile.project.config import ResolverConfig
from atopile.project.project import Project

from .resolver import Resolver

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

class DesignatorConfig(ResolverConfig):
    def __init__(self, config_data: dict, project: Project) -> None:
        super().__init__("designators", config_data, project)

    @property
    def designators_file(self) -> Path:
        return self.project.root / self._config_data.get("designators-file", "designators.yaml")

class ComponentView(BaseComponentView):
    @property
    def designator(self) -> str:
        return self.data.get("designator")

    @designator.setter
    def designator(self, designator_str: str) -> None:
        self.data["designator"] = designator_str

    @property
    def designator_prefix(self) -> str:
        return self.data.get("designator_prefix")

    @designator_prefix.setter
    def designator_prefix(self, designator_str: str) -> None:
        self.data["designator_prefix"] = designator_str

class DesignatorSource(enum.Enum):
    # TODO: I don't think we really need this anymore
    model = "model"
    designators_file = "designators_file"
    generated = "generated"

class DesignatorResolver(Resolver):
    @property
    def resolver_config(self) -> DesignatorConfig:
        generic_config = self.project.config.resolvers.get("designators")
        if generic_config is None:
            return DesignatorConfig({}, self.project)
        return DesignatorConfig(generic_config._config_data, self.project)

    def run(self):
        assert isinstance(self.resolver_config, DesignatorConfig)

        if self.resolver_config.designators_file.exists():
            with self.resolver_config.designators_file.open() as f:
                designator_data: Dict[str, str] = yaml.safe_load(f)
        else:
            designator_data = {}

        components: List[ComponentView] = get_all_as(self.model, VertexType.component, ComponentView)

        designator_sources: Dict[str, DesignatorSource] = {}
        designator_values: Dict[str, str] = {}
        for component in components:
            if component.designator is not None:
                if component.designator_prefix:
                    if not component.designator.startswith(component.designator_prefix):
                        log.warning(f"Designator {component.designator} assigned for {component.path} does not match assigned prefix {component.designator_prefix}")

                if component.designator in designator_values.values():
                    log.warning(f"Designator {component.designator} assigned for {component.path} is not unique. Auto-assigning a new one.")
                    continue

                designator_sources[component.path] = DesignatorSource.model
                designator_values[component.path] = component.designator
                continue

            if component.path in designator_data:
                if component.designator_prefix and designator_data[component.path].startswith(component.designator_prefix):
                    if designator_data[component.path] in designator_values.values():
                        log.warning(f"The existing designator for {component.path} is not unique. Auto-generating a new one")
                        continue
                    designator_sources[component.path] = DesignatorSource.designators_file
                    designator_values[component.path] = component.designator

        # create a designator from scratch
        paths_with_designators = set(designator_values.keys())
        for component in components:
            if component.path in paths_with_designators:
                continue

            designator_prefix = component.designator_prefix or "U"
            # TODO: this sucks, why the hell are we looping here?
            # well, we're looping because we want to find a unique designator
            # without doing string parsing (removing the letters)
            for i in range (1, 10000):
                designator_value = designator_prefix + str(i)
                if designator_value in designator_values.values():
                    continue
                break

            designator_values[component.path] = designator_value
            designator_sources[component.path] = DesignatorSource.generated

        # finally, back-assign everything to the model
        for component in components:
            component.designator = designator_values[component.path]

        with self.resolver_config.designators_file.open("w") as f:
            yaml.safe_dump(designator_values, f)
