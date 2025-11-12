# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll


class Signal(fabll.Node):
    _is_interface = fabll.is_interface.MakeChild()
