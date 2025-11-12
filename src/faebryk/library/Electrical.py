# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class Electrical(fabll.Node):
    """
    Electrical interface.
    """

    _is_interface = fabll._ChildField(fabll.is_interface)

    usage_example = F.has_usage_example.MakeChild(
        example="""
        import Electrical, Resistor, Capacitor

        # Basic electrical connection point
        electrical1 = new Electrical
        electrical2 = new Electrical

        # Connect two electrical interfaces directly
        electrical1 ~ electrical2

        # Connect through components
        resistor = new Resistor
        resistor.resistance = 1kohm +/- 5%
        electrical1 ~ resistor.unnamed[0]
        resistor.unnamed[1] ~ electrical2

        # Or using bridge syntax
        electrical1 ~> resistor ~> electrical2

        # Multiple connections to same net
        capacitor = new Capacitor
        electrical1 ~ capacitor.unnamed[0]
        capacitor.unnamed[1] ~ electrical2
        """,
        language=F.has_usage_example.Language.ato,
    ).put_on_type()
