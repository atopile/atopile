# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.Logic import Logic


class ElectricLogic(Logic):
    def __init__(self) -> None:
        super().__init__()

        class NODES(Logic.NODES()):
            reference = ElectricPower()
            signal = Electrical()

        self.NODEs = NODES(self)

    def connect_to_electric(self, signal: Electrical, reference: ElectricPower):
        self.NODEs.reference.connect(reference)
        self.NODEs.signal.connect(signal)
        return self

    def pull_down(self, resistor):
        from faebryk.library.Resistor import Resistor

        assert isinstance(resistor, Resistor)
        self.NODEs.signal.connect_via(resistor, self.NODEs.reference.NODEs.lv)

    def pull_up(self, resistor):
        from faebryk.library.Resistor import Resistor

        assert isinstance(resistor, Resistor)
        self.NODEs.signal.connect_via(resistor, self.NODEs.reference.NODEs.hv)
