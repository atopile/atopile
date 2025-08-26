# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.node import Node
from faebryk.libs.library import L


class Electrical(ModuleInterface):
    """
    Electrical interface.
    """

    # potential= L.p_field(units=P.dimensionless)

    def get_net(self):
        from faebryk.library.Net import Net

        nets = {
            net
            for mif in self.get_connected()
            if (net := mif.get_parent_of_type(Net)) is not None
        }

        if not nets:
            return None

        assert len(nets) == 1
        return next(iter(nets))

    def net_crosses_pad_boundary(self) -> bool:
        from faebryk.library.Pad import Pad

        def _get_pad(n: Node):
            if (parent := n.get_parent()) is None:
                return None

            parent_node, name_on_parent = parent

            return (
                parent_node
                if isinstance(parent_node, Pad) and name_on_parent == "net"
                else None
            )

        net = self.get_connected().keys()
        pads_on_net = {pad for n in net if (pad := _get_pad(n)) is not None}

        return len(pads_on_net) > 1

    usage_example = L.f_field(F.has_usage_example)(
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
    )
