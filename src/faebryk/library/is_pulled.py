import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.pathfinder import find_paths
from faebryk.libs.util import once


class is_pulled(Module.TraitT.decless()):
    def __init__(self, signal: F.ElectricSignal):
        super().__init__()
        self.signal = signal

    @property
    @once  # TODO: only cache once True
    def fulfilled(self) -> bool:
        # TODO: more efficient method?
        paths = find_paths(self.signal, [self.signal.reference])
        for path in paths:
            for node in path:
                if isinstance(node, F.Resistor):
                    return True

        return False
