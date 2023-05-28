import enum
import logging
from pathlib import Path
from typing import Dict, List

import yaml

from atopile.model.accessors import ModelVertexView
from atopile.model.accessors import get_all_as
from atopile.model.model import VertexType
from atopile.project.config import ResolverConfig
from atopile.project.project import Project

from atopile.resolvers.resolver import Resolver

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

class DesignatorConfig(ResolverConfig):
    def __init__(self, config_data: dict, project: Project) -> None:
        super().__init__("designators", config_data, project)

    @property
    def designators_file_template(self) -> str:
        return self._config_data.get("designators-file", "{build-config}-designators.yaml")

class ComponentView(ModelVertexView):
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

class DesignatorResolver(Resolver):
    @property
    def resolver_config(self) -> DesignatorConfig:
        generic_config = self.project.config.resolvers.get("designators")
        if generic_config is None:
            return DesignatorConfig({}, self.project)
        return DesignatorConfig(generic_config._config_data, self.project)

    def run(self):
        assert isinstance(self.resolver_config, DesignatorConfig)

        designators_file = self.project.root / self.resolver_config.designators_file_template.format(**{"build-config": self.build_config.name})
        if designators_file.exists():
            with designators_file.open() as f:
                designator_data: Dict[str, str] = yaml.safe_load(f)
        else:
            designator_data = {}

        root_node = ModelVertexView.from_path(self.model, self.build_config.root_node)
        generic_descendants = root_node.get_descendants(VertexType.component)
        components: List[ComponentView] = [ComponentView(v.model, v.index) for v in generic_descendants]

        # apply existing designators to components
        for component in components:
            if component.designator is None:
                if component.path in designator_data:
                    component.designator = designator_data[component.path]

        # find all the components still missing designators
        components_to_designate: List[ComponentView] = []
        consumed_designators: List[str] = []

        for component in components:
            if component.designator is None:
                components_to_designate.append(component)
                continue

            if component.designator in consumed_designators:
                components_to_designate.append(component)
                continue

            if not component.designator.startswith(component.designator_prefix):
                components_to_designate.append(component)
                log.warning(f"{component.path} has a designator-prefix mis-match. Regenerating designator.")
                continue

            # if none of the above, then we're cool with the existing designator. Let's roll.
            consumed_designators.append(component.designator)

        # generate designators and back-assign everything to the model
        for component in components_to_designate:
            MAX_DESIGNATOR = 10000
            for i in range(1, 10000):
                designator = component.designator_prefix + str(i)
                if designator not in consumed_designators:
                    consumed_designators.append(designator)
                    component.designator = designator
                    break
            else:
                raise ValueError(f"Exceeded the limit of {MAX_DESIGNATOR} on a board! Eeek!")

        # finally, save all designators for next time
        designator_dict = {c.path: c.designator for c in components}
        with designators_file.open("w") as f:
            yaml.safe_dump(designator_dict, f)
