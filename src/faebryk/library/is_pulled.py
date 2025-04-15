import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.pathfinder import find_paths
from faebryk.libs.util import predicated_once


class is_pulled(Module.TraitT.decless()):
    def __init__(self, signal: F.ElectricSignal):
        super().__init__()
        self.signal = signal

    @predicated_once(lambda result: result is True)
    def check(self) -> bool:
        # TODO: more efficient method?
        paths = find_paths(self.signal, [self.signal.reference])
        for path in paths:
            for node in path:
                if isinstance(node, F.Resistor):
                    return True

        return False
