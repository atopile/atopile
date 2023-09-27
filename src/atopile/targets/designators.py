import logging
from pathlib import Path
from typing import Dict, List

# TODO: pick one yaml injestor
import ruamel.yaml
import yaml

from atopile.model.accessors import ModelVertexView
from atopile.model.model import VertexType
from atopile.project.config import BaseConfig
from atopile.targets.targets import Target, TargetCheckResult
from atopile.utils import update_dict

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class DesignatorConfig(BaseConfig):
    @property
    def designators_file_template(self) -> str:
        return self._config_data.get("designators-file", "{build-config}-designators.yaml")

    @property
    def default_prefix(self) -> str:
        return self._config_data.get("default-prefix", "U")

class Designators(Target):
    name = "designators"

    def __init__(self, *args, **kwargs) -> None:
        self._designator_map: Dict[str, str] = None
        self._check_result: TargetCheckResult = None
        super().__init__(*args, **kwargs)

    @property
    def config(self) -> DesignatorConfig:
        return DesignatorConfig.from_config(super().config)

    def get_designators_file(self) -> Path:
        return self.project.root / self.config.designators_file_template.format(**{"build-config": self.build_config.name})

    def check(self) -> TargetCheckResult:
        if self._check_result is not None:
            return self._check_result
        self.generate()
        return self._check_result

    @property
    def check_has_been_run(self) -> bool:
        return self._check_result is not None

    def generate(self) -> Dict[str, str]:
        # cache previous builds
        # designators are common enough that we're likely to call a few times during other targets
        # we also use this data for checks
        if self._designator_map is not None:
            return self._designator_map

        assert isinstance(self.config, DesignatorConfig)

        # set this as unsolvable at the beginning so if it crashes, the check is pre-marked as failed
        self._check_result = TargetCheckResult.UNSOLVABLE

        # get designator file data
        designators_file = self.get_designators_file()
        if designators_file.exists():
            with designators_file.open() as f:
                designator_file_data: Dict[str, str] = yaml.safe_load(f)
        else:
            designator_file_data = {}

        root_node = ModelVertexView.from_path(self.model, self.build_config.root_node)
        components = root_node.get_descendants(VertexType.component)
        rel_paths = {c.index: root_node.relative_path(c) for c in components}

        # find all the components still missing designators
        components_to_designate: List[ModelVertexView] = []
        designator_map: Dict[str, str] = {}

        for component in components:
            rel_path = rel_paths[component.index]
            existing_designator = designator_file_data.get(component.path) or designator_file_data.get(rel_path)
            if existing_designator is None:
                components_to_designate.append(component)
                continue

            if existing_designator in designator_map.values():
                components_to_designate.append(component)
                continue

            designator_prefix = component.get_data("designator_prefix", self.config.default_prefix)
            if not existing_designator.startswith(designator_prefix):
                components_to_designate.append(component)
                log.warning(f"{component.path} has a designator-prefix mis-match. Regenerating designator.")
                continue

            # if none of the above, then we're cool with the existing designator. Let's roll.
            designator_map[rel_path] = existing_designator

        # if at this point, we've got stuff to designate, we're solvable
        # if not, perhaps we're still untidy
        if components_to_designate:
            check_result = TargetCheckResult.SOLVABLE
        elif set(designator_map.keys()) == set(designator_file_data.keys()):
            check_result = TargetCheckResult.COMPLETE
        else:
            check_result = TargetCheckResult.UNTIDY

        # generate designators and back-assign everything to the designator data
        MAX_DESIGNATOR = 10000
        for component in components_to_designate:
            designator_prefix = component.get_data("designator_prefix", self.config.default_prefix)
            # TODO: this is cruddy and inefficent. Fix it.
            for i in range(1, MAX_DESIGNATOR):
                designator = designator_prefix + str(i)
                if designator not in designator_map.values():
                    designator_map[rel_paths[component.index]] = designator
                    break
            else:
                raise ValueError(f"Exceeded the limit of {MAX_DESIGNATOR} on a board! Eeek!")

        # finally, return the designator values
        self._designator_map = designator_map
        self._check_result = check_result
        return designator_map

    def build(self) -> None:
        output_file = self.build_config.build_path / self.build_config.root_file.with_suffix(".ref-map.yaml").name
        designator_map = [(v, k) for k, v in self.generate().items()]
        sorted_designators = sorted(designator_map, key=lambda x: x[0] or 0)
        with output_file.open("w") as f:
            for designator, path in sorted_designators:
                f.write(f"{designator}: {path}\n")

    def resolve(self, *args, clean=None , **kwargs) -> None:
        # TODO: better caching?
        if self._designator_map is None:
            self.generate()

        # input sanitisation
        if clean is None:
            clean = False

        # using ruamel.yaml to preserve quotes, comments, etc...
        yaml = ruamel.yaml.YAML()
        yaml.preserve_quotes = True

        designators_file = self.get_designators_file()
        if designators_file.exists():
            with designators_file.open() as f:
                designator_file_data: Dict[str, str] = yaml.load(f)
        else:
            designator_file_data: Dict[str, str] = {}

        update_dict(designator_file_data, self._designator_map)

        if clean:
            # remove any designators that are no longer in the designator map
            for k in list(designator_file_data.keys()):
                if k not in self._designator_map:
                    designator_file_data.pop(k)
                    log.warning(f"Removing designator {k} from {designators_file} as it is no longer in the designator map.")

        with designators_file.open("w") as f:
            yaml.dump(designator_file_data, f)

        log.info(f"Designators written to {designators_file}")
