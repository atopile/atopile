import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import ruamel.yaml
from attrs import frozen

from atopile.model.accessors import ModelVertexView
from atopile.model.model import VertexType
from atopile.project.config import BaseConfig
from atopile.targets.targets import Target, TargetCheckResult, TargetMuster


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

yaml = ruamel.yaml.YAML()
yaml.preserve_quotes = True

class PartMapConfig(BaseConfig):
    @property
    def component_selection_file_template(self) -> str:
        return self._config_data.get("component-selection-file", "{build-config}-components.yaml")

@frozen
class ImplicitPartSpec:
    instance_of: str
    footprint: Optional[str]
    value: Optional[str]
    part: Optional[str]

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
        part = data.get("part")
        if part == "<fill-me>":
            part = None
        return ImplicitPartSpec(data["instance_of"], data.get("footprint"), data.get("value"), part)

    @staticmethod
    def from_component(component: ModelVertexView) -> "ImplicitPartSpec":
        return ImplicitPartSpec(
            component.instance_of.path,
            component.get_data("footprint"),
            component.get_data("value"),
            component.get_data("part")
        )

    def to_dict(self, missing_part: str) -> Dict[str, Any]:
        result = {"instance_of": self.instance_of, "footprint": self.footprint, "value": self.value, "part": self.part or missing_part}
        return {k: v for k, v in result.items() if v is not None}


class PartMapTarget(Target):
    name = "part-map"

    def __init__(self, muster: TargetMuster) -> None:
        # cached outputs
        self._component_path_to_part_number: Optional[Dict[str, str]] = None
        self._check_result: Optional[TargetCheckResult] = None

        # cached inputs
        self._components: Optional[List[ModelVertexView]] = None
        self._implict_part_specs: Optional[List[ImplicitPartSpec]] = None

        # cached intermediate results
        self._unused_implicit_specs: Optional[Set[ImplicitPartSpec]] = None
        self._unused_explicit_specs: Optional[Set[str]] = None
        self._unspecd_components: Optional[List[ModelVertexView]] = None

        super().__init__(muster)

    @property
    def config(self) -> PartMapConfig:
        return PartMapConfig.from_config(super().config)

    def get_mfg_map_file(self) -> Path:
        return self.project.root / self.config.component_selection_file_template.format(**{"build-config": self.build_config.name})

    def get_components(self) -> List[ModelVertexView]:
        if self._components is not None:
            return self._components

        root_node = ModelVertexView.from_path(self.model, self.build_config.root_node)
        self._components = root_node.get_descendants(VertexType.component)
        return self._components

    def build(self) -> None:
        part_map_path = self.build_config.build_path / self.build_config.root_file.with_suffix(".part-map.yaml").name
        with part_map_path.open("w") as f:
            f.write(yaml.dump(self.generate()))

    def resolve(self, *args, clean=None, **kwargs) -> None:
        # skip this if there's nothing to do
        if self.check() == TargetCheckResult.COMPLETE:
            log.info(f"Nothing to resolve for {self.name} target.")
            return

        # ensure generate has been run
        self.generate()

        mfg_map_file = self.get_mfg_map_file()

        if mfg_map_file.exists():
            with mfg_map_file.open() as f:
                existing_file_data = yaml.load(f)
        else:
            existing_file_data = yaml.load("{}")

        if not isinstance(existing_file_data, dict):
            log.warning(f"Existing {self.get_mfg_map_file()} is not in the correct format. Rewriting.")
            existing_file_data = yaml.load("{}")

        missing_specs: Set[ImplicitPartSpec] = set()
        for unspecd_component in self._unspecd_components:
            missing_specs.add(ImplicitPartSpec.from_component(unspecd_component))

        if missing_specs:
            log.warning(f"Missing part numbers for {len(missing_specs)} parts. You need to manually add these to {self.get_mfg_map_file()}.")
            for missing_spec in missing_specs:
                existing_file_data.setdefault("implicit", []).append(missing_spec.to_dict("<fill-me>"))

        if clean:
            for spec in existing_file_data.get("implicit", []):
                if spec in self._unused_implicit_specs:
                    log.info(f"Removing unused implicit spec {spec} from {self.get_mfg_map_file()}.")
                    existing_file_data["implicit"].remove(spec)
            for unused_explicit_spec in self._unused_explicit_specs:
                log.info(f"Removing unused explicit spec {unused_explicit_spec} from {self.get_mfg_map_file()}.")
                existing_file_data["explicit"].pop(unused_explicit_spec)

        with mfg_map_file.open("w") as f:
            yaml.dump(existing_file_data, f)

        # reload self
        self.muster.reset_target(self.name)

    def check(self) -> TargetCheckResult:
        # cache previous checks
        if self._check_result is None:
            self.generate()
        return self._check_result

    def generate(self) -> Dict[str, str]:
        # cache previous builds
        if self._component_path_to_part_number is not None:
            return self._component_path_to_part_number

        # get existing data
        component_selection_file = self.get_mfg_map_file()
        if component_selection_file.exists():
            with component_selection_file.open() as f:
                file_data = yaml.load(f)
        else:
            file_data = {}

        if not isinstance(file_data, dict):
            log.warning(f"Existing {self.get_mfg_map_file()} is not in the correct format. Ignoring.")
            # TODO: danger of overwriting the check?
            # consider creating a helper function `elevate_check_result` or something
            self._check_result = TargetCheckResult.UNTIDY
            file_data = {}

        self._implict_part_specs: List[ImplicitPartSpec] = []
        for key_data in file_data.get("implicit", []):
            self._implict_part_specs.append(ImplicitPartSpec.from_dict(key_data))

        components = self.get_components()

        component_path_to_part_number = {}
        unspecd_components = []
        partially_specd_components = []
        used_implicit_specs = []
        used_explicit_specs = []
        for c in components:
            # embedded in the ato file
            # TODO: not sure this is a great idea
            # TODO: we should at least be able to glob match these or something
            if c.get_data("mfg_part_number"):
                log.info(f"Using mfg part number {c.get_data('mfg_part_number')} from ato code for {c.path}.")
                component_path_to_part_number[c.path] = c.get_data("mfg_part_number")
                continue

            # explicitly defined in the part map file
            if c.path in file_data.get("explicit", {}):
                log.info(f"Using explicit mfg part number {file_data['explicit'][c.path]} for {c.path}.")
                used_explicit_specs.append(c.path)
                component_path_to_part_number[c.path] = file_data["explicit"][c.path]
                continue

            # implicitly defined in the part map file
            matching_specs: List[ImplicitPartSpec] = [s for s in self._implict_part_specs if s.matches_component(c)]
            if len(matching_specs) == 1:
                # TODO: move fill me to a constant
                if matching_specs[0].part != "<fill-me>":
                    log.info(f"Using implicit mfg part number {matching_specs[0].part} for {c.path}.")
                    component_path_to_part_number[c.path] = matching_specs[0].part
                    used_implicit_specs.append(matching_specs[0])
                    continue
                else:
                    log.error(f"Part number for {c.path} needs to be filled in.")
                    partially_specd_components.append(c)
                    continue

            elif len(matching_specs) > 1:
                log.error(f"Multiple implicit part specs match {c.path}.")
                continue

            log.error(f"No part number for {c.path}.")
            unspecd_components.append(c)

        self._unused_implicit_specs = set(self._implict_part_specs) - set(used_implicit_specs)
        self._unused_explicit_specs = set(file_data.get("explicit", {}).keys()) - set(used_explicit_specs)
        self._unspecd_components = unspecd_components
        self._partially_specd_components = partially_specd_components

        if unspecd_components or partially_specd_components:
            log.error(f"Unable to generate {self.name} target since some data is missing.")
            self._check_result = TargetCheckResult.UNSOLVABLE
            return

        if self._unused_implicit_specs or self._unused_explicit_specs:
            log.warning(f"There are extraneous specs in {self.get_mfg_map_file()}. Run `ato resolve --clean {self.name}` to fix this.")
            self._check_result = TargetCheckResult.UNTIDY

        self._check_result = TargetCheckResult.COMPLETE
        self._component_path_to_part_number = component_path_to_part_number

        return self._component_path_to_part_number
