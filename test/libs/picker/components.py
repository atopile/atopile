# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.brightness import TypicalLuminousIntensity
from faebryk.libs.library import L
from faebryk.libs.smd import SMDSize
from faebryk.libs.units import P, quantity

logger = logging.getLogger(__name__)


@dataclass
class ComponentTestCase:
    module: Module
    packages: list[SMDSize]
    lcsc_id: str | None = None
    mfr_mpn: tuple[str, str] | None = None
    override_test_name: str | None = None

    def __post_init__(self):
        if self.lcsc_id:
            self.module.add(F.has_explicit_part.by_supplier(self.lcsc_id))
        elif self.mfr_mpn:
            self.module.add(F.has_explicit_part.by_mfr(*self.mfr_mpn))


mfr_parts = [
    ComponentTestCase(
        F.OpAmp().builder(
            lambda r: (
                r.bandwidth.constrain_le(1 * P.Mhertz),
                r.common_mode_rejection_ratio.constrain_ge(quantity(50, P.dB)),
                r.input_bias_current.constrain_le(1 * P.nA),
                r.input_offset_voltage.constrain_le(1 * P.mV),
                r.gain_bandwidth_product.constrain_le(1 * P.Mhertz),
                r.output_current.constrain_le(1 * P.mA),
                r.slew_rate.constrain_le(1 * P.MV / P.us),
            )
        ),
        packages=[],  # FIXME: re-add package requirement"SOT-23-5"
        mfr_mpn=("Texas Instruments", "LMV321IDBVR"),
        override_test_name="MFR_TI_LMV321IDBVR",
    )
]

lcsc_id_parts = [
    ComponentTestCase(
        F.OpAmp().builder(
            lambda r: (
                r.bandwidth.constrain_le(1 * P.Mhertz),
                r.common_mode_rejection_ratio.constrain_ge(quantity(50, P.dB)),
                r.input_bias_current.constrain_le(1 * P.nA),
                r.input_offset_voltage.constrain_le(1 * P.mV),
                r.gain_bandwidth_product.constrain_le(1 * P.Mhertz),
                r.output_current.constrain_le(1 * P.mA),
                r.slew_rate.constrain_le(1 * P.MV / P.us),
            )
        ),
        packages=[],  # FIXME: re-add package requirement"SOT-23-5"
        lcsc_id="C7972",
        override_test_name="LCSC_ID_C7972",
    )
]

resistors = [
    ComponentTestCase(
        F.Resistor().builder(
            lambda r: (
                r.resistance.constrain_subset(
                    L.Range.from_center(10 * P.kohm, 1 * P.kohm)
                ),
                r.max_power.constrain_ge(0.05 * P.W),
                r.max_voltage.constrain_ge(25 * P.V),
            )
        ),
        packages=[SMDSize.I0402],
    ),
    ComponentTestCase(
        F.Resistor().builder(
            lambda r: (
                r.resistance.constrain_subset(
                    L.Range.from_center(69 * P.kohm, 2 * P.kohm)
                ),
                r.max_power.constrain_ge(0.1 * P.W),
                r.max_voltage.constrain_ge(50 * P.V),
            )
        ),
        packages=[SMDSize.I0603],
    ),
    ComponentTestCase(
        F.Resistor().builder(
            lambda r: (
                r.resistance.constrain_subset(
                    L.Range.from_center_rel(3 * P.mohm, 0.01)
                ),
            )
        ),
        packages=[SMDSize.I0805],
    ),
]

capacitors = [
    ComponentTestCase(
        F.Capacitor().builder(
            lambda c: (
                c.capacitance.constrain_subset(
                    L.Range.from_center(100 * P.nF, 10 * P.nF)
                ),
                c.max_voltage.constrain_ge(25 * P.V),
                c.temperature_coefficient.constrain_subset(
                    F.Capacitor.TemperatureCoefficient.X7R
                ),
            )
        ),
        packages=[SMDSize.I0603],
    ),
    ComponentTestCase(
        F.Capacitor().builder(
            lambda c: (
                c.capacitance.constrain_subset(
                    L.Range.from_center(47 * P.pF, 4.7 * P.pF)
                ),
                c.max_voltage.constrain_ge(50 * P.V),
                c.temperature_coefficient.constrain_subset(
                    F.Capacitor.TemperatureCoefficient.C0G
                ),
            )
        ),
        packages=[SMDSize.I0402],
    ),
]

inductors = [
    ComponentTestCase(
        F.Inductor().builder(
            lambda i: (
                i.inductance.constrain_subset(L.Range.from_center(10 * P.uH, 2 * P.uH)),
                i.max_current.constrain_ge(0.05 * P.A),
                i.dc_resistance.constrain_le(1.17 * P.ohm),
                i.self_resonant_frequency.constrain_ge(30 * P.Mhertz),
            )
        ),
        packages=[SMDSize.I0603],
    ),
    ComponentTestCase(
        F.Inductor().builder(
            lambda i: (
                i.inductance.constrain_subset(
                    L.Range.from_center(27 * P.uH, 2.7 * P.uH)
                ),
                i.max_current.constrain_ge(0.06 * P.A),
                i.dc_resistance.constrain_le(10.7 * P.ohm),
                i.self_resonant_frequency.constrain_ge(17 * P.Mhertz),
            )
        ),
        packages=[SMDSize.I0805],
    ),
]

mosfets = [
    ComponentTestCase(
        F.MOSFET().builder(
            lambda m: (
                m.channel_type.constrain_subset(F.MOSFET.ChannelType.N_CHANNEL),
                m.saturation_type.constrain_subset(F.MOSFET.SaturationType.ENHANCEMENT),
                m.gate_source_threshold_voltage.constrain_subset(
                    L.Range.from_center(0.4 * P.V, 3 * P.V)
                ),
                m.max_drain_source_voltage.constrain_ge(20 * P.V),
                m.max_continuous_drain_current.constrain_ge(2 * P.A),
                m.on_resistance.constrain_le(0.1 * P.ohm),
            )
        ),
        packages=[],  # FIXME: re-add package requirement "SOT-23"
    ),
]

diodes = [
    ComponentTestCase(
        F.Diode().builder(
            lambda d: (
                d.current.constrain_ge(1 * P.A),
                d.forward_voltage.constrain_le(1.7 * P.V),
                d.reverse_working_voltage.constrain_ge(20 * P.V),
                d.reverse_leakage_current.constrain_le(100 * P.uA),
                d.max_current.constrain_ge(1 * P.A),
            )
        ),
        packages=[],  # FIXME: re-add package requirement "SOD-123FL", "SMB"
    ),
]

leds = [
    ComponentTestCase(
        F.LED().builder(
            lambda led: (
                led.color.constrain_subset(F.LED.Color.RED),
                led.brightness.constrain_ge(
                    TypicalLuminousIntensity.APPLICATION_LED_INDICATOR_INSIDE.value
                ),
                # led.reverse_leakage_current.constrain_le(100 * P.uA),
                # led.reverse_working_voltage.constrain_ge(20 * P.V),
                led.max_brightness.constrain_ge(100 * P.millicandela),
                # led.forward_voltage.constrain_le(2.5 * P.V),
                led.max_current.constrain_ge(20 * P.mA),
            )
        ),
        packages=[],
    ),
]

tvs = [
    ComponentTestCase(
        F.TVS().builder(
            lambda t: (
                # t.current.constrain_ge(10 * P.A),
                # t.forward_voltage.constrain_le(1.7 * P.V),
                t.reverse_working_voltage.constrain_ge(5 * P.V),
                # t.reverse_leakage_current.constrain_le(100 * P.uA),
                t.max_current.constrain_ge(10 * P.A),
                t.reverse_breakdown_voltage.constrain_le(8 * P.V),
            )
        ),
        # FIXME: re-add package requirement
        # "SOD-123", "SOD-123FL", "SOT-23-6", "SMA", "SMB", "SMC"
        packages=[],
    ),
]

ldos = [
    ComponentTestCase(
        F.LDO().builder(
            lambda u: (
                u.output_voltage.constrain_superset(L.Single(2.8 * P.V)),
                u.output_current.constrain_ge(0.1 * P.A),
                u.power_in.voltage.constrain_ge(5 * P.V),
                u.dropout_voltage.constrain_le(1 * P.V),
                u.output_polarity.constrain_subset(F.LDO.OutputPolarity.POSITIVE),
                u.output_type.constrain_subset(F.LDO.OutputType.FIXED),
                # u.ripple_rejection_ratio,
                # u.quiescent_current,
            )
        ),
        # FIXME: re-add package requirement
        # "SOT-23", "SOT-23-5", "SOT23", "SOT-23-3", "SOT-23-3L"
        packages=[],
    ),
]

components_to_test = (
    *mfr_parts,
    *lcsc_id_parts,
    *resistors,
    *capacitors,
    *inductors,
    # *mosfets,
    # *diodes,
    # *leds,
    # *tvs,
    # *ldos,
)
