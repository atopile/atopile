import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.sets.quantity_sets import Quantity_Interval
from faebryk.libs.util import predicated_once


class is_pulled(Module.TraitT.decless()):
    def __init__(self, signal: F.ElectricSignal):
        super().__init__()
        self.signal = signal

    @predicated_once(lambda result: result is True)
    def check(self, required_resistance: Quantity_Interval) -> bool:
        connected_to = self.signal.line.get_connected()
        if connected_to is None:
            return False

        resistors = []
        for mif, _ in connected_to.items():
            if (maybe_parent := mif.get_parent()) is not None:
                parent, _ = maybe_parent

                if isinstance(parent, F.Resistor):
                    resistors.append(parent)

        if len(resistors) == 0:
            return False
        elif len(resistors) == 1:
            return resistors[0].resistance in required_resistance
        else:
            raise ValueError(
                "Cannot determine effective resistance of multiple resistors"
            )
