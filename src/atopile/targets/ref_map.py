from typing import List, Tuple

from atopile.model.accessors import get_all
from atopile.model.model import VertexType
from atopile.targets.targets import Target


class RefMapTarget(Target):
    def generate(self) -> None:
        output_file = self.project.config.paths.build / self.build_config.root_file.with_suffix(".ref-map").name
        designators: List[Tuple[str, str]] = [(c.data.get("designator"), str(c.path)) for c in get_all(self.model, VertexType.component)]
        sorted(designators, key=lambda x: x[0] or 0)
        with output_file.open("w") as f:
            for designator, path in designators:
                f.write(f"{designator}: {path}\n")

    required_resolvers = ["designators"]
