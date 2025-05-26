# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from textwrap import dedent

from faebryk.libs.codegen.atocodegen import AtoCodeGen


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
