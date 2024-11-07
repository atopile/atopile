# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from textwrap import indent

from faebryk.core.parameter import Parameter, _resolved
from faebryk.libs.units import UnitsContainer


class TBD(Parameter):
    @_resolved
    def __eq__(self, __value: object) -> bool:
        if isinstance(__value, TBD):
            return True

        return False

    def __hash__(self) -> int:
        return super().__hash__()

    def __repr__(self) -> str:
        o = self.get_most_narrow()
        if o is self:
            return super().__repr__()
        else:
            out = f"{super().__repr__():<80}    ===>    "
            or_ = repr(o)
            if "\n" in or_:
                out += indent(or_, len(out) * " ")
            else:
                out += or_

            return out

    def _as_unit(self, unit: UnitsContainer, base: int, required: bool) -> str:
        return "TBD" if required else ""
