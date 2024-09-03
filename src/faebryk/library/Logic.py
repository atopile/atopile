# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.libs.library import L


class Logic(F.Signal):
    state = L.f_field(F.Range)(False, True)

    def set(self, on: bool):
        self.state.merge(on)
