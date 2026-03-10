# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from __future__ import annotations

import logging

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.errors import UserDesignCheckException, accumulate
from faebryk.library.DataBus import has_databus_role, has_databus_specification
from faebryk.libs.app.checks import check_design
from faebryk.libs.app.erc import _format_source_info, _get_connection_source_chunk

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Exception classes
# -----------------------------------------------------------------------------


class BusCheckFault(F.implements_design_check.UnfulfilledCheckException):
    """Base class for bus check faults."""

    pass


class BusTopologyViolation(BusCheckFault):
    """Point-to-point bus has more than 2 endpoints."""

    pass


class BusMultipleControllersError(BusCheckFault):
    """Multiple controllers on a bus that doesn't support multi-controller."""

    pass


class BusMultipleControllersWarning(
    F.implements_design_check.MaybeUnfulfilledCheckException
):
    """Multiple controllers on a bus that supports multi-controller (warning)."""

    pass


class BusMissingControllerError(BusCheckFault):
    """Bus has targets but no controller."""

    pass


# -----------------------------------------------------------------------------
# Source location helpers
# -----------------------------------------------------------------------------


def _get_bus_source_info(bus_members: set[fabll.Node], tg: fbrk.TypeGraph) -> str:
    """
    Try to find source location for a bus connection by looking up the .ato
    source chunk for a representative pair of bus members.
    """
    members = list(bus_members)
    for i, source in enumerate(members):
        for target in members[i + 1 :]:
            chunk = _get_connection_source_chunk(source, target, tg)
            if chunk is not None:
                return _format_source_info(chunk)
    return ""


# -----------------------------------------------------------------------------
# Check trait
# -----------------------------------------------------------------------------


class needs_bus_check(fabll.Node):
    """
    Centralized bus design checks.

    Validates:
    - Topology constraints (point-to-point buses have <= 2 endpoints)
    - Role constraints (controller/target relationships)
    """

    is_trait = fabll._ChildField(fabll.ImplementsTrait).put_on_type()
    design_check = fabll.Traits.MakeEdge(F.implements_design_check.MakeChild())

    @F.implements_design_check.register_post_instantiation_design_check
    def __check_post_instantiation_design_check__(self):
        logger.info("Checking bus constraints")

        g = self.g
        tg = self.tg

        # Ensure bus spec parameters are resolved (@once makes repeated calls free)
        has_databus_specification.resolve_data_bus_specification_parameters(g, tg)

        with accumulate(
            BusCheckFault,
            F.implements_design_check.MaybeUnfulfilledCheckException,
        ) as accumulator:
            bus_groups = has_databus_specification.get_bus_groups(g, tg)
            self._check_topology_constraints(accumulator, bus_groups, tg)
            self._check_role_constraints(accumulator, bus_groups, tg)

    def _check_topology_constraints(
        self,
        accumulator: accumulate,
        bus_groups: list[tuple[has_databus_specification, set[fabll.Node]]],
        tg: fbrk.TypeGraph,
    ) -> None:
        """Check that point-to-point buses have at most 2 endpoints."""
        for spec, bus_members in bus_groups:
            with accumulator.collect():
                topologies = spec.get_topology_values()

                # Only enforce for strictly point-to-point buses
                if (
                    topologies == {has_databus_specification.Topology.POINT_TO_POINT}
                    and len(bus_members) > 2
                ):
                    friendly = ", ".join(
                        n.get_full_name(include_uuid=False) for n in bus_members
                    )
                    source_info = _get_bus_source_info(bus_members, tg)
                    raise BusTopologyViolation(
                        f"Point-to-point bus has {len(bus_members)} endpoints "
                        f"(max 2): {friendly}{source_info}",
                        nodes=list(bus_members),
                    )

    def _check_role_constraints(
        self,
        accumulator: accumulate,
        bus_groups: list[tuple[has_databus_specification, set[fabll.Node]]],
        tg: fbrk.TypeGraph,
    ) -> None:
        """Check controller/target role constraints on buses."""
        for spec, bus_members in bus_groups:
            with accumulator.collect():
                # Collect roles for members that have has_role
                role_map: dict[fabll.Node, set[has_databus_role.Role]] = {}
                for member in bus_members:
                    if member.has_trait(has_databus_role):
                        role_trait = member.get_trait(has_databus_role)
                        role_map[member] = role_trait.get_roles()

                if not role_map:
                    # No role markers on this bus - that's fine
                    continue

                controllers = [
                    n
                    for n, roles in role_map.items()
                    if has_databus_role.Role.CONTROLLER in roles
                ]
                targets = [
                    n
                    for n, roles in role_map.items()
                    if has_databus_role.Role.TARGET in roles
                ]

                multi_controller = spec.get_multi_controller()

                # Multiple controllers check
                if len(controllers) > 1:
                    friendly_controllers = ", ".join(
                        n.get_full_name(include_uuid=False) for n in controllers
                    )
                    source_info = _get_bus_source_info(bus_members, tg)
                    if multi_controller is False:
                        raise BusMultipleControllersError(
                            f"Multiple controllers on bus that doesn't support "
                            f"multi-controller: "
                            f"{friendly_controllers}{source_info}",
                            nodes=controllers,
                        )
                    else:
                        raise BusMultipleControllersWarning(
                            f"Multiple controllers on bus: "
                            f"{friendly_controllers}{source_info}",
                            nodes=controllers,
                        )

                # Targets without controller check
                if len(targets) > 0 and len(controllers) == 0:
                    friendly_targets = ", ".join(
                        n.get_full_name(include_uuid=False) for n in targets
                    )
                    source_info = _get_bus_source_info(bus_members, tg)
                    raise BusMissingControllerError(
                        f"Bus has targets but no controller: "
                        f"{friendly_targets}{source_info}",
                        nodes=list(bus_members),
                    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class Test:
    class _App(fabll.Node):
        is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    def _run_checks(self, tg: fbrk.TypeGraph) -> None:
        g = tg.get_graph_view()
        app_type = self._App.bind_typegraph(tg)
        app = app_type.create_instance(g=g)
        fabll.Traits.create_and_add_instance_to(app, needs_bus_check)
        has_databus_specification.resolve_data_bus_specification_parameters(g, tg)
        check_design(
            app, F.implements_design_check.CheckStage.POST_INSTANTIATION_DESIGN_CHECK
        )

    # -- Topology checks --

    def test_point_to_point_two_ok(self):
        """Two UART_Base instances connected -> pass (point-to-point allows 2)."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        uart_type = F.UART_Base.bind_typegraph(tg)
        a = uart_type.create_instance(g=g)
        b = uart_type.create_instance(g=g)

        a._is_interface.get().connect_to(b)

        self._run_checks(tg)

    def test_point_to_point_three_error(self):
        """Three UART_Base instances connected -> BusTopologyViolation."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        uart_type = F.UART_Base.bind_typegraph(tg)
        a = uart_type.create_instance(g=g)
        b = uart_type.create_instance(g=g)
        c = uart_type.create_instance(g=g)

        a._is_interface.get().connect_to(b)
        b._is_interface.get().connect_to(c)

        with pytest.raises(
            (UserDesignCheckException, ExceptionGroup),
            match="Point-to-point bus",
        ):
            self._run_checks(tg)

    def test_multi_drop_many_ok(self):
        """Five I2C instances connected -> pass (BUS topology allows many)."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        i2c_type = F.I2C.bind_typegraph(tg)
        instances = [i2c_type.create_instance(g=g) for _ in range(5)]

        for i in range(4):
            instances[i]._is_interface.get().connect_to(instances[i + 1])

        self._run_checks(tg)

    # -- Role checks --
    # Wrapper modules that attach bus roles to I2C/SPI children via owner=[].
    # Roles are placed on the bus interface child, so the check code finds
    # them when inspecting bus members.

    class _I2CControllerModule(fabll.Node):
        i2c = F.I2C.MakeChild()
        _bus_role = fabll.Traits.MakeEdge(
            has_databus_role.MakeChild(role=[has_databus_role.Role.CONTROLLER]),
            owner=[i2c],
        )

    class _I2CTargetModule(fabll.Node):
        i2c = F.I2C.MakeChild()
        _bus_role = fabll.Traits.MakeEdge(
            has_databus_role.MakeChild(role=[has_databus_role.Role.TARGET]),
            owner=[i2c],
        )

    class _SPIControllerModule(fabll.Node):
        spi = F.SPI.MakeChild()
        _bus_role = fabll.Traits.MakeEdge(
            has_databus_role.MakeChild(role=[has_databus_role.Role.CONTROLLER]),
            owner=[spi],
        )

    def test_single_controller_ok(self):
        """1 CONTROLLER + 1 TARGET on I2C -> pass."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        ctrl = self._I2CControllerModule.bind_typegraph(tg).create_instance(g=g)
        tgt = self._I2CTargetModule.bind_typegraph(tg).create_instance(g=g)

        ctrl.i2c.get()._is_interface.get().connect_to(tgt.i2c.get())

        self._run_checks(tg)

    def test_multiple_controllers_no_multi_error(self):
        """2 CONTROLLERs on SPI (multi_controller=False) -> error."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        ctrl1 = self._SPIControllerModule.bind_typegraph(tg).create_instance(g=g)
        ctrl2 = self._SPIControllerModule.bind_typegraph(tg).create_instance(g=g)

        ctrl1.spi.get()._is_interface.get().connect_to(ctrl2.spi.get())

        with pytest.raises(
            (UserDesignCheckException, ExceptionGroup),
            match="Multiple controllers",
        ):
            self._run_checks(tg)

    def test_multiple_controllers_multi_warning(self):
        """2 CONTROLLERs on I2C (multi_controller=True) -> warning."""
        from atopile.errors import DowngradedExceptionCollector

        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        ctrl1 = self._I2CControllerModule.bind_typegraph(tg).create_instance(g=g)
        ctrl2 = self._I2CControllerModule.bind_typegraph(tg).create_instance(g=g)

        ctrl1.i2c.get()._is_interface.get().connect_to(ctrl2.i2c.get())

        # MaybeUnfulfilledCheckException is downgraded to a warning
        with DowngradedExceptionCollector(UserDesignCheckException) as collector:
            self._run_checks(tg)

        # Should have collected a warning
        assert len(collector.exceptions) > 0

    def test_targets_no_controller_error(self):
        """TARGETs but no CONTROLLER -> error."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        t1 = self._I2CTargetModule.bind_typegraph(tg).create_instance(g=g)
        t2 = self._I2CTargetModule.bind_typegraph(tg).create_instance(g=g)

        t1.i2c.get()._is_interface.get().connect_to(t2.i2c.get())

        with pytest.raises(
            (UserDesignCheckException, ExceptionGroup),
            match="no controller",
        ):
            self._run_checks(tg)

    def test_no_roles_ok(self):
        """Connected buses without any role markers -> pass."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        i2c_type = F.I2C.bind_typegraph(tg)
        a = i2c_type.create_instance(g=g)
        b = i2c_type.create_instance(g=g)

        a._is_interface.get().connect_to(b)

        self._run_checks(tg)

    def test_disconnected_buses_independent(self):
        """Two separate valid I2C buses -> pass."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        i2c_type = F.I2C.bind_typegraph(tg)

        # Bus 1
        a1 = i2c_type.create_instance(g=g)
        b1 = i2c_type.create_instance(g=g)
        a1._is_interface.get().connect_to(b1)

        # Bus 2
        a2 = i2c_type.create_instance(g=g)
        b2 = i2c_type.create_instance(g=g)
        a2._is_interface.get().connect_to(b2)

        self._run_checks(tg)
