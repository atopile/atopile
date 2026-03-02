import faebryk.core.node as fabll
import faebryk.library._F as F


class Connector4Pin(fabll.Node):
    """
    A 4-pin connector with board_side (PCB pads) and wire_side (cable termination).
    Internal passthrough connects board_side[i] to wire_side[i].
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    board_side = [F.Electrical.MakeChild() for _ in range(4)]
    wire_side = [F.Electrical.MakeChild() for _ in range(4)]

    # Internal passthrough connections
    _conn_0 = fabll.is_interface.MakeConnectionEdge([board_side[0]], [wire_side[0]])
    _conn_1 = fabll.is_interface.MakeConnectionEdge([board_side[1]], [wire_side[1]])
    _conn_2 = fabll.is_interface.MakeConnectionEdge([board_side[2]], [wire_side[2]])
    _conn_3 = fabll.is_interface.MakeConnectionEdge([board_side[3]], [wire_side[3]])

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    _can_attach_to_footprint = fabll.Traits.MakeEdge(
        F.Footprints.can_attach_to_footprint.MakeChild()
    )

    designator_prefix = fabll.Traits.MakeEdge(
        F.has_designator_prefix.MakeChild(F.has_designator_prefix.Prefix.J)
    )

    # Leads for board-side pins (these get soldered to the PCB)
    for e in board_side:
        lead = fabll.Traits.MakeEdge(F.Lead.is_lead.MakeChild(), [e])
        lead.add_dependant(
            fabll.Traits.MakeEdge(F.Lead.can_attach_to_any_pad.MakeChild(), [lead])
        )
        e.add_dependant(lead)

    # Bridge: board_side[0] -> wire_side[0] for ~> chain support
    can_bridge = fabll.Traits.MakeEdge(
        F.can_bridge.MakeChild(["board_side[0]"], ["wire_side[0]"])
    )
