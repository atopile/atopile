import logging
from typing import Any, Dict, List, Optional, Tuple, Union, Set, Iterable
from collections import OrderedDict
from pathlib import Path

import ruamel.yaml
from attrs import define, field, frozen

from atopile.model.accessors import ModelVertexView
from atopile.model.model import Model, VertexType
from atopile.project.config import BaseConfig
from atopile.project.project import Project
from atopile.targets.targets import Target, TargetCheckResult, TargetMuster
from atopile.utils import update_dict

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

yaml = ruamel.yaml.YAML()
yaml.preserve_quotes = True

class ComponentSelectionConfig(BaseConfig):
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
        if self.footprint and self.footprint != component.data.get("footprint"):
            return False
        if self.value and self.value != component.data.get("value"):
            return False
        return True

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ImplicitPartSpec":
        return ImplicitPartSpec(data["instance_of"], data.get("footprint"), data.get("value"), data.get("part"))

    @staticmethod
    def from_component(component: ModelVertexView) -> "ImplicitPartSpec":
        return ImplicitPartSpec(component.instance_of.path, component.data.get("footprint"), component.data.get("value"), component.data.get("part"))

    def to_dict(self) -> Dict[str, Any]:
        return {"instance_of": self.instance_of, "footprint": self.footprint, "value": self.value, "part": self.part}

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
    def config(self) -> ComponentSelectionConfig:
        return ComponentSelectionConfig.from_config(super().config)

    def get_mfg_map_file(self) -> Path:
        return self.project.root / self.config.component_selection_file_template.format(**{"build-config": self.build_config.name})

    def get_components(self) -> List[ModelVertexView]:
        if self._components is not None:
            return self._components

        root_node = ModelVertexView.from_path(self.model, self.build_config.root_node)
        self._components = root_node.get_descendants(VertexType.component)
        return self._components

    def build(self) -> None:
        part_map_path = self.project.config.paths.build / self.build_config.root_file.with_suffix(".part-map.yaml").name
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
                existing_file_data.setdefault("implicit", []).append(missing_spec.to_dict())

        if clean:
            for unused_implicit_spec in self._unused_implicit_specs:
                log.info(f"Removing unused implicit spec {unused_implicit_spec.to_dict()} from {self.get_mfg_map_file()}.")
                existing_file_data["implicit"].remove(unused_implicit_spec.to_dict())
            for unused_explicit_spec in self._unused_explicit_specs:
                log.info(f"Removing unused explicit spec {unused_explicit_spec} from {self.get_mfg_map_file()}.")
                existing_file_data["explicit"].pop(unused_explicit_spec)

        with mfg_map_file.open("w") as f:
            yaml.dump(existing_file_data, f)

    def check(self) -> TargetCheckResult:
        # cache previous checks
        if self._check_result is None:
            self.generate()
        return self._check_result

    @property
    def check_has_been_run(self) -> bool:
        if self._check_result is None:
            return False
        return True

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
            self._check_result = TargetCheckResult.UNSOLVABLE

        self._implict_part_specs: List[ImplicitPartSpec] = []
        for key_data in file_data.get("implicit", []):
            self._implict_part_specs.append(ImplicitPartSpec.from_dict(key_data))

        components = self.get_components()

        component_path_to_part_number = {}
        undefined_components = []
        used_implicit_specs = []
        used_explicit_specs = []
        for c in components:
            # embedded in the ato file
            # TODO: not sure this is a great idea
            # TODO: we should at least be able to glob match these or something
            if c.data.get("mfg_part_number"):
                log.info(f"Using mfg part number {c.data.get('mfg_part_number')} from ato code for {c.path}.")
                component_path_to_part_number[c.path] = c.data.get("mfg_part_number")
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
                if matching_specs[0].part is not None:
                    log.info(f"Using implicit mfg part number {matching_specs[0].part} for {c.path}.")
                    component_path_to_part_number[c.path] = matching_specs[0].part
                    used_implicit_specs.append(matching_specs[0])
                    continue
            elif len(matching_specs) > 1:
                log.error(f"Multiple implicit part specs match {c.path}.")
                continue

            log.error(f"No part number for {c.path}.")
            undefined_components.append(c)

        self._unused_implicit_specs = set(self._implict_part_specs) - set(used_implicit_specs)
        self._unused_explicit_specs = set(file_data.get("explicit", {}).keys()) - set(used_explicit_specs)
        self._unspecd_components = undefined_components

        if undefined_components:
            log.error(f"Unable to generate {self.name} target.")
            self._check_result = TargetCheckResult.UNSOLVABLE
            return

        if self._unused_implicit_specs or self._unused_explicit_specs:
            log.warning(f"There are extraneous specs in {self.get_mfg_map_file()}. Run `ato resolve --clean {self.name}` to fix this.")
            self._check_result = TargetCheckResult.UNTIDY

        self._check_result = TargetCheckResult.COMPLETE
        self._component_path_to_part_number = component_path_to_part_number

        return self._component_path_to_part_number

class DefunctBomJlcpcbTarget(Target):
    name = "bom-jlcpcb"

    def __init__(self, muster: TargetMuster) -> None:
        self._designator_target = muster.ensure_target("designators")
        self._part_map_target = muster.ensure_target("part-map")
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

class BomJlcpcbTarget(Target):
    name = "bom-jlcpcb"
    def __init__(self, muster: TargetMuster) -> None:
        self.muster = muster

    @property
    def project(self) -> Project:
        return self.muster.project

    @property
    def model(self) -> Model:
        return self.muster.model

    @property
    def build_config(self) -> BuildConfig:
        return self.muster.build_config

    @property
    def name(self) -> str:
        raise NotImplementedError

    @property
    def config(self) -> BaseConfig:
        return self.project.config.targets.get(self.name, BaseConfig({}, self.project, self.name))

    def build(self) -> None:
        """
        Build this targets output and save it to the build directory.
        What gets called when you run `ato build <target>`
        """
        raise NotImplementedError

    def resolve(self, *args, clean=None, **kwargs) -> None:
        """
        Interactively solve for missing data, potentially:
        - prompting the user for more info
        - outputting template files for a user to fill out
        This function is expected to be called manually, and is
        therefore allowed to write to version controlled files.
        This is what's run with the `ato resolve <target>` command.
        """
        raise NotImplementedError

    def check(self) -> TargetCheckResult:
        """
        Check whether all the data required to build this target is available and valid.
        This is what's run with the `ato check <target>` command.
        """
        raise NotImplementedError

    @property
    def check_has_been_run(self) -> bool:
        raise NotImplementedError

    def generate(self) -> Any:
        """
        Generate and return the underlying data behind the target.
        This isn't available from the command-line and is instead only used internally.
        It provides other targets with access to the data generated by this target.
        """
        raise NotImplementedError
