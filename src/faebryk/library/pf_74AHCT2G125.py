# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.library.can_attach_to_footprint_via_pinmap import (
    can_attach_to_footprint_via_pinmap,
)
from faebryk.library.can_be_decoupled import can_be_decoupled
from faebryk.library.can_bridge_defined import can_bridge_defined
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_datasheet_defined import has_datasheet_defined
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.has_single_electric_reference_defined import (
    has_single_electric_reference_defined,
)
from faebryk.library.Range import Range
from faebryk.libs.units import P


class pf_74AHCT2G125(Module):
    """
    The 74AHC1G/AHCT1G125 is a high-speed Si-gate CMOS device.
    The 74AHC1G/AHCT1G125 provides one non-inverting buffer/line
    driver with 3-state output. The 3-state output is controlled
    by the output enable input (OE). A HIGH at OE causes the
    output to assume a high-impedance OFF-state.
    """

    def __init__(self) -> None:
        super().__init__()

        # interfaces
        class _IFs(Module.IFS()):
            power = ElectricPower()
            a = ElectricLogic()  # IN
            y = ElectricLogic()  # OUT
            oe = ElectricLogic()  # enable, active low

        self.IFs = _IFs(self)

        x = self.IFs
        self.add_trait(
            can_attach_to_footprint_via_pinmap(
                {
                    "1": x.oe.IFs.signal,
                    "2": x.a.IFs.signal,
                    "3": x.power.IFs.lv,
                    "4": x.y.IFs.signal,
                    "5": x.power.IFs.hv,
                }
            )
        )

        self.IFs.power.PARAMs.voltage.merge(Range(4.5 * P.V, 5.5 * P.V))

        self.IFs.power.get_trait(can_be_decoupled).decouple()

        # connect all logic references
        ref = ElectricLogic.connect_all_module_references(self)
        self.add_trait(has_single_electric_reference_defined(ref))

        self.add_trait(has_designator_prefix_defined("U"))

        self.add_trait(can_bridge_defined(self.IFs.a, self.IFs.y))

        self.add_trait(
            has_datasheet_defined(
                "https://datasheet.lcsc.com/lcsc/2304140030_Nexperia-74AHCT1G125GV-125_C12494.pdf"
            )
        )
