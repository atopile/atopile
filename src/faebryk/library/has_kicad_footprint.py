# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

from faebryk.library.FootprintTrait import FootprintTrait
from faebryk.library.Pad import Pad


class has_kicad_footprint(FootprintTrait):
    @abstractmethod
    def get_kicad_footprint(self) -> str: ...

    @abstractmethod
    def get_pin_names(self) -> dict[Pad, str]: ...

    def get_kicad_footprint_name(self) -> str:
        return self.get_kicad_footprint().split(":")[-1]
