# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass, field
from typing import Callable

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.smd import SMDSize

logger = logging.getLogger(__name__)

# Graph and TypeGraph setup
_g = graph.GraphView.create()
_tg = fbrk.TypeGraph.create(g=_g)
_literals = F.Literals.BoundLiteralContext(_tg, _g)


@dataclass
class ComponentTestCase:
    module: fabll.Node
    packages: list[SMDSize] = field(default_factory=list)
    lcsc_id: str | None = None
    mfr_mpn: tuple[str, str] | None = None
    override_test_name: str | None = None
    setup_fn: Callable[[fabll.Node], None] | None = None

    def __post_init__(self):
        if self.setup_fn:
            self.setup_fn(self.module)
        if self.lcsc_id:
            fabll.Traits.create_and_add_instance_to(self.module, F.has_explicit_part)
        elif self.mfr_mpn:
            fabll.Traits.create_and_add_instance_to(self.module, F.has_explicit_part)


mfr_parts = [
    ComponentTestCase(
        F.OpAmp.bind_typegraph(tg=_tg).create_instance(g=_g),
        packages=[],  # FIXME: re-add package requirement "SOT-23-5"
        mfr_mpn=("Texas Instruments", "LMV321IDBVR"),
        override_test_name="MFR_TI_LMV321IDBVR",
        setup_fn=lambda r: (
            # bandwidth <= 1MHz
            F.Expressions.LessOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                r.bandwidth.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(1e6, F.Units.Hertz)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            # CMRR >= 50dB
            F.Expressions.GreaterOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                r.common_mode_rejection_ratio.get()
                .get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(50, F.Units.Decibel)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            # input_bias_current <= 1nA
            F.Expressions.LessOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                r.input_bias_current.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(1e-9, F.Units.Ampere)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            # input_offset_voltage <= 1mV
            F.Expressions.LessOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                r.input_offset_voltage.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(1e-3, F.Units.Volt)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            # gain_bandwidth_product <= 1MHz
            F.Expressions.LessOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                r.gain_bandwidth_product.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(1e6, F.Units.Hertz)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            # output_current <= 1mA
            F.Expressions.LessOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                r.output_current.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(1e-3, F.Units.Ampere)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            # slew_rate <= 1MV/s
            F.Expressions.LessOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                r.slew_rate.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(1e6, F.Units.VoltsPerSecond)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
        ),
    )
]

lcsc_id_parts = [
    ComponentTestCase(
        F.OpAmp.bind_typegraph(tg=_tg).create_instance(g=_g),
        packages=[],  # FIXME: re-add package requirement "SOT-23-5"
        lcsc_id="C7972",
        override_test_name="LCSC_ID_C7972",
        setup_fn=lambda r: (
            # bandwidth <= 1MHz
            F.Expressions.LessOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                r.bandwidth.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(1e6, F.Units.Hertz)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            # CMRR >= 50dB
            F.Expressions.GreaterOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                r.common_mode_rejection_ratio.get()
                .get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(50, F.Units.Decibel)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            # input_bias_current <= 1nA
            F.Expressions.LessOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                r.input_bias_current.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(1e-9, F.Units.Ampere)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            # input_offset_voltage <= 1mV
            F.Expressions.LessOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                r.input_offset_voltage.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(1e-3, F.Units.Volt)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            # gain_bandwidth_product <= 1MHz
            F.Expressions.LessOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                r.gain_bandwidth_product.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(1e6, F.Units.Hertz)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            # output_current <= 1mA
            F.Expressions.LessOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                r.output_current.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(1e-3, F.Units.Ampere)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            # slew_rate <= 1MV/s
            F.Expressions.LessOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                r.slew_rate.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(1e6, F.Units.VoltsPerSecond)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
        ),
    )
]

resistors = [
    ComponentTestCase(
        F.Resistor.bind_typegraph(tg=_tg).create_instance(g=_g),
        packages=[SMDSize.I0402],
        setup_fn=lambda r: (
            F.Expressions.IsSubset.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                r.resistance.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_interval(9e3, 11e3, F.Units.Ohm)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            F.Expressions.GreaterOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                r.max_power.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(0.05, F.Units.Watt)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            F.Expressions.GreaterOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                r.max_voltage.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(25, F.Units.Volt)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
        ),
    ),
    ComponentTestCase(
        F.Resistor.bind_typegraph(tg=_tg).create_instance(g=_g),
        packages=[SMDSize.I0603],
        setup_fn=lambda r: (
            F.Expressions.IsSubset.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                r.resistance.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_interval(67e3, 71e3, F.Units.Ohm)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            F.Expressions.GreaterOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                r.max_power.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(0.1, F.Units.Watt)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            F.Expressions.GreaterOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                r.max_voltage.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(50, F.Units.Volt)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
        ),
    ),
    ComponentTestCase(
        F.Resistor.bind_typegraph(tg=_tg).create_instance(g=_g),
        packages=[SMDSize.I0805],
        setup_fn=lambda r: (
            F.Expressions.IsSubset.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                r.resistance.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_interval(
                    3e-3 * 0.99, 3e-3 * 1.01, F.Units.Ohm
                ).get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
        ),
    ),
]

capacitors = [
    ComponentTestCase(
        F.Capacitor.bind_typegraph(tg=_tg).create_instance(g=_g),
        packages=[SMDSize.I0603],
        setup_fn=lambda c: (
            F.Expressions.IsSubset.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                c.capacitance.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_interval(90e-9, 110e-9, F.Units.Farad)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            F.Expressions.GreaterOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                c.max_voltage.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(25, F.Units.Volt)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            # TODO: temperature_coefficient constraint when EnumParameter works
        ),
    ),
    ComponentTestCase(
        F.Capacitor.bind_typegraph(tg=_tg).create_instance(g=_g),
        packages=[SMDSize.I0402],
        setup_fn=lambda c: (
            F.Expressions.IsSubset.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                c.capacitance.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_interval(
                    42.3e-12, 51.7e-12, F.Units.Farad
                ).get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            F.Expressions.GreaterOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                c.max_voltage.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(50, F.Units.Volt)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            # TODO: temperature_coefficient constraint when EnumParameter works
        ),
    ),
]

inductors = [
    ComponentTestCase(
        F.Inductor.bind_typegraph(tg=_tg).create_instance(g=_g),
        packages=[SMDSize.I0603],
        setup_fn=lambda i: (
            F.Expressions.IsSubset.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                i.inductance.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_interval(8e-6, 12e-6, F.Units.Henry)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            # max_current >= 0.05A
            F.Expressions.GreaterOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                i.max_current.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(0.05, F.Units.Ampere)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            # dc_resistance <= 1.17Ω
            F.Expressions.LessOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                i.dc_resistance.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(1.17, F.Units.Ohm)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            # self_resonant_frequency >= 30MHz
            F.Expressions.GreaterOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                i.self_resonant_frequency.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(30e6, F.Units.Hertz)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
        ),
    ),
    ComponentTestCase(
        F.Inductor.bind_typegraph(tg=_tg).create_instance(g=_g),
        packages=[SMDSize.I0805],
        setup_fn=lambda i: (
            F.Expressions.IsSubset.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                i.inductance.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_interval(24.3e-6, 29.7e-6, F.Units.Henry)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            # max_current >= 0.06A
            F.Expressions.GreaterOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                i.max_current.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(0.06, F.Units.Ampere)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            # dc_resistance <= 10.7Ω
            F.Expressions.LessOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                i.dc_resistance.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(10.7, F.Units.Ohm)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            # self_resonant_frequency >= 17MHz
            F.Expressions.GreaterOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                i.self_resonant_frequency.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(17e6, F.Units.Hertz)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
        ),
    ),
]

mosfets = [
    ComponentTestCase(
        F.MOSFET.bind_typegraph(tg=_tg).create_instance(g=_g),
        packages=[],  # FIXME: re-add package requirement "SOT-23"
        setup_fn=lambda m: (
            # TODO: EnumParameter constraints for channel_type, saturation_type
            F.Expressions.IsSubset.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                m.gate_source_threshold_voltage.get()
                .get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_interval(-2.6, 3.4, F.Units.Volt)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            # max_drain_source_voltage >= 20V
            F.Expressions.GreaterOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                m.max_drain_source_voltage.get()
                .get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(20, F.Units.Volt)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            # max_continuous_drain_current >= 2A
            F.Expressions.GreaterOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                m.max_continuous_drain_current.get()
                .get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(2, F.Units.Ampere)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            # on_resistance <= 0.1Ω
            F.Expressions.LessOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                m.on_resistance.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(0.1, F.Units.Ohm)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
        ),
    ),
]

diodes = [
    ComponentTestCase(
        F.Diode.bind_typegraph(tg=_tg).create_instance(g=_g),
        packages=[],  # FIXME: re-add package requirement "SOD-123FL", "SMB"
        setup_fn=lambda d: (
            # current >= 1A
            F.Expressions.GreaterOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                d.current.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(1, F.Units.Ampere)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            # forward_voltage <= 1.7V
            F.Expressions.LessOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                d.forward_voltage.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(1.7, F.Units.Volt)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            # reverse_working_voltage >= 20V
            F.Expressions.GreaterOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                d.reverse_working_voltage.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(20, F.Units.Volt)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            # reverse_leakage_current <= 100µA
            F.Expressions.LessOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                d.reverse_leakage_current.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(100e-6, F.Units.Ampere)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            # max_current >= 1A
            F.Expressions.GreaterOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                d.max_current.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(1, F.Units.Ampere)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
        ),
    ),
]

leds = [
    ComponentTestCase(
        F.LED.bind_typegraph(tg=_tg).create_instance(g=_g),
        packages=[],
        setup_fn=lambda led: (
            # TODO: EnumParameter constraints for color
            F.Expressions.GreaterOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                led.max_brightness.get().get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(100e-3, F.Units.Candela)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
            F.Expressions.GreaterOrEqual.bind_typegraph(tg=_tg)
            .create_instance(g=_g)
            .setup(
                led.diode.get()
                .max_current.get()
                .get_trait(F.Parameters.can_be_operand),
                _literals.Numbers.setup_from_singleton(20e-3, F.Units.Ampere)
                .get_trait(F.Parameters.can_be_operand),
                assert_=True,
            ),
        ),
    ),
]

components_to_test = (
    *mfr_parts,
    *lcsc_id_parts,
    *resistors,
    *capacitors,
    *inductors,
    *mosfets,
    *diodes,
    *leds,
)
