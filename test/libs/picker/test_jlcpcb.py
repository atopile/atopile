# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging
import unittest
from pathlib import Path
from tempfile import mkdtemp

import faebryk.library._F as F
import faebryk.libs.picker.lcsc as lcsc
from faebryk.core.core import Module
from faebryk.libs.logging import setup_basic_logging
from faebryk.libs.picker.jlcpcb.jlcpcb import JLCPCB_DB
from faebryk.libs.picker.jlcpcb.pickers import add_jlcpcb_pickers
from faebryk.libs.picker.picker import DescriptiveProperties, has_part_picked
from faebryk.libs.units import P, Quantity

logger = logging.getLogger(__name__)


lcsc.LIB_FOLDER = Path(mkdtemp())


@unittest.skipIf(not JLCPCB_DB.config.db_path.exists(), reason="Requires large db")
class TestPickerJlcpcb(unittest.TestCase):
    class TestRequirements:
        def __init__(
            self,
            test_case: unittest.TestCase,
            requirement: Module,
            footprint: list[tuple[str, int]],
        ):
            self.test_case = test_case
            self.result = requirement
            self.requirement = requirement
            self.footprint = footprint

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

            requirement.add_trait(F.has_footprint_requirement_defined(footprint))

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
                self.requirement.PARAMs.get_all(), self.result.PARAMs.get_all()
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
            add_jlcpcb_pickers(self.result)
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
                r.PARAMs.bandwidth.merge(F.Range.upper_bound(1 * P.Mhertz)),
                r.PARAMs.common_mode_rejection_ratio.merge(
                    F.Range.lower_bound(Quantity(50, P.dB))
                ),
                r.PARAMs.input_bias_current.merge(F.Range.upper_bound(1 * P.nA)),
                r.PARAMs.input_offset_voltage.merge(F.Range.upper_bound(1 * P.mV)),
                r.PARAMs.gain_bandwidth_product.merge(
                    F.Range.upper_bound(1 * P.Mhertz)
                ),
                r.PARAMs.output_current.merge(F.Range.upper_bound(1 * P.mA)),
                r.PARAMs.slew_rate.merge(F.Range.upper_bound(1 * P.MV / P.us)),
            )
        )
        requirement.add_trait(
            F.has_defined_descriptive_properties(
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
        )

    def test_find_lcsc_partnumber(self):
        requirement = F.OpAmp().builder(
            lambda r: (
                r.PARAMs.bandwidth.merge(F.Range.upper_bound(1 * P.Mhertz)),
                r.PARAMs.common_mode_rejection_ratio.merge(
                    F.Range.lower_bound(Quantity(50, P.dB))
                ),
                r.PARAMs.input_bias_current.merge(F.Range.upper_bound(1 * P.nA)),
                r.PARAMs.input_offset_voltage.merge(F.Range.upper_bound(1 * P.mV)),
                r.PARAMs.gain_bandwidth_product.merge(
                    F.Range.upper_bound(1 * P.Mhertz)
                ),
                r.PARAMs.output_current.merge(F.Range.upper_bound(1 * P.mA)),
                r.PARAMs.slew_rate.merge(F.Range.upper_bound(1 * P.MV / P.us)),
            )
        )
        requirement.add_trait(
            F.has_defined_descriptive_properties(
                {
                    "LCSC": "C7972",
                }
            )
        )
        self.TestRequirements(
            self,
            requirement=requirement,
            footprint=[("SOT-23-5", 5)],
        )

    def test_find_resistor(self):
        self.TestRequirements(
            self,
            requirement=F.Resistor().builder(
                lambda r: (
                    r.PARAMs.resistance.merge(
                        F.Range.from_center(10 * P.kohm, 1 * P.kohm)
                    ),
                    r.PARAMs.rated_power.merge(F.Range.lower_bound(0.05 * P.W)),
                    r.PARAMs.rated_voltage.merge(F.Range.lower_bound(25 * P.V)),
                )
            ),
            footprint=[("0402", 2)],
        )

        self.TestRequirements(
            self,
            requirement=F.Resistor().builder(
                lambda r: (
                    r.PARAMs.resistance.merge(
                        F.Range.from_center(69 * P.kohm, 2 * P.kohm)
                    ),
                    r.PARAMs.rated_power.merge(F.Range.lower_bound(0.1 * P.W)),
                    r.PARAMs.rated_voltage.merge(F.Range.lower_bound(50 * P.V)),
                )
            ),
            footprint=[("0603", 2)],
        )

    def test_find_capacitor(self):
        self.TestRequirements(
            self,
            requirement=F.Capacitor().builder(
                lambda c: (
                    c.PARAMs.capacitance.merge(
                        F.Range.from_center(100 * P.nF, 10 * P.nF)
                    ),
                    c.PARAMs.rated_voltage.merge(F.Range.lower_bound(25 * P.V)),
                    c.PARAMs.temperature_coefficient.merge(
                        F.Range.lower_bound(F.Capacitor.TemperatureCoefficient.X7R)
                    ),
                )
            ),
            footprint=[("0603", 2)],
        )

        self.TestRequirements(
            self,
            requirement=F.Capacitor().builder(
                lambda c: (
                    c.PARAMs.capacitance.merge(
                        F.Range.from_center(47 * P.pF, 4.7 * P.pF)
                    ),
                    c.PARAMs.rated_voltage.merge(F.Range.lower_bound(50 * P.V)),
                    c.PARAMs.temperature_coefficient.merge(
                        F.Range.lower_bound(F.Capacitor.TemperatureCoefficient.C0G)
                    ),
                )
            ),
            footprint=[("0402", 2)],
        )

    def test_find_inductor(self):
        self.TestRequirements(
            self,
            requirement=F.Inductor().builder(
                lambda i: (
                    i.PARAMs.inductance.merge(
                        F.Range.from_center(4.7 * P.nH, 0.47 * P.nH)
                    ),
                    i.PARAMs.rated_current.merge(F.Range.lower_bound(0.01 * P.A)),
                    i.PARAMs.dc_resistance.merge(F.Range.upper_bound(1 * P.ohm)),
                    i.PARAMs.self_resonant_frequency.merge(
                        F.Range.lower_bound(100 * P.Mhertz)
                    ),
                )
            ),
            footprint=[("0603", 2)],
        )

    def test_find_mosfet(self):
        self.TestRequirements(
            self,
            requirement=F.MOSFET().builder(
                lambda m: (
                    m.PARAMs.channel_type.merge(
                        F.Constant(F.MOSFET.ChannelType.N_CHANNEL)
                    ),
                    m.PARAMs.saturation_type.merge(
                        F.Constant(F.MOSFET.SaturationType.ENHANCEMENT)
                    ),
                    m.PARAMs.gate_source_threshold_voltage.merge(
                        F.Range(0.4 * P.V, 3 * P.V)
                    ),
                    m.PARAMs.max_drain_source_voltage.merge(
                        F.Range.lower_bound(20 * P.V)
                    ),
                    m.PARAMs.max_continuous_drain_current.merge(
                        F.Range.lower_bound(2 * P.A)
                    ),
                    m.PARAMs.on_resistance.merge(F.Range.upper_bound(0.1 * P.ohm)),
                )
            ),
            footprint=[("SOT-23", 3)],
        )

    def test_find_diode(self):
        self.TestRequirements(
            self,
            requirement=F.Diode().builder(
                lambda d: (
                    d.PARAMs.current.merge(F.Range.lower_bound(1 * P.A)),
                    d.PARAMs.forward_voltage.merge(F.Range.upper_bound(1.7 * P.V)),
                    d.PARAMs.reverse_working_voltage.merge(
                        F.Range.lower_bound(20 * P.V)
                    ),
                    d.PARAMs.reverse_leakage_current.merge(
                        F.Range.upper_bound(100 * P.uA)
                    ),
                    d.PARAMs.max_current.merge(F.Range.lower_bound(1 * P.A)),
                )
            ),
            footprint=[("SOD-123", 2)],
        )

    def test_find_tvs(self):
        self.TestRequirements(
            self,
            requirement=F.TVS().builder(
                lambda t: (
                    # TODO: There is no current specified for TVS diodes, only peak
                    # current
                    t.PARAMs.current.merge(F.ANY()),
                    t.PARAMs.forward_voltage.merge(F.ANY()),
                    t.PARAMs.reverse_working_voltage.merge(
                        F.Range.lower_bound(5 * P.V)
                    ),
                    t.PARAMs.reverse_leakage_current.merge(F.ANY()),
                    t.PARAMs.max_current.merge(F.Range.lower_bound(10 * P.A)),
                    t.PARAMs.reverse_breakdown_voltage.merge(
                        F.Range.upper_bound(8 * P.V)
                    ),
                )
            ),
            footprint=[("SMB(DO-214AA)", 2)],
        )

    def test_find_ldo(self):
        self.TestRequirements(
            self,
            F.LDO().builder(
                lambda u: (
                    u.PARAMs.output_voltage.merge(
                        F.Range.from_center(3.3 * P.V, 0.1 * P.V)
                    ),
                    u.PARAMs.output_current.merge(F.Range.lower_bound(0.1 * P.A)),
                    u.PARAMs.max_input_voltage.merge(F.Range.lower_bound(5 * P.V)),
                    u.PARAMs.dropout_voltage.merge(F.Range.upper_bound(1 * P.V)),
                    u.PARAMs.output_polarity.merge(
                        F.Constant(F.LDO.OutputPolarity.POSITIVE)
                    ),
                    u.PARAMs.output_type.merge(F.Constant(F.LDO.OutputType.FIXED)),
                    u.PARAMs.psrr.merge(F.ANY()),
                    u.PARAMs.quiescent_current.merge(F.ANY()),
                )
            ),
            footprint=[
                ("SOT-23", 3),
                ("SOT23", 3),
                ("SOT-23-3", 3),
                ("SOT-23-3L", 3),
            ],
        )

    def tearDown(self):
        # in test atexit not triggered, thus need to close DB manually
        JLCPCB_DB.get().close()


if __name__ == "__main__":
    setup_basic_logging()
    logger.setLevel(logging.DEBUG)
    unittest.main()
