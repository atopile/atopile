# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.core import Module
from faebryk.libs.units import P
from faebryk.libs.util import times


class SNx4LVC541A(Module):
    """
    The SN54LVC541A octal buffer/driver is designed for
    3.3-V VCC) 2.7-V to 3.6-V VCC operation, and the SN74LVC541A
    octal buffer/driver is designed for 1.65-V to 3.6-V VCC operation.
    """

    def __init__(self):
        super().__init__()

        # ----------------------------------------
        #     modules, interfaces, parameters
        # ----------------------------------------
        class _PARAMs(Module.PARAMS()): ...

        self.PARAMs = _PARAMs(self)

        class _IFs(Module.IFS()):
            A = times(8, F.ElectricLogic)
            Y = times(8, F.ElectricLogic)

            vcc = F.ElectricPower()

            OE = times(2, F.ElectricLogic)

        self.IFs = _IFs(self)

        # ----------------------------------------
        #                traits
        # ----------------------------------------
        self.add_trait(F.has_designator_prefix_defined("U"))
        self.add_trait(
            F.has_datasheet_defined(
                "https://www.ti.com/lit/ds/symlink/sn74lvc541a.pdf?ts=1718881644774&ref_url=https%253A%252F%252Fwww.mouser.ie%252F"
            )
        )

        # ----------------------------------------
        #                parameters
        # ----------------------------------------
        self.IFs.vcc.PARAMs.voltage.merge(F.Range.upper_bound(3.6 * P.V))

        # ----------------------------------------
        #                aliases
        # ----------------------------------------

        # ----------------------------------------
        #                connections
        # ----------------------------------------
        self.IFs.vcc.get_trait(F.can_be_decoupled).decouple()

        # set all electric logic references
        for a, y, oe in zip(self.IFs.A, self.IFs.Y, self.IFs.OE):
            a.connect_reference(self.IFs.vcc)
            y.connect_reference(self.IFs.vcc)
            oe.connect_reference(self.IFs.vcc)
