# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import Enum, auto
from typing import Any

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.util import once

logger = logging.getLogger(__name__)


class has_databus_specification(fabll.Node):
    """
    Type-level specification for data bus interfaces.

    Describes the topology, data flow, and multi-controller support of a data bus.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    is_immutable = fabll.Traits.MakeEdge(fabll.is_immutable.MakeChild()).put_on_type()

    class Topology(Enum):
        POINT_TO_POINT = auto()
        BUS = auto()
        STAR = auto()
        DAISY_CHAIN = auto()
        RING = auto()
        MESH = auto()
        TREE = auto()

    class DataFlow(Enum):
        SIMPLEX = auto()
        HALF_DUPLEX = auto()
        FULL_DUPLEX = auto()

    topology_ = F.Parameters.EnumParameter.MakeChild(enum_t=Topology)
    data_flow_ = F.Parameters.EnumParameter.MakeChild(enum_t=DataFlow)
    multi_controller_ = F.Parameters.BooleanParameter.MakeChild()

    @classmethod
    def MakeChild(
        cls,
        topology: str | list[Topology],
        data_flow: DataFlow,
        multi_controller: bool,
    ) -> fabll._ChildField[Any]:
        if isinstance(topology, str):
            topology = [cls.Topology[t.strip()] for t in topology.split(",")]
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.AbstractEnums.MakeChild_SetSuperset(
                [out, cls.topology_],
                *topology,
            )
        )
        out.add_dependant(
            F.Literals.AbstractEnums.MakeChild_SetSuperset(
                [out, cls.data_flow_],
                data_flow,
            )
        )
        out.add_dependant(
            F.Literals.Booleans.MakeChild_SetSuperset(
                [out, cls.multi_controller_],
                multi_controller,
            )
        )
        return out

    def get_topology_values(self) -> set[Topology]:
        lit = self.topology_.get().try_extract_superset()
        if lit is None:
            return set()
        return set(lit.get_values_typed(self.Topology))

    def get_data_flow(self) -> DataFlow | None:
        return self.data_flow_.get().try_extract_singleton_typed(self.DataFlow)

    def get_multi_controller(self) -> bool | None:
        return self.multi_controller_.get().try_extract_singleton()

    def resolve(self, interfaces: set[fabll.Node]):
        """Create Is constraints for bus spec params across connected interfaces."""
        if len(interfaces) < 2:
            return

        g = self.g
        tg = self.tg

        # Get all has_databus_specification traits from connected interfaces
        specs = []
        for iface in interfaces:
            if iface.has_trait(has_databus_specification):
                specs.append(iface.get_trait(has_databus_specification))

        if len(specs) < 2:
            return

        first = specs[0]
        for other in specs[1:]:
            # Alias topology
            F.Expressions.Is.c(
                first.topology_.get().get_trait(F.Parameters.can_be_operand),
                other.topology_.get().get_trait(F.Parameters.can_be_operand),
                g=g,
                tg=tg,
                assert_=True,
            )
            # Alias data_flow
            F.Expressions.Is.c(
                first.data_flow_.get().get_trait(F.Parameters.can_be_operand),
                other.data_flow_.get().get_trait(F.Parameters.can_be_operand),
                g=g,
                tg=tg,
                assert_=True,
            )
            # Alias multi_controller
            F.Expressions.Is.c(
                first.multi_controller_.get().get_trait(F.Parameters.can_be_operand),
                other.multi_controller_.get().get_trait(F.Parameters.can_be_operand),
                g=g,
                tg=tg,
                assert_=True,
            )

    @staticmethod
    @once
    def resolve_data_bus_specification_parameters(
        g: graph.GraphView, tg: fbrk.TypeGraph
    ):
        """
        Find all DataBus.has_specification implementors, group interfaces into buses,
        and create Is constraints across each bus.
        Called from build_steps.py during SETUP alongside
        resolve_data_bus_specification_parameters().
        """
        implementors = list(
            fabll.Traits.get_implementors(
                has_databus_specification.bind_typegraph(tg), g=g
            )
        )

        if not implementors:
            return

        # Group implementors by their owner interface type
        interface_specs: dict[fabll.Node, has_databus_specification] = {}
        for impl in implementors:
            owner = fabll.Traits(impl).get_obj_raw()
            interface_specs[owner] = impl

        # Group interfaces into buses
        buses = fabll.is_interface.group_into_buses(interface_specs.keys())

        processed: set[frozenset[fabll.Node]] = set()
        for bus_interfaces in buses.values():
            bus_id = frozenset(bus_interfaces)
            if bus_id in processed:
                continue
            processed.add(bus_id)

            # Find a representative spec from this bus
            for iface in bus_interfaces:
                if iface in interface_specs:
                    interface_specs[iface].resolve(bus_interfaces)
                    break


class has_databus_role(fabll.Node):
    """
    Role marker for data bus interfaces.

    Marks an individual data bus interface instance with its role
    (e.g., CONTROLLER, TARGET, NODE).
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    class Role(Enum):
        CONTROLLER = auto()
        TARGET = auto()
        NODE = auto()
        END_NODE = auto()
        PASSIVE = auto()

    role_ = F.Parameters.EnumParameter.MakeChild(enum_t=Role)

    @classmethod
    def MakeChild(cls, role: str | list[Role]) -> fabll._ChildField[Any]:
        # From ato: role="CONTROLLER" or role="CONTROLLER,TARGET"
        # From Python: role=[BusRole.CONTROLLER]
        if isinstance(role, str):
            role = [cls.Role[r.strip()] for r in role.split(",")]
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.AbstractEnums.MakeChild_SetSuperset(
                [out, cls.role_],
                *role,
            )
        )
        return out

    def get_roles(self) -> set[Role]:
        lit = self.role_.get().try_extract_superset()
        if lit is None:
            return set()
        return set(lit.get_values_typed(self.Role))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class Test:
    def test_bus_spec_roundtrip(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class _Host(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            bus_spec = fabll.Traits.MakeEdge(
                has_databus_specification.MakeChild(
                    topology=[has_databus_specification.Topology.BUS],
                    data_flow=has_databus_specification.DataFlow.HALF_DUPLEX,
                    multi_controller=True,
                )
            )

        inst = _Host.bind_typegraph(tg).create_instance(g=g)
        spec = inst.get_trait(has_databus_specification)

        assert spec.get_topology_values() == {has_databus_specification.Topology.BUS}
        assert spec.get_data_flow() == has_databus_specification.DataFlow.HALF_DUPLEX
        assert spec.get_multi_controller() is True

    def test_bus_spec_multi_topology(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class _Host(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            bus_spec = fabll.Traits.MakeEdge(
                has_databus_specification.MakeChild(
                    topology=[
                        has_databus_specification.Topology.STAR,
                        has_databus_specification.Topology.TREE,
                    ],
                    data_flow=has_databus_specification.DataFlow.FULL_DUPLEX,
                    multi_controller=False,
                )
            )

        inst = _Host.bind_typegraph(tg).create_instance(g=g)
        spec = inst.get_trait(has_databus_specification)

        assert spec.get_topology_values() == {
            has_databus_specification.Topology.STAR,
            has_databus_specification.Topology.TREE,
        }
        assert spec.get_data_flow() == has_databus_specification.DataFlow.FULL_DUPLEX
        assert spec.get_multi_controller() is False

    def test_bus_role_roundtrip(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class _Host(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            _bus_role = fabll.Traits.MakeEdge(
                has_databus_role.MakeChild(role=[has_databus_role.Role.CONTROLLER])
            )

        inst = _Host.bind_typegraph(tg).create_instance(g=g)
        role = inst.get_trait(has_databus_role)

        assert role.get_roles() == {has_databus_role.Role.CONTROLLER}

    def test_bus_role_multi_role(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class _Host(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            _bus_role = fabll.Traits.MakeEdge(
                has_databus_role.MakeChild(
                    role=[
                        has_databus_role.Role.CONTROLLER,
                        has_databus_role.Role.TARGET,
                    ]
                )
            )

        inst = _Host.bind_typegraph(tg).create_instance(g=g)
        role = inst.get_trait(has_databus_role)

        assert role.get_roles() == {
            has_databus_role.Role.CONTROLLER,
            has_databus_role.Role.TARGET,
        }

    def test_bus_spec_aliasing(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class _I2CLike(fabll.Node):
            scl = F.Electrical.MakeChild()
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            bus_spec = fabll.Traits.MakeEdge(
                has_databus_specification.MakeChild(
                    topology=[has_databus_specification.Topology.BUS],
                    data_flow=has_databus_specification.DataFlow.HALF_DUPLEX,
                    multi_controller=True,
                )
            )

        a = _I2CLike.bind_typegraph(tg).create_instance(g=g)
        b = _I2CLike.bind_typegraph(tg).create_instance(g=g)

        a._is_interface.get().connect_to(b)

        has_databus_specification.resolve_data_bus_specification_parameters(g, tg)

        spec_a = a.get_trait(has_databus_specification)
        spec_b = b.get_trait(has_databus_specification)

        assert spec_a.get_topology_values() == {has_databus_specification.Topology.BUS}
        assert spec_b.get_topology_values() == {has_databus_specification.Topology.BUS}
        assert spec_a.get_multi_controller() is True
        assert spec_b.get_multi_controller() is True
