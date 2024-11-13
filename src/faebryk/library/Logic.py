# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.libs.library import L  # noqa: F401


class Logic(F.Signal):
    """
    Acts as protocol, because multi inheritance is not supported
    """

    # state = L.p_field(domain=L.Domains.BOOL())

    def set(self, on: bool):
        # self.state.constrain_subset(on)
        ...
