# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import ModuleInterface
from faebryk.library.Electrical import Electrical


class SPI(ModuleInterface):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        class _NODEs(ModuleInterface.NODES()):
            sclk = Electrical()
            miso = Electrical()
            mosi = Electrical()
            gnd = Electrical()

        self.NODEs = _NODEs(self)
