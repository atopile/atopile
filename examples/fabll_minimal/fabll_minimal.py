import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.faebrykpy import EdgeInterfaceConnection as interface


class App(fabll.Node):
    cap1 = F.Capacitor.MakeChild()
    res1 = F.Resistor.MakeChild()
    res2 = F.Resistor.MakeChild()

    constraints = [
        F.Literals.Numbers.MakeChild_ConstrainToSubsetLiteral(
            [res1, F.Resistor.resistance], 200, 400, unit=F.Units.Ohm
        ),
        F.Literals.Numbers.MakeChild_ConstrainToSubsetLiteral(
            [res2, F.Resistor.resistance], 15, 40, unit=F.Units.Ohm
        )
    ]

    ep1 = F.ElectricPower.MakeChild()
    ep2 = F.ElectricPower.MakeChild()

    gnd = F.Electrical.MakeChild()

    connections = [
        fabll.MakeEdge([gnd], [res1, "unnamed[0]"], edge=interface.build(shallow=False)),
        fabll.MakeEdge([gnd], [res2, "unnamed[0]"], edge=interface.build(shallow=False)),
        fabll.MakeEdge([ep1, "hv"], [res1, "unnamed[1]"], edge=interface.build(shallow=False)),
        fabll.MakeEdge([ep2, "hv"], [res2, "unnamed[1]"], edge=interface.build(shallow=False)),
        fabll.MakeEdge([ep1, "lv"], [gnd], edge=interface.build(shallow=False)),
        fabll.MakeEdge([ep2, "lv"], [gnd], edge=interface.build(shallow=False)),
    ]

    res3 = F.Resistor.MakeChild()
    diff_pair = F.DifferentialPair.MakeChild()

    connections2 = [
        fabll.MakeEdge([diff_pair, "p", "line"], [res3, "unnamed[0]"], edge=interface.build(shallow=False)),
        fabll.MakeEdge([diff_pair, "n", "line"], [res3, "unnamed[1]"], edge=interface.build(shallow=False)),
    ]