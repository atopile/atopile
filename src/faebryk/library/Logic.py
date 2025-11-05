# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll  # noqa: F401
import faebryk.library._F as F


class Logic(fabll.Node):
    """
    Acts as protocol, because multi inheritance is not supported
    """
    _is_interface = fabll.is_interface.MakeChild()

    # state = fabll.p_field(domain=fabll.Domains.BOOL())

    def set(self, on: bool):
        # self.state.constrain_subset(on)
        ...
