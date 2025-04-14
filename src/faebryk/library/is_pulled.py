import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.node import Node
from faebryk.core.pathfinder import find_paths
from faebryk.library.implements_design_check import CheckException
from faebryk.libs.library import L
from faebryk.libs.util import once


class RequiresPullNotFulfilled(CheckException):
    def __init__(self, nodes: list[Node]):
        self.nodes = nodes
        super().__init__(
            f"Signals requiring pulls but not pulled: "
            f"{', '.join(mif.get_full_name() for mif in nodes)}"
        )


class is_pulled(Module.TraitT.decless()):
    def __init__(self, signal: F.ElectricSignal):
        super().__init__()
        self.signal = signal

    @L.rt_field
    def check(self) -> F.implements_design_check:
        @once  # TODO: only cache once True
        def _check():
            # TODO: more efficient method?
            paths = find_paths(self.signal, [self.signal.reference])
            for path in paths:
                for node in path:
                    if isinstance(node, F.Resistor):
                        return

            raise RequiresPullNotFulfilled([self.signal])

        return F.implements_design_check(_check)
