import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.util import predicated_once


class is_pulled(Module.TraitT.decless()):
    def __init__(self, signal: F.ElectricSignal):
        super().__init__()
        self.signal = signal

    @predicated_once(lambda result: result is True)
    def check(self) -> bool:
        connected_to = self.signal.line.get_connected()
        if connected_to is None:
            return False

        for mif, _ in connected_to.items():
            if (parent := mif.get_parent()) is not None:
                if isinstance(parent[0], F.Resistor):
                    return True

        return False
