import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F


class App(fabll.Node):
    r1 = F.Resistor.MakeChild()
    r2 = F.Resistor.MakeChild()

    x = fabll.MakeEdge(
        lhs=[r1, F.Resistor.unnamed[0]],
        rhs=[r2, F.Resistor.unnamed[1]],
        edge=fbrk.EdgeInterfaceConnection.build(shallow=False)
    )