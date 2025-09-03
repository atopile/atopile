# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P, quantity
from faebryk.libs.util import assert_once


class LDO(Module):
    @assert_once
    def enable_output(self):
        self.enable.set(True)

    class OutputType(Enum):
        FIXED = auto()
        ADJUSTABLE = auto()

    class OutputPolarity(Enum):
        POSITIVE = auto()
        NEGATIVE = auto()

    max_input_voltage = L.p_field(
        units=P.V,
        likely_constrained=True,
        soft_set=L.Range(1 * P.V, 100 * P.V),
    )
    output_voltage = L.p_field(
        units=P.V,
        likely_constrained=True,
        soft_set=L.Range(1 * P.V, 100 * P.V),
    )
    quiescent_current = L.p_field(
        units=P.A,
        likely_constrained=True,
        soft_set=L.Range(1 * P.mA, 100 * P.mA),
    )
    dropout_voltage = L.p_field(
        units=P.V,
        likely_constrained=True,
        soft_set=L.Range(1 * P.mV, 100 * P.mV),
    )
    ripple_rejection_ratio = L.p_field(
        units=P.dB,
        likely_constrained=True,
        soft_set=L.Range(quantity(1, P.dB), quantity(100, P.dB)),
    )
    output_polarity = L.p_field(
        domain=L.Domains.ENUM(OutputPolarity),
    )
    output_type = L.p_field(
        domain=L.Domains.ENUM(OutputType),
    )
    output_current = L.p_field(
        units=P.A,
        likely_constrained=True,
        soft_set=L.Range(1 * P.mA, 100 * P.mA),
    )
    enable: F.EnablePin
    power_in: F.ElectricPower
    power_out = L.d_field(lambda: F.ElectricPower().make_source())

    # @L.rt_field
    # def pickable(self) -> F.is_pickable_by_type:
    #     return F.is_pickable_by_type(
    #         F.is_pickable_by_type.Type.LDO,
    #         {
    #             "max_input_voltage": self.max_input_voltage,
    #             "output_voltage": self.output_voltage,
    #             "quiescent_current": self.quiescent_current,
    #             "dropout_voltage": self.dropout_voltage,
    #             # TODO: add support in backend
    #             # "ripple_rejection_ratio": self.ripple_rejection_ratio,
    #             "output_polarity": self.output_polarity,
    #             "output_type": self.output_type,
    #             "output_current": self.output_current,
    #         },
    #     )

    def __preinit__(self):
        self.max_input_voltage.constrain_ge(self.power_in.voltage)
        self.power_out.voltage.constrain_subset(self.output_voltage)

        self.enable.enable.reference.connect(self.power_in)
        # TODO: should be implemented differently (see below)
        # if self.output_polarity == self.OutputPolarity.NEGATIVE:
        #    self.power_in.hv.connect(self.power_out.hv)
        # else:
        #    self.power_in.lv.connect(self.power_out.lv)

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self, gnd_only=True)
        )

    @L.rt_field
    def decoupled(self):
        return F.can_be_decoupled_rails(self.power_in, self.power_out)

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.power_in, self.power_out)

    @L.rt_field
    def simple_value_representation(self):
        S = F.has_simple_value_representation_based_on_params_chain.Spec
        return F.has_simple_value_representation_based_on_params_chain(
            S(self.output_voltage, tolerance=True),
            S(self.output_current),
            S(self.ripple_rejection_ratio),
            S(self.dropout_voltage),
            S(self.max_input_voltage, prefix="Vin max"),
            S(self.quiescent_current, prefix="Iq"),
            prefix="LDO",
        )

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )

    @L.rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.power_in.hv: ["Vin", "Vi", "in"],
                self.power_out.hv: ["Vout", "Vo", "out", "output"],
                self.power_in.lv: ["GND", "V-", "ADJ/GND"],
                self.enable.enable.line: ["EN", "Enable"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import LDO, ElectricPower, Capacitor

        ldo = new LDO
        ldo.output_voltage = 3.3V +/- 2%
        ldo.max_input_voltage = 6V
        ldo.max_current = 1A
        ldo.dropout_voltage = 300mV +/- 50%
        ldo.output_type = LDO.OutputType.FIXED
        ldo.package = "SOT-223"

        # Connect input power (typically 5V)
        power_5v = new ElectricPower
        assert power_5v.voltage within 5V +/- 5%
        ldo.power_in ~ power_5v

        # Connect output power (regulated 3.3V)
        power_3v3 = new ElectricPower
        ldo.power_out ~ power_3v3

        # Enable the LDO
        ldo.enable_output()

        # Add input and output capacitors
        input_cap = new Capacitor
        output_cap = new Capacitor
        input_cap.capacitance = 1uF +/- 20%
        output_cap.capacitance = 10uF +/- 20%
        ldo.power_in.hv ~> input_cap ~> ldo.power_in.lv
        ldo.power_out.hv ~> output_cap ~> ldo.power_out.lv
        """,
        language=F.has_usage_example.Language.ato,
    )
