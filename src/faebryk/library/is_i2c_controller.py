# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll


class is_i2c_controller(fabll.Node):
    """Trait marking an I2C interface as operating in controller (master) mode."""

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    is_immutable = fabll.Traits.MakeEdge(fabll.is_immutable.MakeChild()).put_on_type()
