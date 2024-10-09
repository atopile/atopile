# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.libs.library import L


class Logic(F.Signal):
    state = L.p_field(domain=L.Domains.BOOL())

    def set(self, on: bool):
        self.state.constrain_subset(L.Single(on))
