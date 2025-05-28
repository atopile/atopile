# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P  # noqa: F401

logger = logging.getLogger(__name__)


class SK6812(Module):
    """
    RGB digital LED with SK6812 controller

    SMD5050-4P
    RGB LEDs(Built-in IC) ROHS
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    power: F.ElectricPower
    data_in: F.ElectricLogic
    data_out: F.ElectricLogic

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.data_in, self.data_out)

    explicit_part = L.f_field(F.has_explicit_part.by_supplier)("C5378720")
    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.LED
    )

    @L.rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.data_in.line: ["DIN"],
                self.data_out.line: ["DOUT"],
                self.power.lv: ["VSS", "GND"],
                self.power.hv: ["VDD"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )

    def __preinit__(self):
        # ------------------------------------
        #           connections
        # ------------------------------------
        # FIXME
        # self.power.decoupled.decouple()
        F.ElectricLogic.connect_all_module_references(self, gnd_only=True)
        F.ElectricLogic.connect_all_module_references(self, exclude=[self.power])

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        self.power.voltage.constrain_subset(L.Range(3.3 * P.V, 5.5 * P.V))
