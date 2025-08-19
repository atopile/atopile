# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from enum import StrEnum, auto

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.parameter import EnumDomain
from faebryk.libs.library import L
from faebryk.libs.units import P


class Inductor(Module):
    class Package(StrEnum):
        L01005 = auto()
        L0201 = auto()
        L0402 = auto()
        L0603 = auto()
        L0805 = auto()
        L1206 = auto()
        L1210 = auto()
        L1808 = auto()
        L1812 = auto()
        L1825 = auto()
        L2220 = auto()
        L2225 = auto()
        L3640 = auto()

        SMD4x4mm = "SMD,4x4mm"
        SMD6x6mm = "SMD,6x6mm"
        SMD5x5mm = "SMD,5x5mm"
        SMD3x3mm = "SMD,3x3mm"
        SMD8x8mm = "SMD,8x8mm"
        SMD12x12mm = "SMD,12x12mm"
        SMD12_5x12_5mm = "SMD,12.5x12.5mm"
        SMD7_8x7mm = "SMD,7.8x7mm"
        SMD4_5x4mm = "SMD,4.5x4mm"
        SMD11_5x10mm = "SMD,11.5x10mm"
        SMD6_6x7mm = "SMD,6.6x7mm"
        SMD7x6_6mm = "SMD,7x6.6mm"
        SMD5_8x5_2mm = "SMD,5.8x5.2mm"
        SMD6_6x7_3mm = "SMD,6.6x7.3mm"
        SMD3_5x3mm = "SMD,3.5x3mm"
        SMD7_3x7_3mm = "SMD,7.3x7.3mm"
        SMD6_6x7_1mm = "SMD,6.6x7.1mm"
        SMD7x7mm = "SMD,7x7mm"
        SMD5_4x5_2mm = "SMD,5.4x5.2mm"
        SMD6_7x6_7mm = "SMD,6.7x6.7mm"
        SMD11x10mm = "SMD,11x10mm"
        SMD10x11mm = "SMD,10x11mm"
        SMD5_2x5_8mm = "SMD,5.2x5.8mm"
        SMD4_4x4_2mm = "SMD,4.4x4.2mm"
        SMD13_8x12_6mm = "SMD,13.8x12.6mm"
        SMD10_1x10_1mm = "SMD,10.1x10.1mm"
        SMD13_5x12_6mm = "SMD,13.5x12.6mm"
        SMD4_7x4_7mm = "SMD,4.7x4.7mm"
        SMD12_3x12_3mm = "SMD,12.3x12.3mm"
        SMD12_6x13_5mm = "SMD,12.6x13.5mm"
        SMD2_8x2_9mm = "SMD,2.8x2.9mm"
        SMD7_3x6_6mm = "SMD,7.3x6.6mm"
        SMD2_5x2mm = "SMD,2.5x2mm"
        SMD4_9x4_9mm = "SMD,4.9x4.9mm"
        SMD10_2x10mm = "SMD,10.2x10mm"
        SMD7_1x6_6mm = "SMD,7.1x6.6mm"
        SMD10x10mm = "SMD,10x10mm"
        SMD5_7x5_7mm = "SMD,5.7x5.7mm"
        SMD4_1x4_1mm = "SMD,4.1x4.1mm"
        SMD4_1x4_5mm = "SMD,4.1x4.5mm"
        SMD7x7_8mm = "SMD,7x7.8mm"
        SMD10x9mm = "SMD,10x9mm"
        SMD0_6x1_2mm = "SMD,0.6x1.2mm"
        SMD6_5x6_9mm = "SMD,6.5x6.9mm"
        SMD1_6x2mm = "SMD,1.6x2mm"
        SMD2x2_5mm = "SMD,2x2.5mm"
        SMD7_1x6_5mm = "SMD,7.1x6.5mm"
        SMD8x8_5mm = "SMD,8x8.5mm"
        SMD4_5x4_1mm = "SMD,4.5x4.1mm"
        SMD4_2x4_4mm = "SMD,4.2x4.4mm"
        SMD10_4x10_3mm = "SMD,10.4x10.3mm"
        SMD10x11_5mm = "SMD,10x11.5mm"
        SMD13_5x12_8mm = "SMD,13.5x12.8mm"
        SMD17_2x17_2mm = "SMD,17.2x17.2mm"
        SMD5_2x5_4mm = "SMD,5.2x5.4mm"
        SMD11_6x10_1mm = "SMD,11.6x10.1mm"
        SMD10_5x10_3mm = "SMD,10.5x10.3mm"
        SMD7_2x6_6mm = "SMD,7.2x6.6mm"
        SMD10x10_2mm = "SMD,10x10.2mm"
        SMD7_8x7_8mm = "SMD,7.8x7.8mm"
        SMD1_7x2_3mm = "SMD,1.7x2.3mm"
        SMD5_2x5_7mm = "SMD,5.2x5.7mm"
        SMD2x2mm = "SMD,2x2mm"
        SMD4_5x5_2mm = "SMD,4.5x5.2mm"
        SMD9x10mm = "SMD,9x10mm"
        SMD2_5x2_9mm = "SMD,2.5x2.9mm"
        SMD4_6x4_1mm = "SMD,4.6x4.1mm"
        SMD7_5x7_5mm = "SMD,7.5x7.5mm"
        SMD5_5x5_2mm = "SMD,5.5x5.2mm"
        SMD6_4x6_6mm = "SMD,6.4x6.6mm"
        SMD12_5x13_5mm = "SMD,12.5x13.5mm"
        SMD10_7x10mm = "SMD,10.7x10mm"
        SMD5_5x5_3mm = "SMD,5.5x5.3mm"
        SMD10_1x11_6mm = "SMD,10.1x11.6mm"
        SMD10_3x10_5mm = "SMD,10.3x10.5mm"
        SMD3_2x3mm = "SMD,3.2x3mm"
        SMD6_6x6_4mm = "SMD,6.6x6.4mm"
        SMD1_2x0_6mm = "SMD,1.2x0.6mm"
        SMD1_2x1_8mm = "SMD,1.2x1.8mm"
        SMD5x5_2mm = "SMD,5x5.2mm"
        SMD8_3x8_3mm = "SMD,8.3x8.3mm"
        SMD10_2x10_8mm = "SMD,10.2x10.8mm"
        SMD2_5x3_2mm = "SMD,2.5x3.2mm"
        SMD4x4_5mm = "SMD,4x4.5mm"
        SMD8_5x8mm = "SMD,8.5x8mm"
        SMD3_5x3_2mm = "SMD,3.5x3.2mm"
        SMD12_9x13_2mm = "SMD,12.9x13.2mm"
        SMD8_8x8_2mm = "SMD,8.8x8.2mm"
        SMD4_1x4_4mm = "SMD,4.1x4.4mm"
        SMD10_8x10mm = "SMD,10.8x10mm"
        SMD10_5x10mm = "SMD,10.5x10mm"
        SMD1_1x1_8mm = "SMD,1.1x1.8mm"
        SMD7_5x7mm = "SMD,7.5x7mm"
        SMD3_8x3_8mm = "SMD,3.8x3.8mm"
        SMD1_6x2_2mm = "SMD,1.6x2.2mm"
        SMD12_2x12_2mm = "SMD,12.2x12.2mm"
        SMD4_8x4_8mm = "SMD,4.8x4.8mm"
        SMD5_7x5_4mm = "SMD,5.7x5.4mm"
        SMD15_5x16_5mm = "SMD,15.5x16.5mm"
        SMD8_2x8_8mm = "SMD,8.2x8.8mm"
        SMD10x14mm = "SMD,10x14mm"
        SMD5_1x5_4mm = "SMD,5.1x5.4mm"
        SMD16_5x15_5mm = "SMD,16.5x15.5mm"
        SMD2_1x3mm = "SMD,2.1x3mm"
        SMD10x11_6mm = "SMD,10x11.6mm"
        SMD3_2x4mm = "SMD,3.2x4mm"
        SMD7_2x7_9mm = "SMD,7.2x7.9mm"
        SMD5_8x5_8mm = "SMD,5.8x5.8mm"
        SMD6_6x7_4mm = "SMD,6.6x7.4mm"
        SMD12_7x12_7mm = "SMD,12.7x12.7mm"
        SMD1_2x2mm = "SMD,1.2x2mm"
        SMD1x1_7mm = "SMD,1x1.7mm"
        SMD4_4x4_1mm = "SMD,4.4x4.1mm"
        SMD4_2x4_2mm = "SMD,4.2x4.2mm"

    unnamed = L.list_field(2, F.Electrical)

    inductance = L.p_field(
        units=P.H,
        likely_constrained=True,
        soft_set=L.Range(100 * P.nH, 1 * P.H),
        tolerance_guess=10 * P.percent,
    )
    max_current = L.p_field(
        units=P.A,
        likely_constrained=True,
        soft_set=L.Range(1 * P.mA, 100 * P.A),
    )
    dc_resistance = L.p_field(
        units=P.Ω,
        soft_set=L.Range(10 * P.mΩ, 100 * P.Ω),
        tolerance_guess=10 * P.percent,
    )
    saturation_current = L.p_field(units=P.A)
    self_resonant_frequency = L.p_field(
        units=P.Hz,
        likely_constrained=True,
        soft_set=L.Range(100 * P.kHz, 1 * P.GHz),
        tolerance_guess=10 * P.percent,
    )
    package = L.p_field(domain=EnumDomain(Package))

    @L.rt_field
    def pickable(self) -> F.is_pickable_by_type:
        return F.is_pickable_by_type(
            endpoint=F.is_pickable_by_type.Endpoint.INDUCTORS,
            params=[
                self.inductance,
                self.max_current,
                self.dc_resistance,
                self.saturation_current,
                self.self_resonant_frequency,
                self.package,
            ],
        )

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(*self.unnamed)

    attach_to_footprint: F.can_attach_to_footprint_symmetrically

    @L.rt_field
    def simple_value_representation(self):
        S = F.has_simple_value_representation_based_on_params_chain.Spec
        return F.has_simple_value_representation_based_on_params_chain(
            S(self.inductance, tolerance=True),
            S(self.self_resonant_frequency),
            S(self.max_current),
            S(self.dc_resistance),
        )

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.L
    )

    # TODO: remove @https://github.com/atopile/atopile/issues/727
    @property
    def p1(self) -> F.Electrical:
        """Signal to one side of the inductor."""
        return self.unnamed[0]

    @property
    def p2(self) -> F.Electrical:
        """Signal to the other side of the inductor."""
        return self.unnamed[1]

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import Inductor

        inductor = new Inductor
        inductor.inductance = 10uH +/- 10%
        inductor.max_current = 2A
        inductor.dc_resistance = 50mohm +/- 20%
        inductor.self_resonant_frequency = 100MHz +/- 10%
        inductor.package = "0805"

        electrical1 ~ inductor.unnamed[0]
        electrical2 ~ inductor.unnamed[1]
        # OR
        electrical1 ~> inductor ~> electrical2

        # For filtering applications
        power_input ~> inductor ~> filtered_output
        """,
        language=F.has_usage_example.Language.ato,
    )
