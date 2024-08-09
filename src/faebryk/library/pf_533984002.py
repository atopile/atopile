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


class pf_533984002(Module):
    def __init__(self) -> None:
        super().__init__()

        # interfaces
        class _IFs(Module.IFS()):
            pin = times(2, Electrical)
            mount = times(2, Electrical)

        self.IFs = _IFs(self)

        x = self.IFs
        self.add_trait(
            can_attach_to_footprint_via_pinmap(
                {
                    "1": x.pin[0],
                    "2": x.pin[1],
                    "3": x.mount[0],
                    "4": x.mount[1],
                }
            )
        )

        self.add_trait(
            has_datasheet_defined(
                "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/1912111437_SHOU-HAN-1-25-2P_C393945.pdf"
            )
        )

        self.add_trait(has_designator_prefix_defined("J"))
