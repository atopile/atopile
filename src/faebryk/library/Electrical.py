# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

# import faebryk.library._F as F
import faebryk.core.node as fabll

# import faebryk.core.node as fabll

from faebryk.core.zig.gen.faebryk.typegraph import TypeGraph
from faebryk.core.zig.gen.graph.graph import GraphView


class Electrical(fabll.Node):
    """
    Electrical interface.
    """

    _is_interface = fabll.is_interface.MakeChild()

    # def get_net(self):
    #     from faebryk.library.Net import Net

    #     nets = {
    #         net
    #         for mif in self.get_connected()
    #         if (net := mif.get_parent_of_type(Net)) is not None
    #     }

    #     if not nets:
    #         return None

    #     assert len(nets) == 1
    #     return next(iter(nets))

    # def net_crosses_pad_boundary(self) -> bool:
    #     from faebryk.library.Pad import Pad

    #     def _get_pad(n: fabll.Node):
    #         if (parent := n.get_parent()) is None:
    #             return None


#         parent_node, name_on_parent = parent

#         return (
#             parent_node
#             if isinstance(parent_node, Pad) and name_on_parent == "net"
#             else None
#         )

#     net = self.get_connected().keys()
#     pads_on_net = {pad for n in net if (pad := _get_pad(n)) is not None}

#     return len(pads_on_net) > 1

# usage_example = fabll.f_field(F.has_usage_example)(
#     example="""
#     import Electrical, Resistor, Capacitor

#     # Basic electrical connection point
#     electrical1 = new Electrical
#     electrical2 = new Electrical

#     # Connect two electrical interfaces directly
#     electrical1 ~ electrical2

#     # Connect through components
#     resistor = new Resistor
#     resistor.resistance = 1kohm +/- 5%
#     electrical1 ~ resistor.unnamed[0]
#     resistor.unnamed[1] ~ electrical2

#     # Or using bridge syntax
#     electrical1 ~> resistor ~> electrical2

#     # Multiple connections to same net
#     capacitor = new Capacitor
#     electrical1 ~ capacitor.unnamed[0]
#     capacitor.unnamed[1] ~ electrical2
#     """,
#     language=F.has_usage_example.Language.ato,
# )

if __name__ == "__main__":
    g = GraphView.create()
    tg = TypeGraph.create(g=g)
    electricalType = Electrical.bind_typegraph(tg)
    e1 = electricalType.create_instance(g=g)
    e2 = electricalType.create_instance(g=g)
    e3 = electricalType.create_instance(g=g)

    e1.get_trait(fabll.is_interface).connect_to(e2, e3)

    print(e1.get_trait(fabll.is_interface).is_connected_to(e1))
    print(e1.get_trait(fabll.is_interface).is_connected_to(e2))
    print(e1.get_trait(fabll.is_interface).is_connected_to(e3))

    print(e1.get_trait(fabll.is_interface).get_connected())
