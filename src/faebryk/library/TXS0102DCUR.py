# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.library.can_be_decoupled import can_be_decoupled
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_datasheet_defined import has_datasheet_defined
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.has_single_electric_reference_defined import (
    has_single_electric_reference_defined,
)
from faebryk.libs.util import times


class TXS0102DCUR(Module):
    """
    TXS0102 2-Bit Bidirectional Voltage-Level Translator for
    Open-Drain and Push-Pull Applications
    """

    class _BidirectionalLevelShifter(Module):
        def __init__(self) -> None:
            super().__init__()

            # interfaces
            class _IFs(Module.IFS()):
                io_a = ElectricLogic()
                io_b = ElectricLogic()

            self.IFs = _IFs(self)

            # TODO: bridge shallow
            # self.add_trait(can_bridge_defined(self.IFs.io_a, self.IFs.io_b))

    def __init__(self) -> None:
        super().__init__()

        # interfaces
        class _IFs(Module.IFS()):
            voltage_a_power = ElectricPower()
            voltage_b_power = ElectricPower()
            n_oe = ElectricLogic()

        self.IFs = _IFs(self)

        class _NODEs(Module.NODES()):
            shifters = times(2, self._BidirectionalLevelShifter)

        self.NODEs = _NODEs(self)

        class _PARAMs(Module.PARAMS()): ...

        self.PARAMs = _PARAMs(self)

        gnd = self.IFs.voltage_a_power.IFs.lv
        gnd.connect(self.IFs.voltage_b_power.IFs.lv)

        self.IFs.voltage_a_power.get_trait(can_be_decoupled).decouple()
        self.IFs.voltage_b_power.get_trait(can_be_decoupled).decouple()

        # eo is referenced to voltage_a_power (active high)
        self.IFs.n_oe.connect_reference(self.IFs.voltage_a_power)

        for shifter in self.NODEs.shifters:
            side_a = shifter.IFs.io_a
            # side_a.IFs.reference.connect(self.IFs.voltage_a_power)
            side_a.add_trait(
                has_single_electric_reference_defined(self.IFs.voltage_a_power)
            )
            side_b = shifter.IFs.io_b
            # side_b.IFs.reference.connect(self.IFs.voltage_b_power)
            side_b.add_trait(
                has_single_electric_reference_defined(self.IFs.voltage_b_power)
            )

        self.add_trait(has_designator_prefix_defined("U"))

        self.add_trait(
            has_datasheet_defined(
                "https://datasheet.lcsc.com/lcsc/1810292010_Texas-Instruments-TXS0102DCUR_C53434.pdf"
            )
        )
