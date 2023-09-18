import json
import logging

import ruamel.yaml

from atopile.model.accessors import ModelVertexView
from atopile.targets.targets import Target, TargetCheckResult, TargetMuster
from atopile.viewer.render import build_view

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

yaml = ruamel.yaml.YAML()
yaml.preserve_quotes = True


class SchematicViewTarget(Target):
    name = "sch-view"

    def __init__(self, muster: TargetMuster) -> None:
        super().__init__(muster)

    def build(self) -> None:
        # ensure a build outputs directory
        output_dir = self.build_config.build_path / self.name
        output_dir.mkdir(parents=True, exist_ok=True)

        # write the core schematic file
        root_node_mvv = ModelVertexView.from_path(self.model, self.build_config.root_node)
        sch = build_view(self.model, self.build_config.root_node)
        sch_file = output_dir / f"{root_node_mvv.ref}.json"
        log.info("Writing schematic view to %s", str(sch_file))
        with sch_file.open("w") as f:
            json.dump(sch, f)

        for ato_src in self.model.src_files:
            # go from something.ato -> something.vis.yaml
            input_vis_file = self.project.root / ato_src.with_suffix(".vis.yaml")
            output_vis_file = output_dir / ato_src.with_suffix(".vis.json")

            if input_vis_file.exists():
                output_vis_file.parent.mkdir(parents=True, exist_ok=True)
                with input_vis_file.open() as in_f, output_vis_file.open("w") as out_f:
                    json.dump(yaml.load(in_f), out_f)

    def resolve(self, *args, clean=None, **kwargs) -> None:
        # nothing to resolve for this target
        pass

    def check(self) -> TargetCheckResult:
        # TODO: I think the only thing here that'd stop us is an unsolvble model,
        # which is picked up prior to this step
        return TargetCheckResult.COMPLETE
