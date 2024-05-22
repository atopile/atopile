# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.library.Electrical import Electrical
from faebryk.library.has_designator_prefix_defined import (
    has_designator_prefix_defined,
)


class PJ398SM(Module):
    def __init__(self) -> None:
        super().__init__()

        class _IFs(Module.IFS()):
            tip = Electrical()
            sleeve = Electrical()
            switch = Electrical()

        self.IFs = _IFs(self)

        self.add_trait(has_designator_prefix_defined("P"))
