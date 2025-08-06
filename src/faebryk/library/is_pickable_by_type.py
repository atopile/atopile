# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
import faebryk.libs.library.L as L
from faebryk.core.parameter import Parameter


class is_pickable_by_type(F.is_pickable.decless()):
    def get_pick_type(self) -> type[L.Module]:
        return type(self.get_obj(L.Module))

    def get_parameters(self) -> dict[str, Parameter]:
        obj = self.get_obj(L.Module)
        params = obj.get_children(direct_only=True, types=(Parameter,))
        return {p.get_name(): p for p in params if p.used_for_picking}
