import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.faebrykpy import EdgeInterfaceConnection


class App(fabll.Node):
    resistor = F.Resistor.MakeChild()
    diode = F.Diode.MakeChild()
    capacitor = F.Capacitor.MakeChild()

    resistor_resistance_constraint = F.Literals.Numbers.MakeChild_ConstrainToLiteral(
        [resistor, F.Resistor.resistance],
        min=1000.0,
        max=1000.0,
        unit=F.Units.Ohm,
    )
    diode_forward_voltage_constraint = F.Literals.Numbers.MakeChild_ConstrainToLiteral(
        [diode, F.Diode.forward_voltage],
        min=0.5,
        max=0.8,
        unit=F.Units.Volt,
    )
    capacitor_capacitance_constraint = F.Literals.Numbers.MakeChild_ConstrainToLiteral(
        [capacitor, F.Capacitor.capacitance],
        min=100.0,
        max=100.0,
        unit=F.Units.Farad,
    )
    capacitor_temperature_coefficient_constraint = (
        F.Literals.AbstractEnums.MakeChild_ConstrainToLiteral(
            [capacitor, F.Capacitor.temperature_coefficient],
            F.Capacitor.TemperatureCoefficient.X7S,
            F.Capacitor.TemperatureCoefficient.X7R,
        )
    )

    r2d = fabll.MakeEdge(
        [resistor, F.Resistor.unnamed[0]],
        [diode, F.Diode.anode],
        edge=EdgeInterfaceConnection.build(shallow=False),
    )
    r2c = fabll.MakeEdge(
        [resistor, F.Resistor.unnamed[1]],
        [capacitor, F.Capacitor.unnamed[0]],
        edge=EdgeInterfaceConnection.build(shallow=False),
    )
    d2c = fabll.MakeEdge(
        [diode, F.Diode.cathode],
        [capacitor, F.Capacitor.unnamed[1]],
        edge=EdgeInterfaceConnection.build(shallow=False),
    )

    F.Literals.Numbers.MakeChild_ConstrainToLiteral(
        [resistor, F.Resistor.resistance],
        min=1000.0,
        max=1000.0,
        unit=F.Units.Ohm,
    )


if __name__ == "__main__":
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    app = App.bind_typegraph(tg).create_instance(g=g)
    print(app.resistor.get().unnamed[0].get()._is_interface.get().get_connected())
    print(app.capacitor.get().unnamed[0].get()._is_interface.get().get_connected())
    print(app.diode.get().anode.get()._is_interface.get().get_connected())
    print(app.resistor.get().resistance.get().force_extract_literal().get_values())
    print(
        app.capacitor.get()
        .temperature_coefficient.get()
        .force_extract_literal()
        .get_values()
    )
