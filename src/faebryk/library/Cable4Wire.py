import faebryk.core.node as fabll
import faebryk.library._F as F


class Cable4Wire(fabll.Node):
    """
    A 4-conductor cable with end_a and end_b interfaces.
    Internal passthrough connects end_a[i] to end_b[i].
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    end_a = [F.Electrical.MakeChild() for _ in range(4)]
    end_b = [F.Electrical.MakeChild() for _ in range(4)]

    length = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)

    # Internal passthrough connections
    _conn_0 = fabll.is_interface.MakeConnectionEdge([end_a[0]], [end_b[0]])
    _conn_1 = fabll.is_interface.MakeConnectionEdge([end_a[1]], [end_b[1]])
    _conn_2 = fabll.is_interface.MakeConnectionEdge([end_a[2]], [end_b[2]])
    _conn_3 = fabll.is_interface.MakeConnectionEdge([end_a[3]], [end_b[3]])

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    # Bridge: end_a[0] -> end_b[0] for ~> chain support
    can_bridge = fabll.Traits.MakeEdge(
        F.can_bridge.MakeChild(["end_a[0]"], ["end_b[0]"])
    )
