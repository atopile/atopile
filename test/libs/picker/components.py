# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.smd import SMDSize
from faebryk.libs.util import assert_once

logger = logging.getLogger(__name__)


@dataclass
class ComponentTestCase[T: fabll.Node]:
    module: Callable[[graph.GraphView, fbrk.TypeGraph], T]
    packages: list[SMDSize] = field(default_factory=list)
    lcsc_id: str | None = None
    mfr_mpn: tuple[str, str] | None = None
    override_test_name: str | None = None
    setup_fn: Callable[[T], Any] | None = None

    @assert_once
    def get_module(self, g: graph.GraphView, tg: fbrk.TypeGraph) -> T:
        module = self.module(g, tg)

        if self.lcsc_id:
            fabll.Traits.create_and_add_instance_to(
                module, F.has_explicit_part
            ).setup_by_supplier(supplier_partno=self.lcsc_id)
            fabll.Traits.create_and_add_instance_to(
                module, F.is_pickable_by_supplier_id
            ).setup(
                supplier_part_id=self.lcsc_id,
                supplier=F.is_pickable_by_supplier_id.Supplier.LCSC,
            )
        elif self.mfr_mpn:
            fabll.Traits.create_and_add_instance_to(
                module, F.has_explicit_part
            ).setup_by_mfr(mfr=self.mfr_mpn[0], partno=self.mfr_mpn[1])
            fabll.Traits.create_and_add_instance_to(
                module, F.is_pickable_by_part_number
            ).setup(manufacturer=self.mfr_mpn[0], partno=self.mfr_mpn[1])

        return module


mfr_parts = [
    ComponentTestCase(
        lambda g, tg: F.OpAmp.bind_typegraph(tg=tg).create_instance(g=g),
        packages=[],  # FIXME: re-add package requirement "SOT-23-5"
        mfr_mpn=("Texas Instruments", "LMV321IDBVR"),
        override_test_name="MFR_TI_LMV321IDBVR",
        setup_fn=lambda r: (
            # bandwidth <= 1MHz
            F.Expressions.LessOrEqual.c(
                left=r.bandwidth.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=r.tg)
                .create_instance(g=r.g)
                .setup_from_singleton(
                    value=1e6,
                    unit=F.Units.Hertz.bind_typegraph(tg=r.tg)
                    .create_instance(g=r.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
            # input_bias_current <= 1nA
            F.Expressions.LessOrEqual.c(
                left=r.input_bias_current.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=r.tg)
                .create_instance(g=r.g)
                .setup_from_singleton(
                    value=1e-9,
                    unit=F.Units.Ampere.bind_typegraph(tg=r.tg)
                    .create_instance(g=r.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
            # input_offset_voltage <= 1mV
            F.Expressions.LessOrEqual.c(
                left=r.input_offset_voltage.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=r.tg)
                .create_instance(g=r.g)
                .setup_from_singleton(
                    value=1e-3,
                    unit=F.Units.Volt.bind_typegraph(tg=r.tg)
                    .create_instance(g=r.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
            # gain_bandwidth_product <= 1MHz
            F.Expressions.LessOrEqual.c(
                left=r.gain_bandwidth_product.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=r.tg)
                .create_instance(g=r.g)
                .setup_from_singleton(
                    value=1e6,
                    unit=F.Units.Hertz.bind_typegraph(tg=r.tg)
                    .create_instance(g=r.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
            # output_current <= 1mA
            F.Expressions.LessOrEqual.c(
                left=r.output_current.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=r.tg)
                .create_instance(g=r.g)
                .setup_from_singleton(
                    value=1e-3,
                    unit=F.Units.Ampere.bind_typegraph(tg=r.tg)
                    .create_instance(g=r.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
            # slew_rate <= 1MV/s
            F.Expressions.LessOrEqual.c(
                left=r.slew_rate.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=r.tg)
                .create_instance(g=r.g)
                .setup_from_singleton(
                    value=1e6,
                    unit=F.Units.VoltsPerSecond.bind_typegraph(tg=r.tg)
                    .create_instance(g=r.g)
                    .get_trait(F.Units.is_unit),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
        ),
    )
]

lcsc_id_parts = [
    ComponentTestCase(
        lambda g, tg: F.OpAmp.bind_typegraph(tg=tg).create_instance(g=g),
        packages=[],  # FIXME: re-add package requirement "SOT-23-5"
        lcsc_id="C7972",
        override_test_name="LCSC_ID_C7972",
        setup_fn=lambda r: (
            # bandwidth <= 1MHz
            F.Expressions.LessOrEqual.c(
                left=r.bandwidth.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=r.tg)
                .create_instance(g=r.g)
                .setup_from_singleton(
                    value=1e6,
                    unit=F.Units.Hertz.bind_typegraph(tg=r.tg)
                    .create_instance(g=r.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
            # input_bias_current <= 1nA
            F.Expressions.LessOrEqual.c(
                left=r.input_bias_current.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=r.tg)
                .create_instance(g=r.g)
                .setup_from_singleton(
                    value=1e-9,
                    unit=F.Units.Ampere.bind_typegraph(tg=r.tg)
                    .create_instance(g=r.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
            # input_offset_voltage <= 1mV
            F.Expressions.LessOrEqual.c(
                left=r.input_offset_voltage.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=r.tg)
                .create_instance(g=r.g)
                .setup_from_singleton(
                    value=1e-3,
                    unit=F.Units.Volt.bind_typegraph(tg=r.tg)
                    .create_instance(g=r.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
            # gain_bandwidth_product <= 1MHz
            F.Expressions.LessOrEqual.c(
                left=r.gain_bandwidth_product.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=r.tg)
                .create_instance(g=r.g)
                .setup_from_singleton(
                    value=1e6,
                    unit=F.Units.Hertz.bind_typegraph(tg=r.tg)
                    .create_instance(g=r.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
            # output_current <= 1mA
            F.Expressions.LessOrEqual.c(
                left=r.output_current.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=r.tg)
                .create_instance(g=r.g)
                .setup_from_singleton(
                    value=1e-3,
                    unit=F.Units.Ampere.bind_typegraph(tg=r.tg)
                    .create_instance(g=r.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
            # slew_rate <= 1MV/s
            F.Expressions.LessOrEqual.c(
                left=r.slew_rate.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=r.tg)
                .create_instance(g=r.g)
                .setup_from_singleton(
                    value=1e6,
                    unit=F.Units.VoltsPerSecond.bind_typegraph(tg=r.tg)
                    .create_instance(g=r.g)
                    .get_trait(F.Units.is_unit),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
        ),
    )
]

resistors = [
    ComponentTestCase(
        lambda g, tg: F.Resistor.bind_typegraph(tg=tg).create_instance(g=g),
        packages=[SMDSize.I0402],
        override_test_name="RESISTOR_I0402",
        setup_fn=lambda r: (
            F.Expressions.IsSubset.c(
                subset=r.resistance.get().can_be_operand.get(),
                superset=F.Literals.Numbers.bind_typegraph(tg=r.tg)
                .create_instance(g=r.g)
                .setup_from_min_max(
                    min=9e3,
                    max=11e3,
                    unit=F.Units.Ohm.bind_typegraph(tg=r.tg)
                    .create_instance(g=r.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
            F.Expressions.GreaterOrEqual.c(
                left=r.max_power.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=r.tg)
                .create_instance(g=r.g)
                .setup_from_singleton(
                    value=0.05,
                    unit=F.Units.Watt.bind_typegraph(tg=r.tg)
                    .create_instance(g=r.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
            F.Expressions.GreaterOrEqual.c(
                left=r.max_voltage.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=r.tg)
                .create_instance(g=r.g)
                .setup_from_singleton(
                    value=25,
                    unit=F.Units.Volt.bind_typegraph(tg=r.tg)
                    .create_instance(g=r.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
        ),
    ),
    ComponentTestCase(
        lambda g, tg: F.Resistor.bind_typegraph(tg=tg).create_instance(g=g),
        packages=[SMDSize.I0603],
        override_test_name="RESISTOR_I0603",
        setup_fn=lambda r: (
            F.Expressions.IsSubset.c(
                subset=r.resistance.get().can_be_operand.get(),
                superset=F.Literals.Numbers.bind_typegraph(tg=r.tg)
                .create_instance(g=r.g)
                .setup_from_min_max(
                    min=67e3,
                    max=71e3,
                    unit=F.Units.Ohm.bind_typegraph(tg=r.tg)
                    .create_instance(g=r.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
            F.Expressions.GreaterOrEqual.c(
                left=r.max_power.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=r.tg)
                .create_instance(g=r.g)
                .setup_from_singleton(
                    value=0.1,
                    unit=F.Units.Watt.bind_typegraph(tg=r.tg)
                    .create_instance(g=r.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
            F.Expressions.GreaterOrEqual.c(
                left=r.max_voltage.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=r.tg)
                .create_instance(g=r.g)
                .setup_from_singleton(
                    value=50,
                    unit=F.Units.Volt.bind_typegraph(tg=r.tg)
                    .create_instance(g=r.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
        ),
    ),
    ComponentTestCase(
        lambda g, tg: F.Resistor.bind_typegraph(tg=tg).create_instance(g=g),
        packages=[SMDSize.I0805],
        override_test_name="RESISTOR_I0805",
        setup_fn=lambda r: (
            F.Expressions.IsSubset.c(
                subset=r.resistance.get().can_be_operand.get(),
                superset=F.Literals.Numbers.bind_typegraph(tg=r.tg)
                .create_instance(g=r.g)
                .setup_from_min_max(
                    min=3e-3 * 0.99,
                    max=3e-3 * 1.01,
                    unit=F.Units.Ohm.bind_typegraph(tg=r.tg)
                    .create_instance(g=r.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
        ),
    ),
]

capacitors = [
    ComponentTestCase(
        lambda g, tg: F.Capacitor.bind_typegraph(tg=tg).create_instance(g=g),
        packages=[SMDSize.I0603],
        override_test_name="CAPACITOR_I0603",
        setup_fn=lambda c: (
            F.Expressions.IsSubset.c(
                subset=c.capacitance.get().can_be_operand.get(),
                superset=F.Literals.Numbers.bind_typegraph(tg=c.tg)
                .create_instance(g=c.g)
                .setup_from_min_max(
                    min=90e-9,
                    max=110e-9,
                    unit=F.Units.Farad.bind_typegraph(tg=c.tg)
                    .create_instance(g=c.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
            F.Expressions.GreaterOrEqual.c(
                left=c.max_voltage.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=c.tg)
                .create_instance(g=c.g)
                .setup_from_singleton(
                    value=25,
                    unit=F.Units.Volt.bind_typegraph(tg=c.tg)
                    .create_instance(g=c.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
            # TODO: temperature_coefficient constraint when EnumParameter works
        ),
    ),
    ComponentTestCase(
        lambda g, tg: F.Capacitor.bind_typegraph(tg=tg).create_instance(g=g),
        packages=[SMDSize.I0402],
        override_test_name="CAPACITOR_I0402",
        setup_fn=lambda c: (
            F.Expressions.IsSubset.c(
                subset=c.capacitance.get().can_be_operand.get(),
                superset=F.Literals.Numbers.bind_typegraph(tg=c.tg)
                .create_instance(g=c.g)
                .setup_from_min_max(
                    min=42.3e-12,
                    max=51.7e-12,
                    unit=F.Units.Farad.bind_typegraph(tg=c.tg)
                    .create_instance(g=c.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
            F.Expressions.GreaterOrEqual.c(
                left=c.max_voltage.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=c.tg)
                .create_instance(g=c.g)
                .setup_from_singleton(
                    value=50,
                    unit=F.Units.Volt.bind_typegraph(tg=c.tg)
                    .create_instance(g=c.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
            # TODO: temperature_coefficient constraint when EnumParameter works
        ),
    ),
]

inductors = [
    ComponentTestCase(
        lambda g, tg: F.Inductor.bind_typegraph(tg=tg).create_instance(g=g),
        packages=[SMDSize.I0603],
        override_test_name="INDUCTOR_I0603",
        setup_fn=lambda i: (
            F.Expressions.IsSubset.c(
                subset=i.inductance.get().can_be_operand.get(),
                superset=F.Literals.Numbers.bind_typegraph(tg=i.tg)
                .create_instance(g=i.g)
                .setup_from_min_max(
                    min=8e-6,
                    max=12e-6,
                    unit=F.Units.Henry.bind_typegraph(tg=i.tg)
                    .create_instance(g=i.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
            # max_current >= 0.05A
            F.Expressions.GreaterOrEqual.c(
                left=i.max_current.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=i.tg)
                .create_instance(g=i.g)
                .setup_from_singleton(
                    value=0.05,
                    unit=F.Units.Ampere.bind_typegraph(tg=i.tg)
                    .create_instance(g=i.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
            # dc_resistance <= 1.17Ω
            F.Expressions.LessOrEqual.c(
                left=i.dc_resistance.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=i.tg)
                .create_instance(g=i.g)
                .setup_from_singleton(
                    value=1.17,
                    unit=F.Units.Ohm.bind_typegraph(tg=i.tg)
                    .create_instance(g=i.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
            # self_resonant_frequency >= 30MHz
            F.Expressions.GreaterOrEqual.c(
                left=i.self_resonant_frequency.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=i.tg)
                .create_instance(g=i.g)
                .setup_from_singleton(
                    value=30e6,
                    unit=F.Units.Hertz.bind_typegraph(tg=i.tg)
                    .create_instance(g=i.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
        ),
    ),
    ComponentTestCase(
        lambda g, tg: F.Inductor.bind_typegraph(tg=tg).create_instance(g=g),
        packages=[SMDSize.I0805],
        override_test_name="INDUCTOR_I0805",
        setup_fn=lambda i: (
            F.Expressions.IsSubset.c(
                subset=i.inductance.get().can_be_operand.get(),
                superset=F.Literals.Numbers.bind_typegraph(tg=i.tg)
                .create_instance(g=i.g)
                .setup_from_min_max(
                    min=24.3e-6,
                    max=29.7e-6,
                    unit=F.Units.Henry.bind_typegraph(tg=i.tg)
                    .create_instance(g=i.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
            # max_current >= 0.06A
            F.Expressions.GreaterOrEqual.c(
                left=i.max_current.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=i.tg)
                .create_instance(g=i.g)
                .setup_from_singleton(
                    value=0.06,
                    unit=F.Units.Ampere.bind_typegraph(tg=i.tg)
                    .create_instance(g=i.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
            # dc_resistance <= 10.7Ω
            F.Expressions.LessOrEqual.c(
                left=i.dc_resistance.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=i.tg)
                .create_instance(g=i.g)
                .setup_from_singleton(
                    value=10.7,
                    unit=F.Units.Ohm.bind_typegraph(tg=i.tg)
                    .create_instance(g=i.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
            # self_resonant_frequency >= 17MHz
            F.Expressions.GreaterOrEqual.c(
                left=i.self_resonant_frequency.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=i.tg)
                .create_instance(g=i.g)
                .setup_from_singleton(
                    value=17e6,
                    unit=F.Units.Hertz.bind_typegraph(tg=i.tg)
                    .create_instance(g=i.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
        ),
    ),
]

mosfets = [
    ComponentTestCase(
        lambda g, tg: F.MOSFET.bind_typegraph(tg=tg).create_instance(g=g),
        packages=[],  # FIXME: re-add package requirement "SOT-23"
        override_test_name="MOSFET_SOT-23",
        setup_fn=lambda m: (
            # TODO: EnumParameter constraints for channel_type, saturation_type
            F.Expressions.IsSubset.c(
                subset=m.gate_source_threshold_voltage.get().can_be_operand.get(),
                superset=F.Literals.Numbers.bind_typegraph(tg=m.tg)
                .create_instance(g=m.g)
                .setup_from_min_max(
                    min=-2.6,
                    max=3.4,
                    unit=F.Units.Volt.bind_typegraph(tg=m.tg)
                    .create_instance(g=m.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
            # max_drain_source_voltage >= 20V
            F.Expressions.GreaterOrEqual.c(
                left=m.max_drain_source_voltage.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=m.tg)
                .create_instance(g=m.g)
                .setup_from_singleton(
                    value=20,
                    unit=F.Units.Volt.bind_typegraph(tg=m.tg)
                    .create_instance(g=m.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
            # max_continuous_drain_current >= 2A
            F.Expressions.GreaterOrEqual.c(
                left=m.max_continuous_drain_current.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=m.tg)
                .create_instance(g=m.g)
                .setup_from_singleton(
                    value=2,
                    unit=F.Units.Ampere.bind_typegraph(tg=m.tg)
                    .create_instance(g=m.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
            # on_resistance <= 0.1Ω
            F.Expressions.LessOrEqual.c(
                left=m.on_resistance.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=m.tg)
                .create_instance(g=m.g)
                .setup_from_singleton(
                    value=0.1,
                    unit=F.Units.Ohm.bind_typegraph(tg=m.tg)
                    .create_instance(g=m.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
        ),
    ),
]

diodes = [
    ComponentTestCase(
        lambda g, tg: F.Diode.bind_typegraph(tg=tg).create_instance(g=g),
        packages=[],  # FIXME: re-add package requirement "SOD-123FL", "SMB"
        override_test_name="DIODE_SOD-123FL",
        setup_fn=lambda d: (
            # current >= 1A
            F.Expressions.GreaterOrEqual.c(
                left=d.current.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=d.tg)
                .create_instance(g=d.g)
                .setup_from_singleton(
                    value=1,
                    unit=F.Units.Ampere.bind_typegraph(tg=d.tg)
                    .create_instance(g=d.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
            # forward_voltage <= 1.7V
            F.Expressions.LessOrEqual.c(
                left=d.forward_voltage.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=d.tg)
                .create_instance(g=d.g)
                .setup_from_singleton(
                    value=1.7,
                    unit=F.Units.Volt.bind_typegraph(tg=d.tg)
                    .create_instance(g=d.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
            # reverse_working_voltage >= 20V
            F.Expressions.GreaterOrEqual.c(
                left=d.reverse_working_voltage.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=d.tg)
                .create_instance(g=d.g)
                .setup_from_singleton(
                    value=20,
                    unit=F.Units.Volt.bind_typegraph(tg=d.tg)
                    .create_instance(g=d.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
            # reverse_leakage_current <= 100µA
            F.Expressions.LessOrEqual.c(
                left=d.reverse_leakage_current.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=d.tg)
                .create_instance(g=d.g)
                .setup_from_singleton(
                    value=100e-6,
                    unit=F.Units.Ampere.bind_typegraph(tg=d.tg)
                    .create_instance(g=d.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
            # max_current >= 1A
            F.Expressions.GreaterOrEqual.c(
                left=d.max_current.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=d.tg)
                .create_instance(g=d.g)
                .setup_from_singleton(
                    value=1,
                    unit=F.Units.Ampere.bind_typegraph(tg=d.tg)
                    .create_instance(g=d.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
        ),
    ),
]

leds = [
    ComponentTestCase(
        lambda g, tg: F.LED.bind_typegraph(tg=tg).create_instance(g=g),
        packages=[],
        override_test_name="LED_RGB",
        setup_fn=lambda led: (
            # TODO: EnumParameter constraints for color
            F.Expressions.GreaterOrEqual.c(
                left=led.max_brightness.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=led.tg)
                .create_instance(g=led.g)
                .setup_from_singleton(
                    value=100e-3,
                    unit=F.Units.Candela.bind_typegraph(tg=led.tg)
                    .create_instance(g=led.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
                assert_=True,
            ),
            F.Expressions.GreaterOrEqual.c(
                left=led.diode.get().max_current.get().can_be_operand.get(),
                right=F.Literals.Numbers.bind_typegraph(tg=led.tg)
                .create_instance(g=led.g)
                .setup_from_singleton(
                    value=20e-3,
                    unit=F.Units.Ampere.bind_typegraph(tg=led.tg)
                    .create_instance(g=led.g)
                    .is_unit.get(),
                )
                .is_literal.get()
                .as_operand.get(),
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
    # No pickers for the following components yet
    # *mosfets,
    # *diodes,
    # *leds,
)
