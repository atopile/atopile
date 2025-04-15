from typing import Callable, Sequence

from faebryk.core.module import Module
from faebryk.core.node import Node


class implements_design_check(Module.TraitT.decless()):
    class CheckException(Exception):
        nodes: Sequence[Node]

        def __init__(self, message: str, nodes: Sequence[Node]):
            self.nodes = nodes
            super().__init__(message)

    def __init__(self, check: Callable[[], None]):
        super().__init__()
        self.check = check
