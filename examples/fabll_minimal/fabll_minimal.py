import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F


class App(fabll.Node):
    res1 = F.Resistor.MakeChild()
    res2 = F.Resistor.MakeChild()

    cap1 = F.Capacitor.MakeChild()

    r2r = fabll.MakeEdge(
        [res1, F.Resistor.unnamed[0]],
        [res2, F.Resistor.unnamed[1]],
        edge=fbrk.EdgeInterfaceConnection.build(shallow=False),
    )

    res1_constraint = F.Literals.Numbers.MakeChild_ConstrainToSubsetLiteral(
        [res1, F.Resistor.resistance], 200, 400, unit=F.Units.Ohm
    )
    res2_constraint = F.Literals.Numbers.MakeChild_ConstrainToSubsetLiteral(
        [res2, F.Resistor.resistance], 15, 40, unit=F.Units.Ohm
    )

    ep1 = F.ElectricPower.MakeChild()
    ep2 = F.ElectricPower.MakeChild()

    connections = [
        fabll.MakeEdge([ep1, "lv"], [res1, "unnamed[0]"], edge=fbrk.EdgeInterfaceConnection.build(shallow=False)),
        fabll.MakeEdge([ep1, "hv"], [res1, "unnamed[1]"], edge=fbrk.EdgeInterfaceConnection.build(shallow=False)),
        fabll.MakeEdge([ep2, "lv"], [res2, "unnamed[0]"], edge=fbrk.EdgeInterfaceConnection.build(shallow=False)),
        fabll.MakeEdge([ep2, "hv"], [res2, "unnamed[1]"], edge=fbrk.EdgeInterfaceConnection.build(shallow=False)),
    ]

