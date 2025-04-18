from typing import Callable, Sequence

from faebryk.core.node import Node
from faebryk.core.trait import Trait


class implements_design_check(Trait.TraitT.decless()):
    class UnfulfilledCheckException(Exception):
        nodes: Sequence[Node]

        def __init__(self, message: str, nodes: Sequence[Node]):
            self.nodes = nodes
            super().__init__(message)

    class MaybeUnfulfilledCheckException(UnfulfilledCheckException): ...

    def __init__(self, check: Callable[[], None]):
        super().__init__()
        self.check = check
