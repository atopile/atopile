# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile import errors
from faebryk.libs.app.checks import check_design
from faebryk.libs.exceptions import accumulate

logger = logging.getLogger(__name__)


class ERCFault(errors.UserException):
    """Base class for ERC faults."""


class ERCFaultShort(ERCFault):
    """Exception raised for short circuits."""


class ERCFaultShortedInterfaces(ERCFaultShort):
    """Short circuit between two Interfaces."""

    def __init__(self, msg: str, path: fabll.Path, *args: object) -> None:
        super().__init__(msg, path, *args, markdown=False)
        self.path = path

    @classmethod
    def from_path(cls, path: fabll.Path) -> "ERCFaultShortedInterfaces":
        """
        Given two shorted Interfaces, return an exception that describes the
        narrowest path for the fault.
        """

        start = path.get_start_node().pretty_repr()
        end = path.get_end_node().pretty_repr()
        return cls(
            f"Shorted:\t{start} -> {end}\nFull path:\t{path.pretty_repr()}", path
        )


class ERCFaultElectricPowerUndefinedVoltage(ERCFault):
    def __init__(self, faulting_EP: "F.ElectricPower", *args: object) -> None:
        msg = (
            f"ElectricPower with undefined or unsolved voltage: {faulting_EP}:"
            f" {faulting_EP.voltage}"
        )
        super().__init__(msg, [faulting_EP], *args)


class ERCPowerSourcesShortedError(ERCFault):
    """
    Multiple power sources shorted together
    """


class ERCFaultIncompatibleInterfaceConnection(ERCFault):
    """
    Raised when two interfaces with incompatible types are connected.
    E.g., connecting ElectricPower directly to Electrical.
    """

    def __init__(
        self,
        msg: str,
        source_node: fabll.Node,
        target_node: fabll.Node,
        source_type: str,
        target_type: str,
        *args: object,
    ) -> None:
        super().__init__(msg, [source_node, target_node], *args, markdown=False)
        self.source_node = source_node
        self.target_node = target_node
        self.source_type = source_type
        self.target_type = target_type

    @classmethod
    def from_nodes(
        cls,
        source: fabll.Node,
        target: fabll.Node,
        source_type: str,
        target_type: str,
    ) -> "ERCFaultIncompatibleInterfaceConnection":
        """Create an exception for incompatible interface connection."""
        return cls(
            f"Incompatible interface types connected:\n"
            f"  {source.pretty_repr()} ({source_type})\n"
            f"    -> {target.pretty_repr()} ({target_type})",
            source,
            target,
            source_type,
            target_type,
        )


# TODO split this up
class needs_erc_check(fabll.Node):
    """
    Implement checks:
    - shorted interfaces:
        - ElectricPower (hv and lv)
    - shorted components:
        - Capacitor (unnamed[0] and unnamed[1])
        - Resistor (unnamed[0] and unnamed[1])
        - Fuse (unnamed[0] and unnamed[1])
    - shorted nets
    - net name collisions

    TODO
    - shorted ElectricPower sources
    - shorted symmetric footprints
    - [unmapped pins for footprints]
    """

    is_trait = fabll._ChildField(fabll.ImplementsTrait).put_on_type()
    design_check = fabll.Traits.MakeEdge(F.implements_design_check.MakeChild())

    @F.implements_design_check.register_post_design_verify_check
    def __check_post_design_verify__(self):
        """
        Early validation of graph structure before any BFS traversal.

        This runs FIRST to catch malformed EdgeInterfaceConnections that would
        cause hangs in later checks (like requires_external_usage which uses BFS).
        """
        logger.info("Verifying interface connection graph structure")
        with accumulate(ERCFault) as accumulator:
            self._verify_interface_connections(accumulator)

    @F.implements_design_check.register_post_design_check
    def __check_post_design__(self):
        logger.info("Checking for ERC violations")
        with accumulate(ERCFault) as accumulator:
            self._check_interface_connection_types(accumulator)
            self._check_shorted_interfaces_and_components()
            self._check_shorted_nets(accumulator)
            self._check_shorted_electric_power_sources(accumulator)
            self._check_additional_heuristics()

    def _check_shorted_interfaces_and_components(self) -> None:
        comps = fabll.Node.bind_typegraph(self.tg).nodes_of_types(
            (F.Resistor, F.Capacitor, F.Fuse, F.ElectricPower)
        )
        logger.info(f"Checking {len(comps)} elements for shorts")

        electrical_instances = {
            elec
            for comp in comps
            for elec in comp.get_children(direct_only=True, types=F.Electrical)
        }

        electrical_buses = fabll.is_interface.group_into_buses(electrical_instances)

        logger.info(
            "Grouped %s electricals into %s buses",
            len(electrical_instances),
            len(electrical_buses),
        )

        for comp in comps:
            if isinstance(comp, F.ElectricPower):
                e1 = comp.hv.get()
                e2 = comp.lv.get()
            else:
                e1 = comp.unnamed[0].get()
                e2 = comp.unnamed[1].get()
            if any(e1 in bus and e2 in bus for bus in electrical_buses.values()):
                path = fabll.Path.from_connection(e1, e2)
                assert path is not None
                raise ERCFaultShortedInterfaces.from_path(path)

    def _check_shorted_nets(self, accumulator: accumulate) -> None:
        nets = F.Net.bind_typegraph(self.tg).get_instances(g=self.tg.get_graph_view())
        logger.info(f"Checking {len(nets)} explicit nets")
        for net in nets:
            with accumulator.collect():
                nets_on_bus = F.Net.find_nets_for_mif(net.part_of.get())

                named_collisions = {
                    neighbor_net
                    for neighbor_net in nets_on_bus
                    if neighbor_net.has_trait(F.has_net_name)
                }

                if named_collisions:
                    friendly_shorted = ", ".join(
                        n.get_full_name() for n in named_collisions
                    )
                    raise ERCFaultShort(f"Shorted nets: {friendly_shorted}")

    def _check_shorted_electric_power_sources(self, accumulator: accumulate) -> None:
        # shorted power
        electricpower = F.ElectricPower.bind_typegraph(self.tg).get_instances(
            g=self.tg.get_graph_view()
        )
        ep_buses = fabll.is_interface.group_into_buses(electricpower)

        # We do collection both inside and outside the loop because we don't
        # want to continue the loop if we've already raised a short exception
        with accumulator.collect():
            logger.info("Checking for power source shorts")
            for ep_bus in ep_buses.values():
                with accumulator.collect():
                    sources = {ep for ep in ep_bus if ep.has_trait(F.is_source)}
                    if len(sources) <= 1:
                        continue

                    friendly_sources = ", ".join(n.get_full_name() for n in sources)
                    raise ERCPowerSourcesShortedError(
                        f"Power sources shorted: {friendly_sources}"
                    )

    def _verify_interface_connections(self, accumulator: accumulate) -> None:
        """
        Verify that all EdgeInterfaceConnections are between is_interface nodes.

        This runs BEFORE any BFS traversal to catch malformed connections like
        `power.lv ~ resistor` (interface to non-interface) that would cause hangs.

        This is a lightweight check that doesn't traverse the graph - it just
        validates edge endpoints.
        """
        g = self.tg.get_graph_view()
        edge_tid = fbrk.EdgeInterfaceConnection.get_tid()

        # Get the is_interface type to find all nodes with the trait
        is_interface_type = self.tg.get_type_by_name(
            type_identifier="is_interface.node.core.faebryk"
        )
        if is_interface_type is None:
            logger.debug("No is_interface type found, skipping verification")
            return

        # Get all nodes that implement is_interface
        interface_nodes: list[graph.BoundNode] = []

        def collect_implementer(
            ctx: list[graph.BoundNode], node: graph.BoundNode
        ) -> None:
            ctx.append(node)

        fbrk.Trait.visit_implementers(
            trait_type=is_interface_type, ctx=interface_nodes, f=collect_implementer
        )

        # Build set of interface node UUIDs for O(1) lookup
        interface_uuids: set[int] = {node.node().get_uuid() for node in interface_nodes}

        # Check all edges from interface nodes
        edges_checked = 0
        for bound_node in interface_nodes:

            def check_edge(
                ctx: tuple[set[int], accumulate, graph.GraphView, int],
                edge: graph.BoundEdge,
            ) -> None:
                interface_uuids, acc, gv, count = ctx
                nonlocal edges_checked
                edges_checked += 1

                source = edge.edge().source()
                target = edge.edge().target()

                source_is_interface = source.get_uuid() in interface_uuids
                target_is_interface = target.get_uuid() in interface_uuids

                if not source_is_interface or not target_is_interface:
                    with acc.collect():
                        source_bound = gv.bind(node=source)
                        target_bound = gv.bind(node=target)
                        source_py = fabll.Node.bind_instance(instance=source_bound)
                        target_py = fabll.Node.bind_instance(instance=target_bound)
                        non_interface = (
                            target_py if not target_is_interface else source_py
                        )
                        raise ERCFaultIncompatibleInterfaceConnection(
                            f"EdgeInterfaceConnection to non-interface node:\n"
                            f"  {non_interface.pretty_repr()} is not an interface",
                            source_py,
                            target_py,
                            "<interface>" if source_is_interface else "<not interface>",
                            "<interface>" if target_is_interface else "<not interface>",
                        )

            bound_node.visit_edges_of_type(
                edge_type=edge_tid,
                ctx=(interface_uuids, accumulator, g, edges_checked),
                f=check_edge,
            )

        logger.debug(f"Verified {edges_checked} interface connection edges")

    def _check_interface_connection_types(self, accumulator: accumulate) -> None:
        """
        Check that all interface connections have compatible types.

        This validates that EdgeInterfaceConnections only exist between nodes
        of compatible types. Compatible types are:
        - Same type (e.g., Electrical to Electrical)
        - ElectricLogic <-> ElectricSignal (structurally compatible)

        Raises ERCFaultIncompatibleInterfaceConnection for invalid connections.
        """
        # Types that are compatible with each other despite being different
        # Both have the same structure: line (Electrical) and reference (ElectricPower)
        COMPATIBLE_TYPE_PAIRS: frozenset[frozenset[str]] = frozenset(
            {
                frozenset({"ElectricLogic", "ElectricSignal"}),
            }
        )

        def are_types_compatible(type1: str | None, type2: str | None) -> bool:
            """Check if two type names are compatible for connection."""
            if type1 is None or type2 is None:
                # If either type is unknown, we can't validate - allow it
                return True
            if type1 == type2:
                return True
            # Check for special compatible pairs
            pair = frozenset({type1, type2})
            return pair in COMPATIBLE_TYPE_PAIRS

        def get_type_name(bound_node: graph.BoundNode) -> str | None:
            """Get the type name of an instance node."""
            type_edge = fbrk.EdgeType.get_type_edge(bound_node=bound_node)
            if type_edge is None:
                return None
            type_node = fbrk.EdgeType.get_type_node(edge=type_edge.edge())
            type_bound = bound_node.g().bind(node=type_node)
            return fbrk.TypeGraph.get_type_name(type_node=type_bound)

        g = self.tg.get_graph_view()
        edge_tid = fbrk.EdgeInterfaceConnection.get_tid()

        # Get the is_interface type to find all nodes with the trait
        is_interface_type = self.tg.get_type_by_name(
            type_identifier="is_interface.node.core.faebryk"
        )
        if is_interface_type is None:
            logger.debug("No is_interface type found, skipping interface type check")
            return

        # Get all nodes that implement is_interface using Trait.visit_implementers
        # This is O(number of interfaces) rather than O(all nodes)
        interface_nodes: list[graph.BoundNode] = []

        def collect_implementer(
            ctx: list[graph.BoundNode], node: graph.BoundNode
        ) -> None:
            ctx.append(node)

        fbrk.Trait.visit_implementers(
            trait_type=is_interface_type, ctx=interface_nodes, f=collect_implementer
        )

        # Collect interface connection edges, only from source side to avoid dupes
        all_edges: list[graph.BoundEdge] = []

        def collect_if_source(
            ctx: tuple[list[graph.BoundEdge], graph.BoundNode],
            edge: graph.BoundEdge,
        ) -> None:
            edges_list, current_node = ctx
            # Only collect if current node is the source - avoids duplicates
            if edge.edge().source().is_same(other=current_node.node()):
                edges_list.append(edge)

        for bound_node in interface_nodes:
            bound_node.visit_edges_of_type(
                edge_type=edge_tid, ctx=(all_edges, bound_node), f=collect_if_source
            )

        logger.debug(
            f"Checking {len(all_edges)} interface connections "
            f"across {len(interface_nodes)} interface nodes"
        )

        # Build set of interface node references for O(1) lookup
        interface_node_set: set[int] = {
            node.node().get_uuid() for node in interface_nodes
        }

        def has_is_interface(bound_node: graph.BoundNode) -> bool:
            """Check if node has is_interface trait (is in our interface set)."""
            return bound_node.node().get_uuid() in interface_node_set

        # Now check each edge exactly once
        # Source is guaranteed to have is_interface (we collected from interface nodes)
        for bound_edge in all_edges:
            edge = bound_edge.edge()
            source_bound = g.bind(node=edge.source())
            target_bound = g.bind(node=edge.target())

            # First verify both sides are interfaces - if not, skip
            # (This can happen with malformed connections like `power.lv ~ resistor`)
            if not has_is_interface(target_bound):
                # Target is not an interface - this is a malformed connection
                # Report error but don't try to get type info which might hang
                with accumulator.collect():
                    source_py = fabll.Node.bind_instance(instance=source_bound)
                    target_py = fabll.Node.bind_instance(instance=target_bound)
                    raise ERCFaultIncompatibleInterfaceConnection.from_nodes(
                        source=source_py,
                        target=target_py,
                        source_type=get_type_name(source_bound) or "<unknown>",
                        target_type="<not an interface>",
                    )
                continue

            # Get type information
            source_type = get_type_name(source_bound)
            target_type = get_type_name(target_bound)

            # Check type compatibility
            if not are_types_compatible(source_type, target_type):
                with accumulator.collect():
                    source_py = fabll.Node.bind_instance(instance=source_bound)
                    target_py = fabll.Node.bind_instance(instance=target_bound)
                    raise ERCFaultIncompatibleInterfaceConnection.from_nodes(
                        source=source_py,
                        target=target_py,
                        source_type=source_type or "<unknown>",
                        target_type=target_type or "<unknown>",
                    )

    def _check_additional_heuristics(self) -> None:
        # shorted components
        # parts = [n for n in nodes if n.has_trait(has_footprint)]
        # sym_fps = [
        #    n.get_trait(has_footprint).get_footprint()
        #    for n in parts
        #    if n.has_trait(F.Footprints.can_attach_to_footprint)
        # ]
        # logger.info(f"Checking {len(sym_fps)} symmetric footprints")
        # for fp in sym_fps:
        #    mifs = set(fp.get_all())
        #    checked = set()
        #    for mif in mifs:
        #        checked.add(mif)
        #        if any(mif.is_connected_to(other) for other in (mifs - checked)):
        #            raise ERCFault([mif], "shorted symmetric footprint")

        ## unmapped Electricals
        # fps = [n for n in nodes if isinstance(n, Footprint)]
        # logger.info(f"Checking {len(fps)} footprints")
        # for fp in fps:
        #    for mif in fp.get_all():
        #        if not mif.get_direct_connections():
        #            raise ERCFault([mif], "no connections")

        # TODO check multiple pulls per logic
        pass


class Test:
    class _App(fabll.Node):
        is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    def _run_post_design_checks(self, tg: fbrk.TypeGraph) -> None:
        g = tg.get_graph_view()
        app_type = self._App.bind_typegraph(tg)
        app = app_type.create_instance(g=g)
        fabll.Traits.create_and_add_instance_to(app, needs_erc_check)
        check_design(app, F.implements_design_check.CheckStage.POST_DESIGN)

    def test_erc_isolated_connect(self):
        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        electricPowerType = F.ElectricPower.bind_typegraph(tg)

        y1 = electricPowerType.create_instance(g=g)
        y2 = electricPowerType.create_instance(g=g)

        y1.make_source()
        y2.make_source()

        with pytest.raises(ERCPowerSourcesShortedError):
            y1._is_interface.get().connect_to(y2)
            self._run_post_design_checks(tg)

        # TODO no more LDO in fabll
        # ldo1 = F.LDO()
        # ldo2 = F.LDO()

        # with pytest.raises(ERCPowerSourcesShortedError):
        #     ldo1.power_out.connect(ldo2.power_out)
        #     simple_erc(ldo1.get_graph())

        i2cType = F.I2C.bind_typegraph(tg)
        a1 = i2cType.create_instance(g=g)
        b1 = i2cType.create_instance(g=g)

        a1._is_interface.get().connect_to(b1)
        assert a1._is_interface.get().is_connected_to(b1)
        assert a1.scl.get()._is_interface.get().is_connected_to(b1.scl.get())
        assert a1.sda.get()._is_interface.get().is_connected_to(b1.sda.get())

        assert not a1.scl.get()._is_interface.get().is_connected_to(b1.sda.get())
        assert not a1.sda.get()._is_interface.get().is_connected_to(b1.scl.get())

    def test_erc_electric_power_short(self):
        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        electricPowerType = F.ElectricPower.bind_typegraph(tg)
        ep1 = electricPowerType.create_instance(g=g)
        ep2 = electricPowerType.create_instance(g=g)

        ep1._is_interface.get().connect_to(ep2)

        # This is okay!
        self._run_post_design_checks(tg)

        ep1.lv.get()._is_interface.get().connect_to(ep2.hv.get())

        # This is not okay!
        with pytest.raises(ERCFaultShortedInterfaces) as ex:
            self._run_post_design_checks(tg)

        # TODO figure out a nice way to format paths for this
        print(ex.value.path)
        # assert set(ex.value.path) == {ep1.lv, ep2.hv}

    def test_erc_electric_power_short_multiple_paths(self):
        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        electricPowerType = F.ElectricPower.bind_typegraph(tg)
        eps = [electricPowerType.create_instance(g=g) for _ in range(4)]

        for i in range(3):
            eps[i]._is_interface.get().connect_to(eps[i + 1])

        eps[0].hv.get()._is_interface.get().connect_to(eps[3].lv.get())

        with pytest.raises(ERCFaultShortedInterfaces):
            self._run_post_design_checks(tg)

    def test_erc_electric_power_short_via_resistor_no_short(self):
        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        electricPowerType = F.ElectricPower.bind_typegraph(tg)
        ep1 = electricPowerType.create_instance(g=g)
        resistor = F.Resistor.bind_typegraph(tg).create_instance(g=g)

        ep1.hv.get()._is_interface.get().connect_to(resistor.unnamed[0].get())
        ep1.lv.get()._is_interface.get().connect_to(resistor.unnamed[1].get())

        # should not raise
        self._run_post_design_checks(tg)

    def test_erc_power_source_short(self):
        """
        Test that a power source is shorted when connected to another power source
        """
        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        power_out_1 = F.ElectricPower.bind_typegraph(tg).create_instance(g=g)
        power_out_2 = F.ElectricPower.bind_typegraph(tg).create_instance(g=g)

        power_out_1._is_interface.get().connect_to(power_out_2)
        power_out_2._is_interface.get().connect_to(power_out_1)

        power_out_1.make_source()
        power_out_2.make_source()

        with pytest.raises(ERCPowerSourcesShortedError):
            self._run_post_design_checks(tg)

    def test_erc_power_source_no_short(self):
        """
        Test that a power source is not shorted when connected to another
        non-power source
        """
        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        power_out_1 = F.ElectricPower.bind_typegraph(tg).create_instance(g=g)
        power_out_2 = F.ElectricPower.bind_typegraph(tg).create_instance(g=g)

        power_out_1.make_source()

        power_out_1._is_interface.get().connect_to(power_out_2)

        self._run_post_design_checks(tg)

    def test_erc_interface_type_same_type_compatible(self):
        """
        Test that connecting interfaces of the same type passes ERC.
        """
        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        # Create two Electrical interfaces and connect them
        electrical_type = F.Electrical.bind_typegraph(tg)
        e1 = electrical_type.create_instance(g=g)
        e2 = electrical_type.create_instance(g=g)

        e1._is_interface.get().connect_to(e2)

        # Should pass - same types
        self._run_post_design_checks(tg)

    def test_erc_interface_type_electric_power_compatible(self):
        """
        Test that connecting ElectricPower interfaces passes ERC.
        """
        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        power_type = F.ElectricPower.bind_typegraph(tg)
        p1 = power_type.create_instance(g=g)
        p2 = power_type.create_instance(g=g)

        p1._is_interface.get().connect_to(p2)

        # Should pass - same types
        self._run_post_design_checks(tg)

    def test_erc_interface_type_electric_logic_compatible(self):
        """
        Test that connecting ElectricLogic interfaces passes ERC.
        """
        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        logic_type = F.ElectricLogic.bind_typegraph(tg)
        l1 = logic_type.create_instance(g=g)
        l2 = logic_type.create_instance(g=g)

        l1._is_interface.get().connect_to(l2)

        # Should pass - same types
        self._run_post_design_checks(tg)

    def test_erc_interface_type_incompatible_power_to_electrical(self):
        """
        Test that the Zig layer prevents incompatible type connections
        (ElectricPower to Electrical directly).

        Note: The Zig connect function enforces type matching at connection
        time, so this tests that the protection is in place.
        """
        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        power = F.ElectricPower.bind_typegraph(tg).create_instance(g=g)
        electrical = F.Electrical.bind_typegraph(tg).create_instance(g=g)

        # The Zig layer should reject this connection due to type mismatch
        # It raises ValueError with "Failed to connect interface nodes"
        with pytest.raises(ValueError, match="Failed to connect"):
            power._is_interface.get().connect_to(electrical)
