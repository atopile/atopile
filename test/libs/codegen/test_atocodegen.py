# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from textwrap import dedent

from faebryk.libs.codegen.atocodegen import AtoCodeGen
from faebryk.libs.codegen.atocodeparse import AtoCodeParse


def _cleanup(s: str) -> str:
    return dedent(s).removeprefix("\n")


def test_atogen_basic_part():
    cf = AtoCodeGen.ComponentFile("TI_TCA9548APWR")

    cf.add_trait(
        "is_atomic_part",
        manufacturer="TI",
        partnumber="TCA9548APWR",
        footprint="TSSOP-24_L7.8-W4.4-P0.65-LS6.4-BL.kicad_mod",
        symbol="TCA9548APWR.kicad_sym",
        model="TSSOP-24_L7.8-W4.4-H1.0-LS6.4-P0.65.step",
    )
    cf.add_comments(
        "This trait marks this file as auto-generated",
        "If you want to manually change it, remove the trait",
        use_spacer=True,
    )
    cf.add_trait(
        "is_auto_generated",
        system="ato_part",
        source="easyeda:C130026",
        date="2025-05-26T12:53:38.352371+00:00",
        checksum="{CHECKSUM_PLACEHOLDER}",
    )
    ato = cf.dump()

    assert ato == _cleanup(
        """
        #pragma experiment("TRAITS")
        import is_atomic_part
        import is_auto_generated

        component TI_TCA9548APWR:
            trait is_atomic_part<manufacturer="TI", partnumber="TCA9548APWR", footprint="TSSOP-24_L7.8-W4.4-P0.65-LS6.4-BL.kicad_mod", symbol="TCA9548APWR.kicad_sym", model="TSSOP-24_L7.8-W4.4-H1.0-LS6.4-P0.65.step">

            # This trait marks this file as auto-generated
            # If you want to manually change it, remove the trait
            trait is_auto_generated<system="ato_part", source="easyeda:C130026", date="2025-05-26T12:53:38.352371+00:00", checksum="{CHECKSUM_PLACEHOLDER}">
        """  # noqa: E501
    )


def test_atogen_postmod():
    cf = AtoCodeGen.ComponentFile("BLA")
    t = cf.add_trait("is_atomic_part")

    assert cf.dump() == _cleanup(
        """
        #pragma experiment("TRAITS")
        import is_atomic_part

        component BLA:
            trait is_atomic_part
        """
    )

    t.args = {
        "manufacturer": "TI",
        "partnumber": "TCA9548APWR",
    }

    assert cf.dump() == _cleanup(
        """
        #pragma experiment("TRAITS")
        import is_atomic_part

        component BLA:
            trait is_atomic_part<manufacturer="TI", partnumber="TCA9548APWR">
        """
    )


def test_parse_regression_1():
    file = _cleanup("""
        #pragma experiment("TRAITS")
        import has_designator_prefix
        import has_part_picked
        import is_atomic_part
        import is_auto_generated

        component TDK_INVENSENSE_ICM_20948_package:
            # This trait marks this file as auto-generated
            # If you want to manually change it, remove the trait
            trait is_auto_generated<system="ato_part", source="easyeda:C726001", date="2025-07-08T23:04:40.873125+00:00", checksum="fa1d904cee1d545d9f702fcbe5be0266192efcbe8edc94acbbaa3493bf3aed62">

            trait is_atomic_part<manufacturer="TDK INVENSENSE", partnumber="ICM-20948", footprint="QFN-24_L3.0-W3.0-P0.40-BL-EP.kicad_mod", symbol="ICM-20948.kicad_sym", model="QFN-24_L3.0-W3.0-H0.9-P0.40-BL-EP.step">
            trait has_part_picked::by_supplier<supplier_id="lcsc", supplier_partno="C726001", manufacturer="TDK INVENSENSE", partno="ICM-20948">
            trait has_designator_prefix<prefix="U">

            # pins
            signal AUX_CL ~ pin 7
            signal AUX_DA ~ pin 21
            signal EP ~ pin 25
            signal FSYNC ~ pin 11
            signal GND ~ pin 18
            signal INT1 ~ pin 12
            signal REGOUT ~ pin 10
            signal RESV ~ pin 19
            RESV ~ pin 20
            signal SCL_SCLK ~ pin 23
            signal SDA_SDI ~ pin 24
            signal SDO_AD0 ~ pin 9
            signal VDD ~ pin 13
            signal VDDIO ~ pin 8
            signal nCS ~ pin 22
        """)  # noqa: E501

    ato = AtoCodeParse.ComponentFile(file)

    assert ato.parse_trait("is_atomic_part") == (
        None,
        {
            "manufacturer": "TDK INVENSENSE",
            "partnumber": "ICM-20948",
            "footprint": "QFN-24_L3.0-W3.0-P0.40-BL-EP.kicad_mod",
            "symbol": "ICM-20948.kicad_sym",
            "model": "QFN-24_L3.0-W3.0-H0.9-P0.40-BL-EP.step",
        },
    )

    import faebryk.library._F as F

    atomic_trait = ato.get_trait(F.is_atomic_part)
    assert atomic_trait._manufacturer == "TDK INVENSENSE"
    assert atomic_trait._partnumber == "ICM-20948"
    assert atomic_trait._footprint == "QFN-24_L3.0-W3.0-P0.40-BL-EP.kicad_mod"
    assert atomic_trait._symbol == "ICM-20948.kicad_sym"
    assert atomic_trait._model == "QFN-24_L3.0-W3.0-H0.9-P0.40-BL-EP.step"
