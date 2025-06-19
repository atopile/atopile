# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P  # noqa: F401

logger = logging.getLogger(__name__)


class PANASONIC_AQY212EHAX(Module):
    """
    PhotoMOS GE 1 Form A(SPST-NO) 1.25V 60V 850mΩ 550mA SOP-4-2.54mm Solid State Relays
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    led: F.LED
    switch = L.f_field(F.Switch(F.Electrical))()

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    explicit_part = L.f_field(F.has_explicit_part.by_supplier)("C29276")
    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )

    @L.rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.led.anode: ["A"],
                self.led.cathode: ["K"],
                self.switch.unnamed[0]: ["S"],
                self.switch.unnamed[1]: ["S1"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )

    def __preinit__(self):
        # ------------------------------------
        #           connections
        # ------------------------------------
        self.led.del_trait(F.is_pickable)
        self.switch.del_trait(F.is_pickable)

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        self.led.max_current.constrain_subset(L.Range(1.2 * P.mA, 3.0 * P.mA))
        self.led.reverse_working_voltage.constrain_subset(L.Range(0 * P.V, 5.0 * P.V))
        self.led.forward_voltage.constrain_subset(L.Range(1.25 * P.V, 2.0 * P.V))
