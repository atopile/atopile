# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


class Regulator(fabll.Node):
    """
    Base voltage regulator module with input and output power interfaces.

    This is intended to be extended by specific regulator implementations
    (LDO, buck, boost, buck-boost, etc.)
    """

    is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    # External interfaces
    power_in = F.ElectricPower.MakeChild()
    """Input power interface"""

    power_out = F.ElectricPower.MakeChild()
    """Regulated output power interface"""

    # Mark as bridgeable between power_in and power_out
    _can_bridge = fabll.Traits.MakeEdge(
        F.can_bridge.MakeChild(["power_in"], ["power_out"])
    )

    # Backwards compatibility aliases - v_in and v_out are aliases
    # to power_in.voltage and power_out.voltage respectively
    v_in = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)
    v_out = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)

    _connections = [
        fabll.is_interface.MakeConnectionEdge(
            [v_in], [power_in, F.ElectricPower.voltage]
        ),
        fabll.is_interface.MakeConnectionEdge(
            [v_out], [power_out, F.ElectricPower.voltage]
        ),
    ]
