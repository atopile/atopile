from typing import Callable, Sequence

from faebryk.core.node import Node
from faebryk.core.trait import Trait


class implements_design_check(Trait.TraitT.decless()):
    class CheckException(Exception):
        nodes: Sequence[Node]

        def __init__(
            self, message: str, nodes: Sequence[Node], bus: set[Node] | None = None
        ):
            self.nodes = nodes
            self.bus = bus
            super().__init__(message)

    def __init__(self, check: Callable[[], None]):
        super().__init__()
        self.check = check
