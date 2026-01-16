# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from rich.syntax import Syntax
from rich.text import Text

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile import errors
from faebryk.libs.app.checks import check_design
from faebryk.libs.exceptions import accumulate

if TYPE_CHECKING:
    from rich.console import Console, ConsoleOptions, ConsoleRenderable

    from atopile.compiler import ast_types as AST

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Shared ERC Error Data Structure
# -----------------------------------------------------------------------------


@dataclass
class InterfaceConnectionError:
    """
    Represents an invalid interface connection error.

    This is a data structure that can be used by both the ERC checker
    (to raise exceptions) and the LSP (to create diagnostics).
    """

    source_node: fabll.Node
    target_node: fabll.Node
    source_is_interface: bool
    target_is_interface: bool
    source_type: str | None
    target_type: str | None
    source_chunk: "AST.SourceChunk | None"

    @property
    def message(self) -> str:
        """Generate a human-readable error message."""
        if not self.source_is_interface or not self.target_is_interface:
            non_interface = (
                self.source_node if not self.source_is_interface else self.target_node
            )
            return (
                "EdgeInterfaceConnection to non-interface node:\n"
                f"  {non_interface.pretty_repr()} is not an interface"
            )

        # Both are interfaces but types are incompatible
        src = self.source_type or "<unknown>"
        tgt = self.target_type or "<unknown>"
        return (
            "Incompatible interface types connected:\n"
            f"  {self.source_node.pretty_repr()} ({src})\n"
            f"    -> {self.target_node.pretty_repr()} ({tgt})"
        )


def find_interface_connection_errors(
    tg: fbrk.TypeGraph,
) -> list[InterfaceConnectionError]:
    """
    Find all invalid interface connections in the graph.

    This is the core ERC checking function that can be used by both:
    - The ERC checker (converts errors to exceptions)
    - The LSP server (converts errors to diagnostics)

    Returns a list of InterfaceConnectionError objects with all info needed
    to report the error (source location, node info, etc.).
    """
    errors_found: list[InterfaceConnectionError] = []

    g = tg.get_graph_view()
    edge_tid = fbrk.EdgeInterfaceConnection.get_tid()

    # Get the is_interface type
    is_interface_type = tg.get_type_by_name(
        type_identifier="is_interface.node.core.faebryk"
    )
    if is_interface_type is None:
        logger.debug("No is_interface type found, skipping ERC check")
        return errors_found

    # Get all nodes that implement is_interface
    interface_nodes: list[graph.BoundNode] = []

    def collect_implementer(ctx: list[graph.BoundNode], node: graph.BoundNode) -> None:
        ctx.append(node)

    fbrk.Trait.visit_implementers(
        trait_type=is_interface_type, ctx=interface_nodes, f=collect_implementer
    )

    # Build set of interface node UUIDs for O(1) lookup
    interface_uuids: set[int] = {node.node().get_uuid() for node in interface_nodes}

    # Collect ALL edges from interface nodes, deduplicating by edge UUID pair
    all_edges: list[graph.BoundEdge] = []
    seen_edges: set[tuple[int, int]] = set()

    def collect_edge(
        ctx: tuple[list[graph.BoundEdge], set[tuple[int, int]]],
        edge: graph.BoundEdge,
    ) -> None:
        edges_list, seen = ctx
        # Dedupe by (source_uuid, target_uuid) pair
        edge_key = (edge.edge().source().get_uuid(), edge.edge().target().get_uuid())
        if edge_key not in seen:
            seen.add(edge_key)
            edges_list.append(edge)

    for bound_node in interface_nodes:
        bound_node.visit_edges_of_type(
            edge_type=edge_tid, ctx=(all_edges, seen_edges), f=collect_edge
        )

    logger.debug(
        f"Checking {len(all_edges)} interface connections "
        f"across {len(interface_nodes)} interface nodes"
    )

    # Types that are compatible despite being different
    COMPATIBLE_TYPE_PAIRS: frozenset[frozenset[str]] = frozenset(
        {frozenset({"ElectricLogic", "ElectricSignal"})}
    )

    def are_types_compatible(type1: str | None, type2: str | None) -> bool:
        if type1 is None or type2 is None:
            return True
        if type1 == type2:
            return True
        return frozenset({type1, type2}) in COMPATIBLE_TYPE_PAIRS

    # Check each edge
    for bound_edge in all_edges:
        edge = bound_edge.edge()
        source_node = fabll.Node.bind_instance(g.bind(node=edge.source()))
        target_node = fabll.Node.bind_instance(g.bind(node=edge.target()))

        source_is_interface = source_node.instance.node().get_uuid() in interface_uuids
        target_is_interface = target_node.instance.node().get_uuid() in interface_uuids

        # Check if both endpoints are interfaces
        if not source_is_interface or not target_is_interface:
            from atopile.compiler.ast_visitor import ASTVisitor

            source_chunk = ASTVisitor.get_source_chunk_for_connection(
                source_node.instance, target_node.instance, tg
            )
            errors_found.append(
                InterfaceConnectionError(
                    source_node=source_node,
                    target_node=target_node,
                    source_is_interface=source_is_interface,
                    target_is_interface=target_is_interface,
                    source_type=(
                        source_node.get_type_name() if source_is_interface else None
                    ),
                    target_type=(
                        target_node.get_type_name() if target_is_interface else None
                    ),
                    source_chunk=source_chunk,
                )
            )
            continue

        # Check type compatibility
        source_type = source_node.get_type_name()
        target_type = target_node.get_type_name()

        if not are_types_compatible(source_type, target_type):
            from atopile.compiler.ast_visitor import ASTVisitor

            source_chunk = ASTVisitor.get_source_chunk_for_connection(
                source_node.instance, target_node.instance, tg
            )
            errors_found.append(
                InterfaceConnectionError(
                    source_node=source_node,
                    target_node=target_node,
                    source_is_interface=True,
                    target_is_interface=True,
                    source_type=source_type,
                    target_type=target_type,
                    source_chunk=source_chunk,
                )
            )

    return errors_found

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
        source_chunk: "AST.SourceChunk | None" = None,
    ) -> None:
        super().__init__(msg, [source_node, target_node], *args, markdown=False)
        self.source_node = source_node
        self.target_node = target_node
        self.source_type = source_type
        self.target_type = target_type
        self.source_chunk = source_chunk

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> list["ConsoleRenderable"]:
        """Render error with source location if available."""
        # Get base rendering from parent
        renderables = super().__rich_console__(console, options)

        # Add source location if we have it
        if self.source_chunk is not None:
            loc = self.source_chunk.loc.get()
            start_line = loc.get_start_line()
            end_line = loc.get_end_line()
            file_path = self.source_chunk.get_path()

            if file_path:
                try:
                    with open(file_path) as f:
                        code = f.read()
                    display_path = str(Path(file_path).resolve())
                    source_info = f"{display_path}:{start_line}"

                    renderables.append(Text("\nCode causing the error:", style="bold"))
                    renderables.append(
                        Text("Source: ", style="bold")
                        + Text(source_info, style="magenta")
                    )
                    renderables.append(
                        Syntax(
                            code,
                            "python",
                            line_numbers=True,
                            line_range=(max(1, start_line - 2), end_line + 2),
                            highlight_lines=set(range(start_line, end_line + 1)),
                            background_color="default",
                        )
                    )
                except (FileNotFoundError, OSError):
                    pass

        return renderables

    @classmethod
    def from_nodes(
        cls,
        source: fabll.Node,
        target: fabll.Node,
        source_type: str,
        target_type: str,
        tg: fbrk.TypeGraph | None = None,
    ) -> "ERCFaultIncompatibleInterfaceConnection":
        """Create an exception for incompatible interface connection."""
        # Try to find source location
        source_chunk = None
        if tg is not None:
            from atopile.compiler.ast_visitor import ASTVisitor

            source_chunk = ASTVisitor.get_source_chunk_for_connection(
                source.instance, target.instance, tg
            )

        return cls(
            f"Incompatible interface types connected:\n"
            f"  {source.pretty_repr()} ({source_type})\n"
            f"    -> {target.pretty_repr()} ({target_type})",
            source,
            target,
            source_type,
            target_type,
            source_chunk=source_chunk,
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

    @F.implements_design_check.register_post_instantiation_graph_check
    def __check_post_instantiation_graph_check__(self):
        """
        Early validation of graph structure before any BFS traversal.

        This runs FIRST to catch malformed EdgeInterfaceConnections that would
        cause hangs in later checks (like requires_external_usage which uses BFS).
        """
        logger.info("Verifying interface connection graph structure")
        with accumulate(ERCFault) as accumulator:
            self._verify_interface_connections(accumulator)

    @F.implements_design_check.register_post_instantiation_design_check
    def __check_post_instantiation_design_check__(self):
        logger.info("Checking for ERC violations")
        with accumulate(ERCFault) as accumulator:
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
        Verify that all EdgeInterfaceConnections are between is_interface nodes
        and have compatible types.

        Uses the shared find_interface_connection_errors() function and converts
        any errors found to exceptions.
        """
        errors = find_interface_connection_errors(self.tg)
        for error in errors:
            with accumulator.collect():
                source_py = error.source_node
                target_py = error.target_node

                raise ERCFaultIncompatibleInterfaceConnection(
                    error.message,
                    source_py,
                    target_py,
                    error.source_type or "<unknown>",
                    error.target_type or "<unknown>",
                    source_chunk=error.source_chunk,
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

    @staticmethod
    def _connect_interface_via_edge_builder(
        g: graph.GraphView,
        source: fabll.Node,
        target: fabll.Node,
    ) -> None:
        edge_attrs = fbrk.EdgeInterfaceConnection.build(shallow=False)
        edge_attrs.insert_edge(
            g=g,
            source=source.instance.node(),
            target=target.instance.node(),
        )

    def _run_checks(self, tg: fbrk.TypeGraph) -> None:
        g = tg.get_graph_view()
        app_type = self._App.bind_typegraph(tg)
        app = app_type.create_instance(g=g)
        fabll.Traits.create_and_add_instance_to(app, needs_erc_check)
        check_design(app, F.implements_design_check.CheckStage.POST_INSTANTIATION_GRAPH_CHECK)
        check_design(app, F.implements_design_check.CheckStage.POST_INSTANTIATION_DESIGN_CHECK)

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
            self._run_checks(tg)

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
        self._run_checks(tg)

        ep1.lv.get()._is_interface.get().connect_to(ep2.hv.get())

        # This is not okay!
        with pytest.raises(ERCFaultShortedInterfaces) as ex:
            self._run_checks(tg)

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
            self._run_checks(tg)

    def test_erc_electric_power_short_via_resistor_no_short(self):
        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        electricPowerType = F.ElectricPower.bind_typegraph(tg)
        ep1 = electricPowerType.create_instance(g=g)
        resistor = F.Resistor.bind_typegraph(tg).create_instance(g=g)

        ep1.hv.get()._is_interface.get().connect_to(resistor.unnamed[0].get())
        ep1.lv.get()._is_interface.get().connect_to(resistor.unnamed[1].get())

        # should not raise
        self._run_checks(tg)

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
            self._run_checks(tg)

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

        self._run_checks(tg)


    def test_verify_graph_interface_type_same_type_compatible(self):
        """
        Test that connecting interfaces of the same type passes ERC.
        """
        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        # Create two Electrical interfaces and connect them
        electrical_type = F.Electrical.bind_typegraph(tg)
        e1 = electrical_type.create_instance(g=g)
        e2 = electrical_type.create_instance(g=g)

        self._connect_interface_via_edge_builder(g, e1, e2)

        assert e1._is_interface.get().is_connected_to(e2)

        # Should pass - same types
        self._run_checks(tg)

    def test_verify_graph_interface_type_different_type_incompatible(self):
        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        electrical_type = F.Electrical.bind_typegraph(tg)
        e1 = electrical_type.create_instance(g=g)

        power_type = F.ElectricPower.bind_typegraph(tg)
        p1 = power_type.create_instance(g=g)

        self._connect_interface_via_edge_builder(g, e1, p1)

        assert e1._is_interface.get().is_connected_to(p1)

        with pytest.raises(ERCFaultIncompatibleInterfaceConnection):
            self._run_checks(tg)
