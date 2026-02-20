# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging

import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


class requires_external_usage(fabll.Node):
    """
    Trait that enforces external usage requirements on nodes.

    For interfaces: ensures the interface has a direct connection to something
    outside its parent module (not just internal connections).

    For parameters: ensures the parameter is constrained to a concrete value
    by the time the solver finishes.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    design_check = fabll.Traits.MakeEdge(F.implements_design_check.MakeChild())

    class RequiresExternalUsageNotFulfilled(
        F.implements_design_check.UnfulfilledCheckException
    ):
        def __init__(self, nodes: list[fabll.Node]):
            super().__init__(
                "Nodes requiring external usage but not used externally",
                nodes=nodes,
            )

    class RequiresValueNotFulfilled(
        F.implements_design_check.UnfulfilledCheckException
    ):
        def __init__(self, nodes: list[fabll.Node]):
            super().__init__(
                "Parameter requires to be constrained but is not",
                nodes=nodes,
            )

    def _has_interfaces(self) -> bool:
        obj = fabll.Traits(self).get_obj_raw()
        return any(
            obj.get_children(
                direct_only=False,
                types=fabll.Node,
                include_root=True,
                required_trait=fabll.is_interface,
            )
        )

    def _has_parameters(self) -> bool:
        obj = fabll.Traits(self).get_obj_raw()
        return any(
            obj.get_children(
                direct_only=False,
                types=fabll.Node,
                include_root=True,
                required_trait=F.Parameters.is_parameter,
            )
        )

    def _fulfilled_interface(self) -> bool:
        """Check if interfaces have external connections."""
        obj = fabll.Traits(self).get_obj_raw()
        parent = obj.get_parent()
        if parent is None:
            return True

        parent_node, _ = parent
        # TODO: disables checks for floating modules
        if parent_node.get_parent() is None:
            return True

        for node in obj.get_children(
            direct_only=False,
            types=fabll.Node,
            include_root=True,
            required_trait=fabll.is_interface,
        ):
            iface = node.get_trait(fabll.is_interface)
            for c, path in iface.get_connected().items():
                if path.length == 1 and not any(
                    parent_node.is_same(p) for p, _ in c.get_hierarchy()
                ):
                    return True

        return False

    def _fulfilled_parameter(self) -> bool:
        """Check if parameters are constrained to a value."""
        param_node = fabll.Traits(self).get_obj_raw()

        param = param_node.get_trait(F.Parameters.is_parameter_operatable)
        # Parameter is constrained when it has a superset
        # TODO: Also check if the superset is numeric, if so:
        # check if it is not (0 to inf) ?
        if param.try_extract_superset() is None:
            return False
        return True

    @property
    def fulfilled(self) -> bool:
        if self._has_interfaces():
            if not self._fulfilled_interface():
                return False
        if self._has_parameters():
            if not self._fulfilled_parameter():
                return False
        return True

    @F.implements_design_check.register_post_instantiation_design_check
    def __check_post_instantiation_design_check__(self):
        # Check interfaces at this stage
        if self._has_interfaces() and not self._fulfilled_interface():
            raise requires_external_usage.RequiresExternalUsageNotFulfilled(
                nodes=[fabll.Traits(self).get_obj_raw()],
            )

    @F.implements_design_check.register_post_solve_check
    def __check_post_solve__(self):
        # Check parameters at this stage (after solver runs)
        if self._has_parameters() and not self._fulfilled_parameter():
            raise requires_external_usage.RequiresValueNotFulfilled(
                nodes=[fabll.Traits(self).get_obj_raw()],
            )


class Test:
    def test_requires_external_usage_interface(self):
        import pytest

        import faebryk.core.faebrykpy as fbrk
        from atopile.errors import UserDesignCheckException
        from faebryk.libs.app.checks import check_design

        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class _Inner(fabll.Node):
            b = F.Electrical.MakeChild()

        class _Outer(fabll.Node):
            a = F.Electrical.MakeChild()
            inner = _Inner.MakeChild()
            _requires_external_usage = fabll.Traits.MakeEdge(
                requires_external_usage.MakeChild(),
                owner=[a],
            )

        class _App(fabll.Node):
            outer1 = _Outer.MakeChild()
            outer2 = _Outer.MakeChild()

        app = _App.bind_typegraph(tg=tg).create_instance(g=g)

        outer1 = app.outer1.get()
        outer2 = app.outer2.get()

        # no connections
        with pytest.raises((ExceptionGroup, UserDesignCheckException)) as excinfo:
            check_design(
                app,
                stage=F.implements_design_check.CheckStage.POST_INSTANTIATION_DESIGN_CHECK,
            )
        if isinstance(excinfo.value, ExceptionGroup):
            assert excinfo.group_contains(
                UserDesignCheckException,
                match="Nodes requiring external usage but not used externally",
            )

        # internal connection
        outer1.a.get()._is_interface.get().connect_to(outer1.inner.get().b.get())
        with pytest.raises((ExceptionGroup, UserDesignCheckException)) as excinfo:
            check_design(
                app,
                stage=F.implements_design_check.CheckStage.POST_INSTANTIATION_DESIGN_CHECK,
            )
        if isinstance(excinfo.value, ExceptionGroup):
            assert excinfo.group_contains(
                UserDesignCheckException,
                match="Nodes requiring external usage but not used externally",
            )

        # path to external (still internal-only for `a`)
        outer1.inner.get().b.get()._is_interface.get().connect_to(outer2.a.get())
        with pytest.raises((ExceptionGroup, UserDesignCheckException)) as excinfo:
            check_design(
                app,
                stage=F.implements_design_check.CheckStage.POST_INSTANTIATION_DESIGN_CHECK,
            )
        if isinstance(excinfo.value, ExceptionGroup):
            assert excinfo.group_contains(
                UserDesignCheckException,
                match="Nodes requiring external usage but not used externally",
            )

        # direct external connection also satisfies the requirement
        outer1.a.get()._is_interface.get().connect_to(outer2.inner.get().b.get())
        check_design(
            app,
            stage=F.implements_design_check.CheckStage.POST_INSTANTIATION_DESIGN_CHECK,
        )

    def test_requires_external_usage_parameter_unconstrained(self):
        import pytest

        import faebryk.core.faebrykpy as fbrk
        from atopile.errors import UserDesignCheckException
        from faebryk.core.solver.solver import Solver
        from faebryk.libs.app.checks import check_design

        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class _Component(fabll.Node):
            voltage = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)
            _requires_external_usage = fabll.Traits.MakeEdge(
                requires_external_usage.MakeChild(),
                owner=[voltage],
            )

        class _App(fabll.Node):
            comp = _Component.MakeChild()

        app = _App.bind_typegraph(tg=tg).create_instance(g=g)

        solver = Solver()
        _ = solver.simplify(tg, g, terminal=True)

        print(app.comp.get().voltage.get().try_extract_superset())
        # Unconstrained - should fail
        with pytest.raises((ExceptionGroup, UserDesignCheckException)) as excinfo:
            check_design(app, stage=F.implements_design_check.CheckStage.POST_SOLVE)
        if isinstance(excinfo.value, ExceptionGroup):
            assert excinfo.group_contains(
                UserDesignCheckException,
                match="Parameter requires to be constrained but is not",
            )

    def test_requires_external_usage_parameter_constrained(self):
        import faebryk.core.faebrykpy as fbrk
        from faebryk.core.solver.solver import Solver
        from faebryk.libs.app.checks import check_design
        from faebryk.libs.util import not_none

        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class _Component2(fabll.Node):
            voltage = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)
            _requires_external_usage = fabll.Traits.MakeEdge(
                requires_external_usage.MakeChild(),
                owner=[voltage],
            )

        class _App2(fabll.Node):
            comp = _Component2.MakeChild()

        app = _App2.bind_typegraph(tg=tg).create_instance(g=g)

        volt_unit = (
            F.Units.Volt.bind_typegraph(tg=tg).create_instance(g=g).is_unit.get()
        )
        # Set a value (need to set both superset and subset to fully constrain)
        lit = (
            F.Literals.Numbers.bind_typegraph(tg=tg)
            .create_instance(g=g)
            .setup_from_center_rel(center=3.3, rel=0.1, unit=volt_unit)
        )

        voltage_param = app.comp.get().voltage.get()
        voltage_param.set_superset(g=g, value=lit)
        # voltage_param.is_parameter_operatable.get().set_subset(g=g, value=lit)

        solver = Solver()
        solver_result = solver.simplify(tg, g, terminal=True)
        repr_map = solver_result.data.mutation_map

        print(app.comp.get().voltage.get().try_extract_superset())

        assert (
            F.Literals.Numbers.bind_typegraph(tg=tg)
            .create_instance(g=g)
            .setup_from_center_rel(center=3.3, rel=0.1, unit=volt_unit)
            .is_literal.get()
            .op_setic_equals(
                not_none(
                    repr_map.try_extract_superset(
                        voltage_param.is_parameter_operatable.get()
                    )
                )
            )
        )
        # Now passes
        check_design(app, stage=F.implements_design_check.CheckStage.POST_SOLVE)
