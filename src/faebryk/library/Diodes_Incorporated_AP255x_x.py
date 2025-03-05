# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.core.parameter import ParameterOperatable
from faebryk.exporters.pcb.layout.extrude import LayoutExtrude
from faebryk.exporters.pcb.layout.heuristic_decoupling import Params
from faebryk.exporters.pcb.layout.next_to import LayoutNextTo
from faebryk.exporters.pcb.layout.typehierarchy import LayoutTypeHierarchy
from faebryk.library.has_pcb_position import has_pcb_position
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P
from faebryk.libs.util import assert_once

logger = logging.getLogger(__name__)


class Diodes_Incorporated_AP255x_x(Module):
    """
    Power Distribution Switch. Mostly used in USB applications.
    - AP2552: Active low enable
    - AP2553: Active high enable
    - 'A' suffix: latch-off during overcurrent
    - No suffix: current limit during overcurrent

    2.7V~5.5V 70mΩ 2.1A SOT-26
    """

    @assert_once
    def set_current_limit(self, current: ParameterOperatable.NumberLike) -> F.Resistor:
        self.current_limit.alias_is(current)

        current_limit_setting_resistor = self.ilim.add(F.Resistor())

        self.ilim.line.connect_via(
            current_limit_setting_resistor, self.ilim.reference.lv
        )  # TODO: bit ugly

        # TODO:
        # Rlim is in Kohm
        # current is in mA
        # Rlim_min = (20.08 / (self.current_limit * P.mA)) ^ (1 / 0.956) * P.kohm
        # Rlim_max = (20.08 / (self.current_limit * P.mA)) ^ (1 / 0.904) * P.kohm

        # Rlim = Range(Rlim_min, Rlim_max)
        # Rlim = 51 * P.kohm  # TODO: remove: ~0.52A typical current limit
        # if not Rlim.is_subset_of(L.Range(10 * P.kohm, 210 * P.kohm)):
        #    raise ModuleException(
        #        self,
        #        f"Rlim must be in the range 10kOhm to 210kOhm but is {Rlim.get_most_narrow()}",  # noqa: E501
        #    )

        # current_limit_setting_resistor.resistance.constrain_subset(Rlim)

        return current_limit_setting_resistor

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    power_in: F.ElectricPower
    power_out: F.ElectricPower
    enable: F.ElectricLogic
    fault: F.ElectricLogic
    ilim: F.ElectricSignal

    current_limit = L.p_field(
        units=P.A,
        likely_constrained=True,
        soft_set=L.Range(100 * P.mA, 2.1 * P.A),
        tolerance_guess=10 * P.percent,
    )
    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )

    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://www.diodes.com/assets/Datasheets/products_inactive_data/AP255x.pdf"
    )

    @L.rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.power_in.hv: ["IN"],
                self.power_in.lv: ["GND"],
                self.enable.line: ["EN/EN#", "EN"],
                self.fault.line: ["FAULT#", "FAULT"],
                self.ilim.line: ["ILIM"],
                self.power_out.hv: ["OUT"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.power_in, self.power_out)

    @L.rt_field
    def has_defined_layout(self):
        # pcb layout
        Point = has_pcb_position.Point
        L = has_pcb_position.layer_type
        LVL = LayoutTypeHierarchy.Level

        layouts = [
            LVL(
                mod_type=F.Resistor,
                layout=LayoutNextTo(
                    self.ilim.line,
                    params=Params(
                        distance_between_pad_edges=1,
                        extra_rotation_of_footprint=90,
                    ),
                ),
            ),
            LVL(
                mod_type=F.Capacitor,
                layout=LayoutExtrude(
                    base=Point((-0.95, 3.25, 270, L.NONE)),
                    vector=(-6.5, 0, 180),
                    dynamic_rotation=True,
                ),
            ),
        ]
        return F.has_pcb_layout_defined(LayoutTypeHierarchy(layouts))

    def __preinit__(self):
        # ------------------------------------
        #           connections
        # ------------------------------------
        F.ElectricLogic.connect_all_module_references(self, gnd_only=True)
        F.ElectricLogic.connect_all_module_references(
            self, exclude={self.power_in, self.power_out, self.ilim}
        )
        # ------------------------------------
        #          parametrization
        # ------------------------------------
