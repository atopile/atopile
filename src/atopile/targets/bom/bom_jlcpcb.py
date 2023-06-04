import logging
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Union

import ruamel.yaml
from attrs import frozen

from atopile.model.model import Model, VertexType
from atopile.model.accessors import ModelVertexView
from atopile.project.config import BaseConfig
from atopile.targets.targets import Target, TargetCheckResult, TargetMuster

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

yaml = ruamel.yaml.YAML()
yaml.preserve_quotes = True

@frozen
class ImplicitPartSpec:
    instance_of: str
    footprint: Optional[str]
    value: Optional[str]

    def matches_component(self, component: ModelVertexView) -> bool:
        if self.instance_of != component.instance_of.path:
            return False
        if self.footprint and self.footprint != component.data.get("footprint"):
            return False
        if self.value and self.value != component.data.get("value"):
            return False
        return True

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ImplicitPartSpec":
        return ImplicitPartSpec(data["instance_of"], data.get("footprint"), data.get("value"))

    @staticmethod
    def from_list(data: List[Dict[str, Any]]) -> Iterable["ImplicitPartSpec"]:
        return [ImplicitPartSpec(d["instance_of"], d.get("footprint"), d.get("value")) for d in data]

    @staticmethod
    def from_component(component: ModelVertexView) -> "ImplicitPartSpec":
        return ImplicitPartSpec(component.instance_of.path, component.data.get("footprint"), component.data.get("value"))

    def to_dict(self) -> Dict[str, Any]:
        result = {"instance_of": self.instance_of, "footprint": self.footprint, "value": self.value}
        return {k: v for k, v in result.items() if v is not None}

def part_spec_groups(model: Model, root_node_path: str) -> Tuple[Iterable[ModelVertexView], Dict[ImplicitPartSpec, Iterable[ModelVertexView]], Dict[str, ImplicitPartSpec]]:
    root_node = ModelVertexView.from_path(model, root_node_path)
    components = root_node.get_descendants(VertexType.component)
    components_by_spec: Dict[ImplicitPartSpec, List[ModelVertexView]] = OrderedDict()
    spec_by_component: Dict[str, ImplicitPartSpec] = OrderedDict()
    for component in components:
        part_spec = ImplicitPartSpec.from_component(component)
        components_by_spec.setdefault(part_spec, []).append(component)
        spec_by_component[component.path] = part_spec
    return components, components_by_spec, spec_by_component

class BomJlcpcbTargetConfig(BaseConfig):
    @property
    def jlcpcb_map_file_template(self) -> str:
        return self._config_data.get("jlcpcb-file", "{build-config}-bom-jlcpcb.yaml")

class BomJlcpcbTarget(Target):
    name = "bom-jlcpcb"
    def __init__(self, muster: TargetMuster) -> None:
        # designators is critical
        # part-map is optional
        self._designator_target = muster.ensure_target("designators")
        self._part_map_target = muster.target_dict.get("part-map")

        # cached intermediates
        # self._components_by_spec: Optional[Dict[ImplicitPartSpec, Iterable[ModelVertexView]]] = None
        # self._spec_by_component: Optional[Dict[str, ImplicitPartSpec]] = None
        # self._missing_part_numbers: Optional[Set[str]] = None
        # self._extra_part_numbers: Optional[Set[str]] = None

        # cached outputs
        self._check_result: Optional[TargetCheckResult] = None
        self._bom: Optional[str] = None

        super().__init__(muster)

    @property
    def config(self) -> BomJlcpcbTargetConfig:
        return BomJlcpcbTargetConfig.from_config(super().config)

    def get_jlcpcb_map_file(self) -> Path:
        return self.project.root / self.config.jlcpcb_map_file_template.format(**{"build-config": self.build_config.name})

    def build(self) -> None:
        if self._bom is None:
            self.generate()

        bom_path = self.project.config.paths.build / self.build_config.root_file.with_suffix(".bom.csv").name
        with bom_path.open("w") as f:
            f.write(self._bom)

    def resolve(self, *args, clean=None, **kwargs) -> None:
        if self.check() == TargetCheckResult.COMPLETE:
            log.info(f"Nothing to resolve for {self.name} target.")
            return

        if clean:
            target_level = TargetCheckResult.COMPLETE
        else:
            target_level = TargetCheckResult.UNTIDY

        # given the designator targets are critical, this must be resolved
        if self._designator_target.check() > target_level:
            self._designator_target.resolve(*args, clean=clean, **kwargs)

        map_file = self.get_jlcpcb_map_file()
        if map_file.exists():
            with map_file.open() as f:
                existing_map = yaml.load(f)
        else:
            existing_map = yaml.load("{}")

        if not isinstance(existing_map, dict):
            log.warning(f"Existing {self.get_jlcpcb_map_file()} is not in the correct format. Rewriting.")
            existing_map = yaml.load("{}")

        for part_number in self._missing_part_numbers:
            existing_map[part_number] = "<fill-me>"

        if clean:
            for part_number in self._extra_part_numbers:
                log.info(f"Removing extraneous part number {part_number} from {self.get_jlcpcb_map_file()}.")
                existing_map.pop(part_number)

        with map_file.open("w") as f:
            yaml.dump(existing_map, f)

        # reload self
        self.muster.reset_target(self.name)

    def check(self) -> TargetCheckResult:
        if self._check_result is None:
            self.generate()
        return max(self._check_result, self._designator_target.check())

    def generate(self) -> None:
        if self._bom is not None:
            return

        component_to_designator_map = self._designator_target.generate()

        # get part map
        part_to_components_map = {}
        components_in_part_map = set()
        if self._part_map_target is not None:
            for component_path, part_number in self._part_map_target.generate().items():
                part_to_components_map.setdefault(part_number, []).append(component_path)
                components_in_part_map.add(component_path)

        # get jlcpcb map
        if self.get_jlcpcb_map_file().exists():
            with self.get_jlcpcb_map_file().open() as f:
                jlcpcb_map = yaml.load(f)
            if not isinstance(jlcpcb_map, dict):
                # TODO: better schema enofrcement
                log.error(f"Existing {self.get_jlcpcb_map_file()} is not in the correct format. Ignoring it. Run `ato resolve {self.name}` to fix this.")
                self.elevate_check_result(TargetCheckResult.UNTIDY)
                jlcpcb_map = yaml.load("{}")
        else:
            log.warning(f"Missing {self.get_jlcpcb_map_file()}.")
            jlcpcb_map = yaml.load("{}")

        # get implicit parts
        components, components_by_spec, spec_by_component = part_spec_groups(self.model, self.build_config.root_node)

        # build up component to jlcpcb map
        component_to_jlcpcb_map = {}
        missing_part_to_component = set()
        missing_spec_to_component = set()
        for component in components:






        self._components_by_spec, self._spec_by_component = part_spec_groups(self.model, self.build_config.root_node)
        part_numbers_expected = set(part_to_components_map.keys())
        self._missing_part_numbers = part_numbers_expected
        self._components_missing = set()
        self._extra_part_numbers = set()

        part_numbers_available = set(jlcpcb_map.get("by-part-number", {}).keys())
        self._missing_part_numbers = part_numbers_expected - part_numbers_available
        self._extra_part_numbers = part_numbers_available - part_numbers_expected

        if self._missing_part_numbers:
            log.error(f"Missing part numbers for {len(part_numbers_expected - part_numbers_available)} parts. Cannot continue. Run `ato resolve {self.name}` to fix this.")
            self._check_result = TargetCheckResult.UNSOLVABLE
            return

        if self._extra_part_numbers:
            log.warning(f"Extraneous part numbers for {len(part_numbers_available - part_numbers_expected)} parts. Run `ato resolve --clean {self.name}` to fix this.")
            self._check_result = TargetCheckResult.UNTIDY
        else:
            self._check_result = TargetCheckResult.COMPLETE

        bom_rows = ["Comment,Designator,Footprint,LCSC"]
        for part_number, component_paths in part_to_components_map.items():
            component_view = ModelVertexView.from_path(self.model, component_path)
            comment = component_view.data.get("value", "")

            designators = ",".join([component_to_designator_map[p] for p in component_paths])
            if len(component_paths) > 1:
                designators = "\"" + designators + "\""

            footprint = component_view.data.get("footprint", "")
            lcsc = jlcpcb_map[part_number]
            row = ",".join([comment, designators, footprint, lcsc])
            bom_rows.append(row)

        self._bom = "\n".join(bom_rows)
