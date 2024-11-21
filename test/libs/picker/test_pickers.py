# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import unittest
from abc import ABC, abstractmethod
from pathlib import Path
from tempfile import mkdtemp

import pytest

import faebryk.library._F as F
import faebryk.libs.picker.lcsc as lcsc
from faebryk.core.module import Module
from faebryk.core.parameter import Parameter
from faebryk.libs.brightness import TypicalLuminousIntensity
from faebryk.libs.logging import setup_basic_logging
from faebryk.libs.picker.api.pickers import add_api_pickers
from faebryk.libs.picker.jlcpcb.jlcpcb import JLCPCB_DB
from faebryk.libs.picker.jlcpcb.pickers import add_jlcpcb_pickers
from faebryk.libs.picker.picker import DescriptiveProperties, has_part_picked
from faebryk.libs.test.times import Times
from faebryk.libs.units import P, Quantity

logger = logging.getLogger(__name__)

lcsc.LIB_FOLDER = Path(mkdtemp())


class TestPickerBase(unittest.TestCase, ABC):
    @abstractmethod
    def add_pickers(self, module: Module):
        pass

    class TestRequirements:
        def __init__(
            self,
            test_case: unittest.TestCase,
            requirement: Module,
            footprint: list[tuple[str, int]],
            add_pickers_func,
        ):
            self.test_case = test_case
            self.result = requirement
            self.requirement = requirement
            self.footprint = footprint
            self.add_pickers_func = add_pickers_func

            self.req_lcsc_pn = None
            if self.requirement.has_trait(F.has_descriptive_properties) and "LCSC" in (
                self.requirement.get_trait(F.has_descriptive_properties).get_properties,
            ):
                self.req_lcsc_pn = self.requirement.get_trait(
                    F.has_descriptive_properties
                ).get_properties()["LCSC"]

            self.req_manufacturer_pn = None
            if (
                self.requirement.has_trait(F.has_descriptive_properties)
                and DescriptiveProperties.partno
                in self.requirement.get_trait(
                    F.has_descriptive_properties
                ).get_properties()
            ):
                self.req_manufacturer_pn = self.requirement.get_trait(
                    F.has_descriptive_properties
                ).get_properties()[DescriptiveProperties.partno]

            requirement.add(F.has_footprint_requirement_defined(footprint))

            self.test()

        def satisfies_requirements(self):
            self.test_case.assertTrue(
                self.result.has_trait(F.has_descriptive_properties)
            )
            if self.req_lcsc_pn is not None:
                self.test_case.assertIn(
                    "LCSC",
                    self.result.get_trait(
                        F.has_descriptive_properties
                    ).get_properties(),
                )

                self.test_case.assertEqual(
                    self.req_lcsc_pn,
                    self.result.get_trait(
                        F.has_descriptive_properties
                    ).get_properties()["LCSC"],
                )

            if self.req_manufacturer_pn is not None:
                self.test_case.assertIn(
                    DescriptiveProperties.partno,
                    self.result.get_trait(
                        F.has_descriptive_properties
                    ).get_properties(),
                )
                self.test_case.assertEqual(
                    self.req_manufacturer_pn,
                    self.result.get_trait(
                        F.has_descriptive_properties
                    ).get_properties()[DescriptiveProperties.partno],
                )

            for req, res in zip(
                self.requirement.get_children(direct_only=True, types=Parameter),
                self.result.get_children(direct_only=True, types=Parameter),
            ):
                req = req.get_most_narrow()
                res = res.get_most_narrow()

                if isinstance(req, F.Range):
                    self.test_case.assertTrue(res in req)
                elif isinstance(req, F.Constant):
                    self.test_case.assertEqual(req, res)
                elif isinstance(req, F.Set):
                    self.test_case.assertIn(res, req.params)
                elif isinstance(req, F.TBD):
                    self.test_case.assertTrue(isinstance(res, F.ANY))
                elif isinstance(req, F.ANY):
                    self.test_case.assertTrue(isinstance(res, F.ANY))
                else:
                    raise NotImplementedError(
                        f"Unsupported type of parameter: {type(req)}: {req}"
                    )

        def test(self):
            self.add_pickers_func(self.result)
            self.result.get_trait(F.has_picker).pick()

            self.test_case.assertTrue(self.result.has_trait(has_part_picked))

            # check part number
            self.test_case.assertTrue(
                self.result.has_trait(F.has_descriptive_properties)
            )
            self.test_case.assertIn(
                DescriptiveProperties.partno,
                self.result.get_trait(F.has_descriptive_properties).get_properties(),
            )
            self.test_case.assertNotEqual(
                "",
                self.result.get_trait(F.has_descriptive_properties).get_properties()[
                    DescriptiveProperties.partno
                ],
            )

            # check footprint
            self.test_case.assertTrue(self.result.has_trait(F.has_footprint))
            self.test_case.assertTrue(
                self.result.get_trait(F.has_footprint)
                .get_footprint()
                .has_trait(F.has_kicad_footprint)
            )
            # check pin count
            self.test_case.assertEqual(
                self.footprint[0][1],
                len(
                    self.result.get_trait(F.has_footprint)
                    .get_footprint()
                    .get_trait(F.has_kicad_footprint)
                    .get_pin_names()
                ),
            )

            # check requirements from module
            self.satisfies_requirements()

    def test_find_manufacturer_partnumber(self):
        requirement = F.OpAmp().builder(
            lambda r: (
                r.bandwidth.merge(F.Range.upper_bound(1 * P.Mhertz)),
                r.common_mode_rejection_ratio.merge(
                    F.Range.lower_bound(Quantity(50, P.dB))
                ),
                r.input_bias_current.merge(F.Range.upper_bound(1 * P.nA)),
                r.input_offset_voltage.merge(F.Range.upper_bound(1 * P.mV)),
                r.gain_bandwidth_product.merge(F.Range.upper_bound(1 * P.Mhertz)),
                r.output_current.merge(F.Range.upper_bound(1 * P.mA)),
                r.slew_rate.merge(F.Range.upper_bound(1 * P.MV / P.us)),
            )
        )
        requirement.add(
            F.has_descriptive_properties_defined(
                {
                    DescriptiveProperties.partno: "LMV321IDBVR",
                    DescriptiveProperties.manufacturer: "Texas Instruments",
                }
            )
        )
        self.TestRequirements(
            self,
            requirement=requirement,
            footprint=[("SOT-23-5", 5)],
            add_pickers_func=self.add_pickers,
        )

    def test_find_lcsc_partnumber(self):
        requirement = F.OpAmp().builder(
            lambda r: (
                r.bandwidth.merge(F.Range.upper_bound(1 * P.Mhertz)),
                r.common_mode_rejection_ratio.merge(
                    F.Range.lower_bound(Quantity(50, P.dB))
                ),
                r.input_bias_current.merge(F.Range.upper_bound(1 * P.nA)),
                r.input_offset_voltage.merge(F.Range.upper_bound(1 * P.mV)),
                r.gain_bandwidth_product.merge(F.Range.upper_bound(1 * P.Mhertz)),
                r.output_current.merge(F.Range.upper_bound(1 * P.mA)),
                r.slew_rate.merge(F.Range.upper_bound(1 * P.MV / P.us)),
            )
        )
        requirement.add(F.has_descriptive_properties_defined({"LCSC": "C7972"}))
        self.TestRequirements(
            self,
            requirement=requirement,
            footprint=[("SOT-23-5", 5)],
            add_pickers_func=self.add_pickers,
        )

    def test_find_resistor(self):
        self.TestRequirements(
            self,
            requirement=F.Resistor().builder(
                lambda r: (
                    r.resistance.merge(F.Range.from_center(10 * P.kohm, 1 * P.kohm)),
                    r.rated_power.merge(F.Range.lower_bound(0.05 * P.W)),
                    r.rated_voltage.merge(F.Range.lower_bound(25 * P.V)),
                )
            ),
            footprint=[("0402", 2)],
            add_pickers_func=self.add_pickers,
        )

        self.TestRequirements(
            self,
            requirement=F.Resistor().builder(
                lambda r: (
                    r.resistance.merge(F.Range.from_center(69 * P.kohm, 2 * P.kohm)),
                    r.rated_power.merge(F.Range.lower_bound(0.1 * P.W)),
                    r.rated_voltage.merge(F.Range.lower_bound(50 * P.V)),
                )
            ),
            footprint=[("0603", 2)],
            add_pickers_func=self.add_pickers,
        )

    def test_find_capacitor(self):
        self.TestRequirements(
            self,
            requirement=F.Capacitor().builder(
                lambda c: (
                    c.capacitance.merge(F.Range.from_center(100 * P.nF, 10 * P.nF)),
                    c.rated_voltage.merge(F.Range.lower_bound(25 * P.V)),
                    c.temperature_coefficient.merge(
                        F.Range.lower_bound(F.Capacitor.TemperatureCoefficient.X7R)
                    ),
                )
            ),
            footprint=[("0603", 2)],
            add_pickers_func=self.add_pickers,
        )

        self.TestRequirements(
            self,
            requirement=F.Capacitor().builder(
                lambda c: (
                    c.capacitance.merge(F.Range.from_center(47 * P.pF, 4.7 * P.pF)),
                    c.rated_voltage.merge(F.Range.lower_bound(50 * P.V)),
                    c.temperature_coefficient.merge(
                        F.Range.lower_bound(F.Capacitor.TemperatureCoefficient.C0G)
                    ),
                )
            ),
            footprint=[("0402", 2)],
            add_pickers_func=self.add_pickers,
        )

    def test_find_inductor(self):
        self.TestRequirements(
            self,
            requirement=F.Inductor().builder(
                lambda i: (
                    i.inductance.merge(F.Range.from_center(4.7 * P.nH, 0.47 * P.nH)),
                    i.rated_current.merge(F.Range.lower_bound(0.01 * P.A)),
                    i.dc_resistance.merge(F.Range.upper_bound(1 * P.ohm)),
                    i.self_resonant_frequency.merge(
                        F.Range.lower_bound(100 * P.Mhertz)
                    ),
                )
            ),
            footprint=[("0603", 2)],
            add_pickers_func=self.add_pickers,
        )

    def test_find_mosfet(self):
        self.TestRequirements(
            self,
            requirement=F.MOSFET().builder(
                lambda m: (
                    m.channel_type.merge(F.Constant(F.MOSFET.ChannelType.N_CHANNEL)),
                    m.saturation_type.merge(
                        F.Constant(F.MOSFET.SaturationType.ENHANCEMENT)
                    ),
                    m.gate_source_threshold_voltage.merge(F.Range(0.4 * P.V, 3 * P.V)),
                    m.max_drain_source_voltage.merge(F.Range.lower_bound(20 * P.V)),
                    m.max_continuous_drain_current.merge(F.Range.lower_bound(2 * P.A)),
                    m.on_resistance.merge(F.Range.upper_bound(0.1 * P.ohm)),
                )
            ),
            footprint=[("SOT-23", 3)],
            add_pickers_func=self.add_pickers,
        )

    def test_find_diode(self):
        self.TestRequirements(
            self,
            requirement=F.Diode().builder(
                lambda d: (
                    d.current.merge(F.Range.lower_bound(1 * P.A)),
                    d.forward_voltage.merge(F.Range.upper_bound(1.7 * P.V)),
                    d.reverse_working_voltage.merge(F.Range.lower_bound(20 * P.V)),
                    d.reverse_leakage_current.merge(F.Range.upper_bound(100 * P.uA)),
                    d.max_current.merge(F.Range.lower_bound(1 * P.A)),
                )
            ),
            footprint=[("SOD-123", 2)],
            add_pickers_func=self.add_pickers,
        )

    def test_find_led(self):
        self.TestRequirements(
            self,
            requirement=F.LED().builder(
                lambda led: (
                    led.color.merge(F.LED.Color.RED),
                    led.brightness.merge(
                        TypicalLuminousIntensity.APPLICATION_LED_INDICATOR_INSIDE.value.value
                    ),
                    # TODO: check semantics of F.ANY vs F.TBD
                    led.reverse_leakage_current.merge(F.ANY()),
                    led.reverse_working_voltage.merge(F.ANY()),
                    led.max_brightness.merge(F.Range.lower_bound(100 * P.millicandela)),
                    led.forward_voltage.merge(F.Range.upper_bound(2.5 * P.V)),
                    led.max_current.merge(F.Range.upper_bound(20 * P.mA)),
                )
            ),
            footprint=[("0805", 2)],
            add_pickers_func=self.add_pickers,
        )

    def test_find_tvs(self):
        self.TestRequirements(
            self,
            requirement=F.TVS().builder(
                lambda t: (
                    # TODO: There is no current specified for TVS diodes, only peak
                    # current
                    t.current.merge(F.ANY()),
                    t.forward_voltage.merge(F.ANY()),
                    t.reverse_working_voltage.merge(F.Range.lower_bound(5 * P.V)),
                    t.reverse_leakage_current.merge(F.ANY()),
                    t.max_current.merge(F.Range.lower_bound(10 * P.A)),
                    t.reverse_breakdown_voltage.merge(F.Range.upper_bound(8 * P.V)),
                )
            ),
            footprint=[("SMB(DO-214AA)", 2)],
            add_pickers_func=self.add_pickers,
        )

    def test_find_ldo(self):
        self.TestRequirements(
            self,
            F.LDO().builder(
                lambda u: (
                    u.output_voltage.merge(F.Range.from_center(3.3 * P.V, 0.1 * P.V)),
                    u.output_current.merge(F.Range.lower_bound(0.1 * P.A)),
                    u.power_in.voltage.merge(5 * P.V),
                    u.dropout_voltage.merge(F.Range.upper_bound(1 * P.V)),
                    u.output_polarity.merge(F.Constant(F.LDO.OutputPolarity.POSITIVE)),
                    u.output_type.merge(F.Constant(F.LDO.OutputType.FIXED)),
                    u.psrr.merge(F.ANY()),
                    u.quiescent_current.merge(F.ANY()),
                )
            ),
            footprint=[
                ("SOT-23", 3),
                ("SOT23", 3),
                ("SOT-23-3", 3),
                ("SOT-23-3L", 3),
            ],
            add_pickers_func=self.add_pickers,
        )


class TestPickerPerformanceBase(unittest.TestCase, ABC):
    @abstractmethod
    def add_pickers(self, module: Module):
        pass

    def test_simple_full(self):
        # conclusions
        # - first pick overall is slow, need to load sqlite into buffer cache
        # - first pick of component type is slower than subsequent picks
        #   (even with different parameters)
        # - component type order has no influence
        # - component type speed differs a lot (res = 500ms, cap = 100ms)
        #   (even though both value based)
        #   e-series speed (query or count), if resistor with E24, 200ms
        #   still 2x though, maybe total count?
        # - e-series intersect 20% execution time
        #   => optimized with cache

        timings = Times()

        def r_builder(resistance_kohm: float):
            return F.Resistor().builder(
                lambda r: (
                    r.resistance.merge(
                        F.Range.from_center_rel(resistance_kohm * P.kohm, 0.1)
                    ),
                    r.rated_power.merge(F.ANY()),
                    r.rated_voltage.merge(F.ANY()),
                )
            )

        def c_builder(capacitance_pf: float):
            return F.Capacitor().builder(
                lambda c: (
                    c.capacitance.merge(
                        F.Range.from_center_rel(capacitance_pf * P.pF, 0.1)
                    ),
                    c.rated_voltage.merge(F.ANY()),
                    c.temperature_coefficient.merge(F.ANY()),
                )
            )

        resistors = [r_builder(5 * (i + 1)) for i in range(5)] + [
            r_builder(5 * (i + 1)) for i in reversed(range(5))
        ]
        caps = [c_builder(10 * (i + 1)) for i in range(5)] + [
            c_builder(10 * (i + 1)) for i in reversed(range(5))
        ]
        resistors_10k = [r_builder(10) for _ in range(10)]

        mods = resistors + caps + resistors_10k

        for mod in mods:
            self.add_pickers(mod)

        with timings.context("resistors"):
            for i, r in enumerate(resistors):
                r.get_trait(F.has_picker).pick()
                timings.add(
                    f"full pick value pick (resistor {i}:"
                    f" {r.resistance.as_unit_with_tolerance('ohm')})"
                )

        # cache is warm now, but also for non resistors?
        with timings.context("capacitors"):
            for i, c in enumerate(caps):
                c.get_trait(F.has_picker).pick()
                timings.add(
                    f"full pick value pick (capacitor {i}:"
                    f" {c.capacitance.as_unit_with_tolerance('F')})"
                )

        with timings.context("resistors_10k"):
            for i, r in enumerate(resistors_10k):
                r.get_trait(F.has_picker).pick()
                timings.add(
                    f"full pick value pick (resistor {i}:"
                    f" {r.resistance.as_unit_with_tolerance('ohm')})"
                )

        print(timings)


def is_db_available():
    return JLCPCB_DB.config.db_path.exists()


@pytest.mark.slow
@unittest.skipIf(not is_db_available(), reason="Requires large db")
class TestPickerJlcpcb(TestPickerBase):
    def add_pickers(self, module):
        add_jlcpcb_pickers(module)

    def tearDown(self):
        # in test atexit not triggered, thus need to close DB manually
        JLCPCB_DB.get().close()


@pytest.mark.slow
@unittest.skipIf(not is_db_available(), reason="Requires large db")
class TestPickerPerformanceJlcpcb(TestPickerPerformanceBase):
    def add_pickers(self, module):
        add_jlcpcb_pickers(module)

    def tearDown(self):
        JLCPCB_DB.get().close()


class TestPickerApi(TestPickerBase):
    def add_pickers(self, module):
        add_api_pickers(module)


class TestPickerPerformanceApi(TestPickerPerformanceBase):
    def add_pickers(self, module):
        add_api_pickers(module)


if __name__ == "__main__":
    setup_basic_logging()
    logger.setLevel(logging.DEBUG)

    unittest.main()
