# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.core.util import connect_to_all_interfaces
from faebryk.library.can_attach_to_footprint_via_pinmap import (
    can_attach_to_footprint_via_pinmap,
)
from faebryk.library.can_be_decoupled import can_be_decoupled
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_datasheet_defined import has_datasheet_defined
from faebryk.library.has_designator_prefix_defined import (
    has_designator_prefix_defined,
)
from faebryk.library.Range import Range


class ME6211C33M5G_N(Module):
    """
    3.3V 600mA LDO
    """

    def __init__(self, default_enabled: bool = True) -> None:
        super().__init__()

        # interfaces
        class _IFs(Module.IFS()):
            power_in = ElectricPower()
            power_out = ElectricPower()
            enable = Electrical()

        self.IFs = _IFs(self)

        # components
        class _NODEs(Module.NODES()): ...

        self.NODEs = _NODEs(self)

        class _PARAMs(Module.PARAMS()): ...

        self.PARAMs = _PARAMs(self)

        # set constraints
        self.IFs.power_out.PARAMs.voltage.merge(Range(3.3 * 0.98, 3.3 * 1.02))

        # connect decouple capacitor
        self.IFs.power_in.get_trait(can_be_decoupled).decouple()
        self.IFs.power_out.get_trait(can_be_decoupled).decouple()

        # LDO in & out share gnd reference
        self.IFs.power_in.IFs.lv.connect(self.IFs.power_out.IFs.lv)

        self.add_trait(has_designator_prefix_defined("U"))
        self.add_trait(
            can_attach_to_footprint_via_pinmap(
                {
                    "1": self.IFs.power_in.IFs.hv,
                    "2": self.IFs.power_in.IFs.lv,
                    "3": self.IFs.enable,
                    "5": self.IFs.power_out.IFs.hv,
                }
            )
        )

        self.add_trait(
            has_datasheet_defined(
                "https://datasheet.lcsc.com/lcsc/1811131510_MICRONE-Nanjing-Micro-One-Elec-ME6211C33M5G-N_C82942.pdf"
            )
        )

        if default_enabled:
            self.IFs.enable.connect(self.IFs.power_in.IFs.hv)

        connect_to_all_interfaces(self.IFs.power_in.IFs.lv, [self.IFs.power_out.IFs.lv])
