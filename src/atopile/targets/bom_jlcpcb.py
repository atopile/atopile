import logging
from typing import Dict, List, Tuple

from atopile.model.accessors import ModelVertexView
from atopile.model.model import VertexType
from atopile.targets.targets import Target

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class BomJlcpcbTarget(Target):
    # TODO: support partially specified BOMs
    def generate(self) -> None:
        output_file = self.project.config.paths.build / self.build_config.root_file.with_suffix(".ref-map.yaml").name
        root_node = ModelVertexView.from_path(self.model, self.build_config.root_node)
        generic_descendants = root_node.get_descendants(VertexType.component)

        # we'll assume a component is the same part if all:
        # - it has the same footprint
        # - it has the same value
        # - it's an instance of the same class
        component_groups: Dict[Tuple[str, str, str, str], List[ModelVertexView]] = []
        for component in generic_descendants:
            # primarily group by LCSC part number
            if component.data.get("lcsc"):
                key = (None, None, None, component.data.get("lcsc"))
            # fall back to footprint, value, and instance_of combination
            else:
                key = (component.data.get("footprint"), component.data.get("value"), component.instance_of.path, None)
            component_groups.setdefault(key, []).append(component)

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
