# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L


class TXS0102DCUR(Module):
    """
    TXS0102 2-Bit Bidirectional Voltage-Level Translator for
    Open-Drain and Push-Pull Applications
    """

    class _BidirectionalLevelShifter(Module):
        # interfaces
        io_a: F.ElectricLogic
        io_b: F.ElectricLogic

        # TODO: bridge shallow

        @L.rt_field
        def can_bridge(self):
            return F.can_bridge_defined(self.io_a, self.io_b)

        # interfaces

    voltage_a_power: F.ElectricPower
    voltage_b_power: F.ElectricPower
    n_oe: F.ElectricLogic

    shifters = L.list_field(2, _BidirectionalLevelShifter)

    def __preinit__(self):
        gnd = self.voltage_a_power.lv
        gnd.connect(self.voltage_b_power.lv)

        # FIXME
        # self.voltage_a_power.decoupled.decouple()
        # self.voltage_b_power.decoupled.decouple()

        # eo is referenced to voltage_a_power (active high)
        self.n_oe.reference.connect(self.voltage_a_power)

        for shifter in self.shifters:
            side_a = shifter.io_a
            # side_a.reference.connect(self.voltage_a_power)
            side_a.add(F.has_single_electric_reference_defined(self.voltage_a_power))
            side_b = shifter.io_b
            # side_b.reference.connect(self.voltage_b_power)
            side_b.add(F.has_single_electric_reference_defined(self.voltage_b_power))

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )
    explicit_part = L.f_field(F.has_explicit_part.by_supplier)("C53434")

    @L.rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.voltage_a_power.lv: ["GND"],
                self.voltage_a_power.hv: ["VCCA"],
                self.voltage_b_power.hv: ["VCCB"],
                self.n_oe.line: ["OE"],
                self.shifters[0].io_a.line: ["A1"],
                self.shifters[0].io_b.line: ["B1"],
                self.shifters[1].io_a.line: ["A2"],
                self.shifters[1].io_b.line: ["B2"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )
