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


class has_bus_spec(fabll.Node):
    """
    Type-level protocol spec for bus interfaces.

    Describes the topology, data flow, and multi-controller support
    of a bus protocol (e.g., I2C, SPI, UART).
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
        # From ato: topology=[BUS], data_flow=HALF_DUPLEX, multi_controller=True
        # From Python: topology=[has_bus_spec.Topology.BUS],
        # data_flow=has_bus_spec.DataFlow.HALF_DUPLEX, multi_controller=True
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

        # Get all has_bus_spec traits from connected interfaces
        specs = []
        for iface in interfaces:
            if iface.has_trait(has_bus_spec):
                specs.append(iface.get_trait(has_bus_spec))

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
    def resolve_bus_spec_parameters(g: graph.GraphView, tg: fbrk.TypeGraph):
        """
        Find all has_bus_spec implementors, group interfaces into buses,
        and create Is constraints across each bus.
        Called from build_steps.py during SETUP alongside resolve_bus_parameters().
        """
        implementors = list(
            fabll.Traits.get_implementors(has_bus_spec.bind_typegraph(tg), g=g)
        )

        if not implementors:
            return

        # Group implementors by their owner interface
        interface_specs: dict[fabll.Node, has_bus_spec] = {}
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


class has_bus_role(fabll.Node):
    """
    Instance-level role marker for bus interfaces.

    Marks an individual bus interface instance with its role
    (e.g., CONTROLLER, TARGET, NODE).
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    class BusRole(Enum):
        CONTROLLER = auto()
        TARGET = auto()
        NODE = auto()
        END_NODE = auto()
        PASSIVE = auto()

    role_ = F.Parameters.EnumParameter.MakeChild(enum_t=BusRole)

    @classmethod
    def MakeChild(cls, role: str | list[BusRole]) -> fabll._ChildField[Any]:
        # From ato: role="CONTROLLER" or role="CONTROLLER,TARGET"
        # From Python: role=[BusRole.CONTROLLER]
        if isinstance(role, str):
            role = [cls.BusRole[r.strip()] for r in role.split(",")]
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.AbstractEnums.MakeChild_SetSuperset(
                [out, cls.role_],
                *role,
            )
        )
        return out

    def get_roles(self) -> set[BusRole]:
        lit = self.role_.get().try_extract_superset()
        if lit is None:
            return set()
        return set(lit.get_values_typed(self.BusRole))


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
                has_bus_spec.MakeChild(
                    topology=[has_bus_spec.Topology.BUS],
                    data_flow=has_bus_spec.DataFlow.HALF_DUPLEX,
                    multi_controller=True,
                )
            )

        inst = _Host.bind_typegraph(tg).create_instance(g=g)
        spec = inst.get_trait(has_bus_spec)

        assert spec.get_topology_values() == {has_bus_spec.Topology.BUS}
        assert spec.get_data_flow() == has_bus_spec.DataFlow.HALF_DUPLEX
        assert spec.get_multi_controller() is True

    def test_bus_spec_multi_topology(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class _Host(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            bus_spec = fabll.Traits.MakeEdge(
                has_bus_spec.MakeChild(
                    topology=[has_bus_spec.Topology.STAR, has_bus_spec.Topology.TREE],
                    data_flow=has_bus_spec.DataFlow.FULL_DUPLEX,
                    multi_controller=False,
                )
            )

        inst = _Host.bind_typegraph(tg).create_instance(g=g)
        spec = inst.get_trait(has_bus_spec)

        assert spec.get_topology_values() == {
            has_bus_spec.Topology.STAR,
            has_bus_spec.Topology.TREE,
        }
        assert spec.get_data_flow() == has_bus_spec.DataFlow.FULL_DUPLEX
        assert spec.get_multi_controller() is False

    def test_bus_role_roundtrip(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class _Host(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            _bus_role = fabll.Traits.MakeEdge(
                has_bus_role.MakeChild(role=[has_bus_role.BusRole.CONTROLLER])
            )

        inst = _Host.bind_typegraph(tg).create_instance(g=g)
        role = inst.get_trait(has_bus_role)

        assert role.get_roles() == {has_bus_role.BusRole.CONTROLLER}

    def test_bus_role_multi_role(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class _Host(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            _bus_role = fabll.Traits.MakeEdge(
                has_bus_role.MakeChild(
                    role=[has_bus_role.BusRole.CONTROLLER, has_bus_role.BusRole.TARGET]
                )
            )

        inst = _Host.bind_typegraph(tg).create_instance(g=g)
        role = inst.get_trait(has_bus_role)

        assert role.get_roles() == {
            has_bus_role.BusRole.CONTROLLER,
            has_bus_role.BusRole.TARGET,
        }

    def test_bus_spec_aliasing(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class _I2CLike(fabll.Node):
            scl = F.Electrical.MakeChild()
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            bus_spec = fabll.Traits.MakeEdge(
                has_bus_spec.MakeChild(
                    topology=[has_bus_spec.Topology.BUS],
                    data_flow=has_bus_spec.DataFlow.HALF_DUPLEX,
                    multi_controller=True,
                )
            )

        a = _I2CLike.bind_typegraph(tg).create_instance(g=g)
        b = _I2CLike.bind_typegraph(tg).create_instance(g=g)

        a._is_interface.get().connect_to(b)

        has_bus_spec.resolve_bus_spec_parameters(g, tg)

        spec_a = a.get_trait(has_bus_spec)
        spec_b = b.get_trait(has_bus_spec)

        assert spec_a.get_topology_values() == {has_bus_spec.Topology.BUS}
        assert spec_b.get_topology_values() == {has_bus_spec.Topology.BUS}
        assert spec_a.get_multi_controller() is True
        assert spec_b.get_multi_controller() is True
