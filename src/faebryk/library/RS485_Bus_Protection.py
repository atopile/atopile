# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class RS485_Bus_Protection(Module):
    """
    RS485 bus protection.
    - Overvoltage protection
    - Overcurrent protection
    - Common mode filter
    - Termination resistor
    - ESD protection
    - Lightning protection

    based on: https://www.mornsun-power.com/public/uploads/pdf/TD(H)541S485H.pdf
    """

    def __init__(self, termination: bool = True, polarization: bool = True) -> None:
        super().__init__()
        self._termination = termination
        self._polarization = polarization

    current_limmiter_resistors = L.list_field(2, F.Resistor)
    gdt: F.GDT
    rs485_tvs: F.ElecSuper_PSM712_ES
    gnd_couple_resistor: F.Resistor
    gnd_couple_capacitor: F.Capacitor
    common_mode_filter: F.Common_Mode_Filter

    power: F.ElectricPower
    rs485_unprotected: F.RS485HalfDuplex
    rs485_protected: F.RS485HalfDuplex
    earth: F.Electrical

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.rs485_unprotected, self.rs485_protected)

    def __preinit__(self):
        # alias
        gnd = self.power.lv

        if self._termination:
            termination_resistor = self.add(F.Resistor(), name="termination_resistor")
            termination_resistor.resistance.constrain_subset(
                L.Range.from_center_rel(120 * P.ohm, 0.05)
            )
            self.rs485_unprotected.diff_pair.p.line.connect_via(
                termination_resistor, self.rs485_unprotected.diff_pair.n.line
            )
        if self._polarization:
            polarization_resistors = self.add_to_container(2, F.Resistor)

            polarization_resistors[0].resistance.constrain_subset(
                L.Range(380 * P.ohm, 420 * P.ohm)
            )
            polarization_resistors[1].resistance.constrain_subset(
                L.Range(380 * P.ohm, 420 * P.ohm)
            )
            self.rs485_protected.diff_pair.p.line.connect_via(
                polarization_resistors[0], self.power.hv
            )
            self.rs485_protected.diff_pair.n.line.connect_via(
                polarization_resistors[1], gnd
            )

        # ----------------------------------------
        #            parametrization
        # ----------------------------------------
        self.current_limmiter_resistors[0].resistance.constrain_subset(
            L.Range.from_center_rel(2.7 * P.ohm, 0.05)
        )
        self.current_limmiter_resistors[0].max_power.constrain_ge(500 * P.mW)
        self.current_limmiter_resistors[1].resistance.constrain_subset(
            L.Range.from_center_rel(2.7 * P.ohm, 0.05)
        )
        self.current_limmiter_resistors[1].max_power.constrain_ge(500 * P.mW)

        self.gnd_couple_resistor.resistance.constrain_subset(
            L.Range.from_center_rel(1 * P.Mohm, 0.05)
        )
        # self.gnd_couple_capacitor.capacitance.constrain_subset(
        #     L.Range.from_center_rel(1 * P.uF, 0.1)
        # )
        # self.gnd_couple_capacitor.max_voltage.constrain_ge(2 * P.kV)
        # TODO: fix, dynamic pick, not by pn
        self.gnd_couple_capacitor.add(F.has_explicit_part.by_supplier("C106126"))
        self.gdt.add(
            F.has_explicit_part.by_supplier(
                "C78322",
                pinmap={
                    "1": self.gdt.tube_1,
                    "2": self.gdt.common,
                    "3": self.gdt.tube_2,
                },
            )
        )
        # TODO: fix, dynamic pick, not by pn
        self.gnd_couple_resistor.add(F.has_explicit_part.by_supplier("C1513439"))
        self.common_mode_filter.add(
            F.has_explicit_part.by_supplier(
                "C76577",
                pinmap={
                    "1": self.common_mode_filter.coil_b.unnamed[1],
                    "2": self.common_mode_filter.coil_a.unnamed[1],
                    "3": self.common_mode_filter.coil_b.unnamed[0],
                    "4": self.common_mode_filter.coil_a.unnamed[0],
                },
            )
        )

        # ----------------------------------------
        #               Connections
        # ----------------------------------------
        # rs485_in/out connections
        self.rs485_protected.diff_pair.n.line.connect_via(
            [self.common_mode_filter.coil_a, self.current_limmiter_resistors[0]],
            self.rs485_unprotected.diff_pair.n.line,
        )
        self.rs485_protected.diff_pair.p.line.connect_via(
            [self.common_mode_filter.coil_b, self.current_limmiter_resistors[1]],
            self.rs485_unprotected.diff_pair.p.line,
        )

        # gdt connections
        self.rs485_unprotected.diff_pair.p.line.connect(self.gdt.tube_1)
        self.rs485_unprotected.diff_pair.n.line.connect(self.gdt.tube_2)

        # earth connections
        gnd.connect_via(self.gnd_couple_resistor, self.earth)
        gnd.connect_via(self.gnd_couple_capacitor, self.earth)
        self.gdt.common.connect(self.earth)

        # tvs connections
        self.current_limmiter_resistors[0].p1.connect(
            self.rs485_tvs.rs485.diff_pair.p.line
        )
        self.current_limmiter_resistors[1].p1.connect(
            self.rs485_tvs.rs485.diff_pair.n.line
        )
        self.rs485_tvs.rs485.diff_pair.n.reference.lv.connect(gnd)
