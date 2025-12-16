import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.faebrykpy import EdgeInterfaceConnection as interface


class App(fabll.Node):
    diode = F.Diode.MakeChild()
    diode.add_dependant(
        fabll.Traits.MakeEdge(
            F.is_pickable_by_supplier_id.MakeChild(supplier_part_id="C64885"),
            owner=[diode],
        )
    )

    cap1 = F.Capacitor.MakeChild()

    res1 = F.Resistor.MakeChild()
    res2 = F.Resistor.MakeChild()

    res3 = F.Resistor.MakeChild()
    res4 = F.Resistor.MakeChild()

    diff_pair = F.DifferentialPair.MakeChild()

    i2c = F.I2C.MakeChild()

    can = F.CAN.MakeChild()

    constraints = [
        F.Literals.Numbers.MakeChild_ConstrainToSubsetLiteral(
            [res1, F.Resistor.resistance], 200, 400, unit=F.Units.Ohm
        ),
        F.Literals.Numbers.MakeChild_ConstrainToSubsetLiteral(
            [res2, F.Resistor.resistance], 15, 40, unit=F.Units.Ohm
        ),
    ]

    power_5v = F.ElectricPower.MakeChild()
    power_3v3 = F.ElectricPower.MakeChild()
    gnd = F.Electrical.MakeChild()

    net_names = [
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="GND", level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[gnd],
        ),
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="+5V", level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[power_5v, "hv"],
        ),
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="+3.3V", level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[power_3v3, "hv"],
        ),
    ]

    reference_connections = [
        fabll.MakeEdge([power_5v, "lv"], [gnd], edge=interface.build(shallow=False)),
        fabll.MakeEdge([power_3v3, "lv"], [gnd], edge=interface.build(shallow=False)),
        fabll.MakeEdge(
            [diff_pair, "reference"], [gnd], edge=interface.build(shallow=False)
        ),
    ]

    resistor_connections = [
        fabll.MakeEdge(
            [res1, "unnamed[0]"], [gnd], edge=interface.build(shallow=False)
        ),
        fabll.MakeEdge(
            [res2, "unnamed[0]"], [gnd], edge=interface.build(shallow=False)
        ),
        fabll.MakeEdge(
            [res1, "unnamed[1]"], [power_5v, "hv"], edge=interface.build(shallow=False)
        ),
        fabll.MakeEdge(
            [res2, "unnamed[1]"], [power_3v3, "hv"], edge=interface.build(shallow=False)
        ),
    ]

    connections2 = [
        fabll.MakeEdge(
            [diff_pair, "p", "line"],
            [res3, "unnamed[0]"],
            edge=interface.build(shallow=False),
        ),
        fabll.MakeEdge(
            [diff_pair, "p", "reference", "lv"],
            [res3, "unnamed[1]"],
            edge=interface.build(shallow=False),
        ),
        fabll.MakeEdge(
            [diff_pair, "n", "line"],
            [res4, "unnamed[0]"],
            edge=interface.build(shallow=False),
        ),
        fabll.MakeEdge(
            [diff_pair, "n", "reference", "lv"],
            [res4, "unnamed[1]"],
            edge=interface.build(shallow=False),
        ),
    ]
