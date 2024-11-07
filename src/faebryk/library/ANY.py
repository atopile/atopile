# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.parameter import Parameter
from faebryk.libs.units import UnitsContainer


class ANY(Parameter):
    """
    Allow parameter to take any value.
    Operations with this parameter automatically resolve to ANY too.
    Don't mistake with F.TBD.
    """

    def __eq__(self, __value: object) -> bool:
        if isinstance(__value, ANY):
            return True

        return False

    def __hash__(self) -> int:
        return super().__hash__()

    def _as_unit(self, unit: UnitsContainer, base: int, required: bool) -> str:
        return "ANY" if required else ""
