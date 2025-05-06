# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P


class SNx4LVC541A(Module):
    """
    The SN54LVC541A octal buffer/driver is designed for
    3.3-V VCC) 2.7-V to 3.6-V VCC operation, and the SN74LVC541A
    octal buffer/driver is designed for 1.65-V to 3.6-V VCC operation.
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    A = L.list_field(8, F.ElectricLogic)
    Y = L.list_field(8, F.ElectricLogic)

    power: F.ElectricPower

    output_enable = L.list_field(2, F.ElectricLogic)

    # ----------------------------------------
    #                traits
    # ----------------------------------------
    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )

    @L.rt_field
    def decoupled(self):
        return F.can_be_decoupled_rails(self.power)

    def __preinit__(self):
        # ----------------------------------------
        #                parameters
        # ----------------------------------------
        self.power.voltage.constrain_le(3.6 * P.V)

        # ----------------------------------------
        #                aliases
        # ----------------------------------------

        # ----------------------------------------
        #                connections
        # ----------------------------------------

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self, gnd_only=True)
        )
