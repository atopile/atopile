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


def test_parse_trait_with_comma_in_footprint():
    file = _cleanup(
        """
        #pragma experiment("TRAITS")
        import is_atomic_part

        component PCA9536_package:
            trait is_atomic_part<
                manufacturer="NXP",
                partnumber="PCA9536",
                footprint="TSSOP-8_L3_0-W3_0-P0_65-LS4_4-BL_EP.kicad_mod",
                symbol="PCA9536.kicad_sym"
            >
        """
    )

    ato = AtoCodeParse.ComponentFile(file)

    assert ato.parse_trait("is_atomic_part") == (
        None,
        {
            "manufacturer": "NXP",
            "partnumber": "PCA9536",
            "footprint": "TSSOP-8_L3_0-W3_0-P0_65-LS4_4-BL_EP.kicad_mod",
            "symbol": "PCA9536.kicad_sym",
        },
    )

    import faebryk.library._F as F

    atomic_trait = ato.get_trait(F.is_atomic_part)
    assert atomic_trait._manufacturer == "NXP"
    assert atomic_trait._partnumber == "PCA9536"
    assert atomic_trait._footprint == "TSSOP-8_L3_0-W3_0-P0_65-LS4_4-BL_EP.kicad_mod"
    assert atomic_trait._symbol == "PCA9536.kicad_sym"


def test_backward_compatibility_unsanitized_footprint():
    """Test that unsanitized footprint files are automatically upgraded."""
    import tempfile
    from pathlib import Path

    import faebryk.libs.ato_part

    assert hasattr(faebryk.libs.ato_part, "load_footprint_with_fallback"), (
        "Function not found in module"
    )

    from faebryk.libs.ato_part import load_footprint_with_fallback

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        part_dir = temp_path / "test_part"
        part_dir.mkdir()

        unsanitized_fp_name = "TSSOP-8_L3,0-W3,0-P0,65-LS4,4-BL_EP.kicad_mod"
        unsanitized_fp_path = part_dir / unsanitized_fp_name

        fp_content = (
            '(footprint "TSSOP-8_L3,0-W3,0-P0,65-LS4,4-BL_EP" '
            '(version 20240108) (generator "pcbnew") (generator_version "8.0")\n'
            '  (layer "F.Cu")\n'
            "  (attr smd)\n"
            ")"
        )
        unsanitized_fp_path.write_text(fp_content)

        _, fp = load_footprint_with_fallback(part_dir, unsanitized_fp_name)

        sanitized_fp_name = "TSSOP_8_L3_0_W3_0_P0_65_LS4_4_BL_EP.kicad_mod"
        sanitized_fp_path = part_dir / sanitized_fp_name

        assert sanitized_fp_path.exists(), (
            "Sanitized footprint file should exist after auto-upgrade"
        )
        assert not unsanitized_fp_path.exists(), (
            "Unsanitized footprint file should be renamed"
        )
        assert fp is not None, "Footprint should load successfully"
