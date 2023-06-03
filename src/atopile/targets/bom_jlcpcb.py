import logging
from typing import Any, Dict, List, Optional, Tuple, Union, Set
from collections import OrderedDict
from pathlib import Path

import ruamel.yaml
from attrs import define, field

from atopile.model.accessors import ModelVertexView
from atopile.model.model import Model, VertexType
from atopile.project.config import BaseConfig
from atopile.project.project import Project
from atopile.targets.targets import Target, TargetCheckResult, TargetMuster
from atopile.utils import update_dict

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


@define
class ImplicitComponent:
    src_index: int
    footprint: str
    value: str
    instance_of: str
    mfg_part: str

    def to_dict(self) -> OrderedDict:
        result = OrderedDict()
        result["footprint"] = self.footprint
        result["value"] = self.value
        result["instance-of"] = self.instance_of
        result["mfg-part"] = self.mfg_part
        return result

    @staticmethod
    def from_dict(data: dict) -> "ImplicitComponent":
        return ImplicitComponent(
            footprint=data["footprint"],
            value=data["value"],
            instance_of=data["instance-of"],
            mfg_part=data["mfg-part"]
        )

    @staticmethod
    def from_component(src_index: int, component: ModelVertexView) -> "ImplicitComponent":
        return ImplicitComponent(
            src_index=src_index,
            footprint=component.data.get("footprint"),
            value=component.data.get("value"),
            instance_of=component.instance_of.path,
            mfg_part=None
        )

@define
class ExplicitComponent:
    src_index: int
    path: str
    mfg_part: str

    def to_dict(self) -> OrderedDict:
        result = OrderedDict()
        result["path"] = self.path
        result["mfg-part"] = self.mfg_part
        return result

    @staticmethod
    def from_dict(src_index: int, data: dict) -> "ExplicitComponent":
        return ExplicitComponent(
            src_index=src_index,
            path=data["path"],
            mfg_part=data["mfg-part"]
        )

class ComponentNotFoundError(Exception):
        """The component you are looking for does not exist in the map."""

@define
class MfgPartMap:
    # a component is assumed to be the same the same part if all:
    # - it has the same footprint
    # - it has the same value
    # - it's an instance of the same class
    # - it's not explicitly stated otherwise

    implicit: List[ImplicitComponent]
    explicit: List[ExplicitComponent]

    implicit_map: Dict[Tuple[str, str, str], ImplicitComponent] = field(init=False)
    explicit_map: Dict[str, str] = field(init=False)

    def __attrs_post_init__(self) -> None:
        self.implicit_map = {}
        for component_group in self.implicit:
            key = (component_group.footprint, component_group.value, component_group.instance_of)
            self.implicit_map[key] = component_group
        self.explicit_map = {c.path: c for c in self.explicit}

    @staticmethod
    def from_dict(data: dict) -> "MfgPartMap":
        return MfgPartMap(
            implicit=[ImplicitComponent.from_dict(i, v) for i, v in enumerate(data.get("implicit", []))],
            explicit=[ExplicitComponent.from_dict(i, v) for i, v in enumerate(data.get("explicit", []))]
        )

    def to_dict(self) -> OrderedDict:
        result = OrderedDict()
        result["implicit"] = [v.to_dict() for v in self.implicit]
        result["explicit"] = [v.to_dict() for v in self.explicit]
        return result

    def find_component(self, component: ModelVertexView, raise_unfound = True) -> Union[ExplicitComponent, ImplicitComponent]:
        if component.path in self.explicit:
            return self.explicit[component.path]

        key = (component.data.get("footprint"), component.data.get("value"), component.instance_of.path)
        if key in self.implicit_map:
            return self.implicit_map[key]

        if component.path in self.explicit_map:
            return self.explicit_map[component.path]

        if raise_unfound:
            raise ComponentNotFoundError

    def add_component(self, component: ModelVertexView) -> None:
        pass


class ComponentSelectionConfig(BaseConfig):
    @property
    def component_selection_file_template(self) -> str:
        return self._config_data.get("component-selection-file", "{build-config}-components.yaml")


class MfgPartMapTarget(Target):
    name = "component-selection"

    def __init__(self, muster: TargetMuster) -> None:
        self._mfg_map: Optional[MfgPartMap] = None
        self._idea_mfg_map: Optional[MfgPartMap] = None
        self._check_result: Optional[TargetCheckResult] = None
        super().__init__(muster)

    @property
    def config(self) -> ComponentSelectionConfig:
        return ComponentSelectionConfig.from_config(super().config)

    def get_mfg_map_file(self) -> Path:
        return self.project.root / self.config.component_selection_file_template.format(**{"build-config": self.build_config.name})

    def build(self) -> None:
        log.info(f"Nothing to build {self.name} target.")

    def resolve(self, *args, clean=None, **kwargs) -> None:
        if self.check() == TargetCheckResult.COMPLETE:
            log.info(f"Nothing to resolve for {self.name} target.")
            return

        mfg_map_file = self.get_mfg_map_file()
        if mfg_map_file.exists():
            with mfg_map_file.open() as f:
                existing_file_data = ruamel.yaml.safe_load(f)
        else:
            # TODO: make this a ruamel.yaml dict so we can add comments?
            existing_file_data = OrderedDict()

        missing_components = 


    def check(self) -> TargetCheckResult:
        # cache previous checks
        if self._check_result is not None:
            return self._check_result

        mfg_map = self.generate()

        # get all components in the build
        root_node = ModelVertexView.from_path(self.model, self.build_config.root_node)
        generic_descendants = root_node.get_descendants(VertexType.component)

        # make sure all components are in the mfg part map
        self._idea_mfg_map = MfgPartMap([], [])
        for component in generic_descendants:
            try:
                component_map = mfg_map.find_component(component)
            except ComponentNotFoundError:
                log.error(f"Component {component.path} isn't in the mfg part map.")
                self._check_result = TargetCheckResult.UNSOLVABLE
                component_map = ImplicitComponent.from_component(component)
            self._idea_mfg_map.implicit.append(component_map)

        # if we've already failed, return early
        if self._check_result == TargetCheckResult.UNSOLVABLE:
            log.error(f"Component selection is unsolvable, because there are parts missing from {self.get_mfg_map_file()}. Run `ato resolve {self.name}` to fix this.")
            return self._check_result

        if set(self._idea_mfg_map.implicit) | set(self._idea_mfg_map.explicit) != set(mfg_map.implicit) | set(mfg_map.explicit):
            log.warning(f"There are unused components in {self.get_mfg_map_file()}. Run `ato resolve --clean {self.name}` to fix this.")
            self._check_result = TargetCheckResult.UNTIDY
        else:
            self._check_result = TargetCheckResult.COMPLETE

        return self._check_result

    @property
    def check_has_been_run(self) -> bool:
        raise NotImplementedError

    def generate(self) -> MfgPartMap:
        # cache previous builds
        if self._mfg_map is not None:
            return self._mfg_map

        # get existing data
        component_selection_file = self.get_mfg_map_file()
        if component_selection_file.exists():
            with component_selection_file.open() as f:
                file_data: Dict[str, str] = ruamel.yaml.safe_load(f)
        else:
            file_data = {}

        existing_mfg_part_map = MfgPartMap.from_dict(file_data)
        return existing_mfg_part_map


class BomJlcpcbTarget(Target):
    def __init__(self, muster: TargetMuster) -> None:
        self._bom: Optional[MfgPartMap] = None
        super().__init__(muster)

    def generate(self) -> None:
        output_file = self.project.config.paths.build / self.build_config.root_file.with_suffix(".ref-map.yaml").name
        root_node = ModelVertexView.from_path(self.model, self.build_config.root_node)
        generic_descendants = root_node.get_descendants(VertexType.component)

        csv_data = []
        csv_data.append(("Comment", "Designator", "Footprint", "LCSC"))
        for component_group in component_groups.values():
            component_sample = component_group[0]
            # figure out what to put in the "value" column
            # start with a "value"
            if component_sample.data.get("value"):
                comment = component_sample.data.get("value")
            # otherwise, try to use the thing it's an instance of
            elif component_sample.instance_of:
                comment = component_sample.instance_of.ref
            else:
                log.warning(f"No clear comment for {component_sample.path}.")
                comment = ""

            # designators
            designators = [c.data.get("designator") for c in component_group]
            designator = "\"" + ",".join(designators) + "\""

            # footprints
            # already grouped by component footprint
            footprint = component_sample.data.get("footprint")

            # figure out what to put in the "LCSC" column
            # TODO: strict component selection? eg. force outputtting only completely specified components?
            if component_sample.data.get("lcsc"):
                lcsc = component_sample.data.get("lcsc")
            else:
                log.warning(f"No LCSC part number specified for {component_sample.path}.")
                lcsc = ""

            csv_data.append((comment, designator, footprint, lcsc))

        with output_file.open("w") as f:
            # TODO: pretty-print? pad our columns?
            for row in csv_data:
                f.write(",".join(row) + "\n")

    required_resolvers = []


class BomResolverConfig(BaseConfig):
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
