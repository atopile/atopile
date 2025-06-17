# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P  # noqa: F401

logger = logging.getLogger(__name__)


class Wuxi_I_core_Elec_AiP74LVC1T45GB236_TR(Module):
    """
    Single channel bidirectional buffer.
    1.2V-5.5V logic levels.
    SOT-23-6
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    direction: F.ElectricLogic
    port_a: F.ElectricLogic
    power_a: F.ElectricPower
    port_b: F.ElectricLogic
    power_b: F.ElectricPower

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )
    explicit_part = L.f_field(F.has_explicit_part.by_mfr)(
        "Wuxi I-core Elec", "AiP74LVC1T45GB236.TR"
    )

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.port_a, self.port_b)

    @L.rt_field
    def decoupled(self):
        return F.can_be_decoupled_rails(self.power_a, self.power_b)

    @L.rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.port_a.line: ["A"],
                self.port_b.line: ["B"],
                self.direction.line: ["DIR"],
                self.power_a.lv: ["GND"],
                self.power_a.hv: ["VCC(A)"],
                self.power_b.hv: ["VCC(B)"],
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
            self, exclude=[self.power_a, self.port_a, self.direction]
        )
        F.ElectricLogic.connect_all_module_references(
            self, exclude=[self.power_b, self.port_b]
        )

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        self.power_a.voltage.constrain_subset(L.Range(1.2 * P.V, 5.5 * P.V))
        self.power_b.voltage.constrain_subset(L.Range(1.2 * P.V, 5.5 * P.V))

        # FIXME
        # self.power_a.decoupled.decouple().capacitance.constrain_subset(
        #     L.Range.from_center(100 * P.nF, 10 * P.nF)
        # )
        # self.power_b.decoupled.decouple().capacitance.constrain_subset(
        #     L.Range.from_center(100 * P.nF, 10 * P.nF)
        # )
