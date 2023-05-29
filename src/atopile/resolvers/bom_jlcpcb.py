import logging
from typing import Dict, List

import yaml

from atopile.model.accessors import ModelVertexView
from atopile.model.model import VertexType
from atopile.project.config import ResolverConfig
from atopile.project.project import Project

from atopile.resolvers.resolver import Resolver

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

class BomResolverConfig(ResolverConfig):
    def __init__(self, config_data: dict, project: Project) -> None:
        super().__init__("bom-jlcpcb", config_data, project)

    @property
    def bom_file_template(self) -> str:
        return self._config_data.get("bom-file", "{build-config}-bom-jlcpcb.yaml")

class BomJlcPcbResolver(Resolver):
    name = "bom-jlcpcb"

    @property
    def config(self) -> BomResolverConfig:
        generic_config = self.project.config.resolvers.get("designators")
        if generic_config is None:
            return BomResolverConfig({}, self.project)
        return BomResolverConfig(generic_config._config_data, self.project)

    def run(self):
        assert isinstance(self.config, BomResolverConfig)

        bomjlcpcb_file = self.project.root / self.config.bom_file_template.format(**{"build-config": self.build_config.name})
        if bomjlcpcb_file.exists():
            with bomjlcpcb_file.open() as f:
                bomjlcpcb_data: Dict[str, str] = yaml.safe_load(f)
        else:
            bomjlcpcb_data = {}

        root_node = ModelVertexView.from_path(self.model, self.build_config.root_node)
        components = root_node.get_descendants(VertexType.component)

        # check everything has a designator and footprint assigned
        missing_designators = False
        missing_footprints = False
        for component in components:
            if component.data.get("designator") is None:
                log.error(f"{component.path} is missing a designator.")
                missing_designators = True
            if component.data.get("footprint") is None:
                log.error(f"{component.path} is missing a footprint.")
                missing_footprints = True

        # raise and exception if there's a problem
        if missing_designators:
            log.error("Components are missing designators. Please assign designators to all components, consider the designators resolver, before running this resolver.")
        if missing_footprints:
            log.error("Components are missing footprints. Please assign footprints to all components, consider the footprints resolver, before running this resolver.")

        if missing_designators or missing_footprints:
            raise ValueError("Data missing for target bom-jlcpcb")

        # bom-jlcpcb has nested keys of: class-path, footprint, value
        # there's an additional key for "ungrouped components"
        # group up components by the bom-jlcpcb structure
        component_groups: Dict[str, Dict[str, Dict[str, List[ModelVertexView]]]] = {}
        ungrouped_components: List[ModelVertexView] = []

        # apply LCSC part numbers from exsiting bom-jlcpcb data
        for component in components:
            # if you're working with something that's not a component instance, I'm not quite sure what's going on, but I can't help...
            if component.instance_of:
                component_groups.setdefault(component.instance_of.path, {}).setdefault(component.data.get("footprint"), {}).setdefault(component.data.get("value"), []).append(component)
            else:
                ungrouped_components.append(component)

        # apply LCSC part numbers from existing bom-jlcpcb data
        for component_path, lcsc in bomjlcpcb_data.get("ungrouped", {}).items():
            ModelVertexView.from_path(self.model, component_path).data["lcsc"] = lcsc
        for class_path, footprints in component_groups.items():
            for footprint, values in footprints.items():
                for value, group_components in values.items():
                    bomjlcpcb_data = bomjlcpcb_data.get(class_path, {}).get(footprint, {}).get(value)
                    if bomjlcpcb_data is not None:
                        for component in group_components:
                            component.data["lcsc"] = bomjlcpcb_data["lcsc"]

        # find component groups with more than one unique lcsc part number
        # if there are multiple unique lcsc part numbers, then we dump all the components into the ungrouped_components list
        # if there's only one unique lcsc part number, then we assign that lcsc part number to all the components
        for class_path, footprints in component_groups.items():
            for footprint, values in footprints.items():
                for value, group_components in values.items():
                    lcsc_part_numbers = set()
                    for component in group_components:
                        if component.data.get("lcsc"):
                            lcsc_part_numbers.add(component.data.get("lcsc"))
                    if len(lcsc_part_numbers) == 1:
                        lcsc_part_number = list(lcsc_part_numbers)[0]
                        for component in group_components:
                            component.data["lcsc"] = lcsc_part_number
                    elif len(lcsc_part_numbers) > 1:
                        ungrouped_components.extend(group_components)
                        component_groups[class_path][footprint][value].clear()

        # finally, save all designators for next time
        designator_dict = {c.path: c.designator for c in components}
        with bomjlcpcb_file.open("w") as f:
            yaml.safe_dump(designator_dict, f)
