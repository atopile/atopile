# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P
from faebryk.libs.util import assert_once  # noqa: F401

logger = logging.getLogger(__name__)


class TPS2116(F.PowerMux):
    """
    2 to 1 1.6 V to 5.5 V, 2.5-A Low IQ Power Mux with Manual and Priority Switchover
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    mode: F.ElectricLogic
    status: F.ElectricLogic

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )
    descriptive_properties = L.f_field(F.has_explicit_part.by_mfr)(
        "Texas Instruments", "TPS2116DRLR"
    )
    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://www.ti.com/lit/ds/symlink/tps2116.pdf"
    )

    @L.rt_field
    def can_attach_to_footprint(self):
        return F.can_attach_to_footprint_via_pinmap(
            {
                "1": self.power_out.lv,
                "2": self.power_out.hv,
                "3": self.power_in[0].hv,
                "4": self.select.line,
                "5": self.mode.line,
                "6": self.power_in[1].hv,
                "7": self.power_out.hv,
                "8": self.status.line,
            },
        )

    @L.rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.power_in[0].lv: ["GND"],
                self.mode.line: ["MODE"],
                self.select.line: ["PR1"],
                self.status.line: ["ST"],
                self.power_in[0].hv: ["VIN1"],
                self.power_in[1].hv: ["VIN2"],
                self.power_out.hv: ["VOUT"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )

    def __preinit__(self):
        # ------------------------------------
        #           connections
        # ------------------------------------
        F.ElectricLogic.connect_all_module_references(self, gnd_only=True)
        F.ElectricLogic.connect_all_module_references(
            self, exclude=[self.power_out, self.power_in[1]]
        )

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        for power in [self.power_in[0], self.power_in[1], self.power_out]:
            power.voltage.constrain_subset(L.Range(1.6 * P.V, 5.5 * P.V))
