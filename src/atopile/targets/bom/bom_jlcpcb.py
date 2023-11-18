import copy
import logging
from collections import ChainMap, OrderedDict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import ruamel.yaml
from atopile.model.accessors import ModelVertexView
from atopile.model.model import Model, VertexType
from atopile.project.config import BaseConfig
from atopile.project.project import Project
from atopile.targets.targets import Target, TargetCheckResult, TargetMuster
from attrs import frozen

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
        if self.footprint and self.footprint != component.get_data("footprint"):
            return False
        if self.value and self.value != component.get_data("value"):
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
        return ImplicitPartSpec(component.instance_of.path, component.get_data("footprint"), component.get_data("value"))

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
        self._component_to_jlcpcb_map: Dict = None
        self._missing_part_to_jlcpcb: Set = None
        self._missing_spec_to_jlcpcb: Set = None

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

        if self._check_result >= TargetCheckResult.UNSOLVABLE:
            log.error(f"Cannot build {self.name} target due to missing translations. Run `ato resolve {self.name}` to fix this.")
            return

        bom_path = self.build_config.build_path / self.build_config.root_file.with_suffix(".bom.csv").name
        with bom_path.open("w") as f:
            f.write(self._bom)

    def resolve(self, *args, clean=None, **kwargs) -> None:
        if self.check() == TargetCheckResult.COMPLETE:
            log.info(f"Nothing to resolve for {self.name} target.")
            return

        # get jlcpcb map
        if self.get_jlcpcb_map_file().exists():
            with self.get_jlcpcb_map_file().open() as f:
                jlcpcb_map = yaml.load(f)
            if not isinstance(jlcpcb_map, dict):
                # TODO: better schema enofrcement
                log.error(f"Existing {self.get_jlcpcb_map_file()} is not in the correct format. Rewriting it.")
                self.elevate_check_result(TargetCheckResult.UNTIDY)
                jlcpcb_map = yaml.load("{}")
        else:
            log.warning(f"Missing {self.get_jlcpcb_map_file()}.")
            jlcpcb_map = yaml.load("{}")

        for part_number in self._missing_part_to_jlcpcb:
            jlcpcb_map.setdefault("by-part", {})[part_number] = "<fill-me>"

        for spec in self._missing_spec_to_jlcpcb:
            spec_dict = spec.to_dict()
            spec_dict["jlcpcb"] = "<fill-me>"
            jlcpcb_map.setdefault("by-spec", []).append(spec_dict)

        with self.get_jlcpcb_map_file().open("w") as f:
            yaml.dump(jlcpcb_map, f)

    def check(self) -> TargetCheckResult:
        if self._check_result is None:
            self.generate()
        return max(self._check_result, self._designator_target.check())

    def generate(self) -> None:
        if self._component_to_jlcpcb_map is not None:
            return self._component_to_jlcpcb_map

        component_to_designator_map = self._designator_target.generate()

        # get part map
        # part_to_components_map = {}
        # components_in_part_map = set()
        # if self._part_map_target is not None:
        #     for component_path, part_number in self._part_map_target.generate().items():
        #         part_to_components_map.setdefault(part_number, []).append(component_path)
        #         components_in_part_map.add(component_path)
        if self._part_map_target is None:
            component_to_part_map = {}
        else:
            component_to_part_map = self._part_map_target.generate()

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

        # get implicit part specs
        components, _, spec_by_component = part_spec_groups(self.model, self.build_config.root_node)

        # get implicit spec-to-jlcpcb map
        def _spec_data_to_map(
            spec_data: List[Dict[str, Any]],
            path_offset: Optional[str] = None
        ) -> Dict[ImplicitPartSpec, str]:
            """
            Convert a list of spec data to a map of spec to jlcpcb part number.
            If the path_offset is provided, it will be prepended to the instance_of field.
            """
            spec_map = {}
            for _data in spec_data:
                data = copy.deepcopy(_data)
                if data.get("jlcpcb", "<fill-me>") != "<fill-me>":
                    # FIXME: please lord forgive me for these sins
                    if path_offset is not None:
                        if not data["instance_of"].startswith("std/"):
                            data["instance_of"] = path_offset + "/" + data["instance_of"]

                    spec_map[ImplicitPartSpec.from_dict(data)] = data["jlcpcb"]

                else:
                    log.warning(f"Missing jlcpcb part number for {data}.")
            return spec_map

        top_level_specs_to_jlcpcb = _spec_data_to_map(jlcpcb_map.get("by-spec", []))

        # FIXME: big o'l hack; globbing the bom-maps and sorting them by length ISN'T a good way to do this
        bom_map_paths = sorted(self.project.root.glob("**/*-bom-jlcpcb.yaml"), key=lambda p: len(p.parts))

        bom_map_by_specs: dict[Path, Dict[ImplicitPartSpec, str]] = {}
        for bom_map_path in bom_map_paths:
            with bom_map_path.open() as f:
                bom_map = yaml.load(f)
            if not isinstance(bom_map, dict):
                log.warning(f"Skipping {bom_map_path} because it is not in the correct format.")
                continue
            sub_project = Project(bom_map_path.parent, self.project.config)
            standardised_sub_project_root = self.project.standardise_import_path(sub_project.root)
            bom_map_by_specs[bom_map_path] = _spec_data_to_map(bom_map.get("by-spec", []), str(standardised_sub_project_root))

        specs_to_jlcpcb = ChainMap(top_level_specs_to_jlcpcb, *bom_map_by_specs.values())

        # build up component to jlcpcb map
        component_to_jlcpcb_map = {}
        self._missing_part_to_jlcpcb = set()
        self._missing_spec_to_jlcpcb = set()
        for component in components:
            if component.path in jlcpcb_map.get("explicit", {}):
                component_to_jlcpcb_map[component.path] = jlcpcb_map.get("explicit", {}).get(component.path)
                continue

            if component.path in component_to_part_map:
                part_number = component_to_part_map[component.path]
                if part_number in jlcpcb_map.get("by-part", {}):
                    component_to_jlcpcb_map[component.path] = jlcpcb_map["by-part"][part_number]
                    continue
                else:
                    self._missing_part_to_jlcpcb.add(part_number)
                    continue

            component_spec = spec_by_component[component.path]
            if component_spec in specs_to_jlcpcb:
                component_to_jlcpcb_map[component.path] = specs_to_jlcpcb[component_spec]
                continue

            self._missing_spec_to_jlcpcb.add(component_spec)
            log.error(f"Missing jlcpcb part number for {component.path}.")

        if self._missing_part_to_jlcpcb or self._missing_spec_to_jlcpcb:
            log.error(f"Missing translations. Cannot continue. Run `ato resolve {self.name}` to fix this.")
            self.elevate_check_result(TargetCheckResult.UNSOLVABLE)
            return {}

        self._component_to_jlcpcb_map = component_to_jlcpcb_map
        self.elevate_check_result(TargetCheckResult.COMPLETE)

        # combine like components
        jlcpcb_to_component_map = {}
        for component_path, jlcpcb_part_number in component_to_jlcpcb_map.items():
            jlcpcb_to_component_map.setdefault(jlcpcb_part_number, []).append(component_path)

        # build up bom
        bom_rows = ["Comment,Designator,Footprint,LCSC"]
        for jlcpcb_number, component_paths in jlcpcb_to_component_map.items():
            if jlcpcb_number == "ignore":
                continue

            component_path = component_paths[0]
            component_view = ModelVertexView.from_path(self.model, component_path)
            comment = component_view.get_data("value", "")

            # designator map's paths are relative to the root node
            root_node = ModelVertexView.from_path(self.model, self.build_config.root_node)
            like_components = [ModelVertexView.from_path(self.model, p) for p in component_paths]
            designators = ",".join(component_to_designator_map[root_node.relative_path(p)] for p in like_components)
            if len(component_paths) > 1:
                designators = "\"" + designators + "\""

            footprint = component_view.get_data("footprint", "").split(":")[-1]
            lcsc = jlcpcb_number
            row = ",".join([comment, designators, footprint, lcsc])
            bom_rows.append(row)

        self._bom = "\n".join(bom_rows)

        return self._component_to_jlcpcb_map
