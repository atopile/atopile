# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.library.can_attach_to_footprint_via_pinmap import (
    can_attach_to_footprint_via_pinmap,
)
from faebryk.library.Electrical import Electrical
from faebryk.library.has_datasheet_defined import has_datasheet_defined
from faebryk.library.has_designator_prefix_defined import (
    has_designator_prefix_defined,
)
from faebryk.libs.util import times


class B4B_ZR_SM4_TF(Module):
    def __init__(self) -> None:
        super().__init__()

        class _IFs(Module.IFS()):
            pin = times(4, Electrical)
            mount = times(2, Electrical)

        self.IFs = _IFs(self)

        x = self.IFs
        self.add_trait(
            can_attach_to_footprint_via_pinmap(
                {
                    "1": x.pin[0],
                    "2": x.pin[1],
                    "3": x.pin[2],
                    "4": x.pin[3],
                    "5": x.mount[0],
                    "6": x.mount[1],
                }
            )
        )

        self.add_trait(
            has_datasheet_defined(
                "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2304140030_BOOMELE-Boom-Precision-Elec-1-5-4P_C145997.pdf"
            )
        )

        self.add_trait(has_designator_prefix_defined("J"))
