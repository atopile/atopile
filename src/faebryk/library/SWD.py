# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import ModuleInterface
from faebryk.library.Electrical import Electrical


class SWD(ModuleInterface):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        class _NODEs(ModuleInterface.NODES()):
            clk = Electrical()
            dio = Electrical()
            gnd = Electrical()

        self.NODEs = _NODEs(self)
