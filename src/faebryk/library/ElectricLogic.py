# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Iterable

from faebryk.core.core import Module, ModuleInterface, Node
from faebryk.core.util import connect_all_interfaces
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_single_electric_reference import has_single_electric_reference
from faebryk.library.has_single_electric_reference_defined import (
    has_single_electric_reference_defined,
)
from faebryk.library.Logic import Logic


class ElectricLogic(Logic):
    def __init__(self) -> None:
        super().__init__()

        class NODES(Logic.NODES()):
            reference = ElectricPower()
            signal = Electrical()

        self.NODEs = NODES(self)

        self.add_trait(has_single_electric_reference_defined(self.NODEs.reference))

    def connect_to_electric(self, signal: Electrical, reference: ElectricPower):
        self.NODEs.reference.connect(reference)
        self.NODEs.signal.connect(signal)
        return self

    def connect_references(self, other: "ElectricLogic"):
        self.NODEs.reference.connect(other.NODEs.reference)

    def pull_down(self, resistor):
        from faebryk.library.Resistor import Resistor

        assert isinstance(resistor, Resistor)
        self.NODEs.signal.connect_via(resistor, self.NODEs.reference.NODEs.lv)

    def pull_up(self, resistor):
        from faebryk.library.Resistor import Resistor

        assert isinstance(resistor, Resistor)
        self.NODEs.signal.connect_via(resistor, self.NODEs.reference.NODEs.hv)

    def set(self, on: bool):
        r = self.NODEs.reference.NODEs
        self.NODEs.signal.connect(r.hv if on else r.lv)

    @staticmethod
    def connect_all_references(ifs: Iterable["ElectricLogic"]) -> ElectricPower:
        return connect_all_interfaces([x.NODEs.reference for x in ifs])

    @staticmethod
    def connect_all_node_references(
        nodes: Iterable[Node], gnd_only=False
    ) -> ElectricPower:
        refs = [
            x.get_trait(has_single_electric_reference).get_reference()
            for x in nodes
            if x.has_trait(has_single_electric_reference)
        ]
        if gnd_only:
            return connect_all_interfaces([r.NODEs.lv for r in refs])
        return connect_all_interfaces(refs)

    @classmethod
    def connect_all_module_references(
        cls, node: Module | ModuleInterface, gnd_only=False
    ) -> ElectricPower:
        return cls.connect_all_node_references(
            # TODO ugly
            node.NODEs.get_all()
            if isinstance(node, ModuleInterface)
            else node.IFs.get_all(),
            gnd_only=gnd_only,
        )
