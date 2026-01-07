# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from itertools import pairwise
from typing import cast

import pytest
from rich.console import Console

from faebryk.libs.test.times import Times

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("setup_project_config")
@pytest.mark.parametrize(
    "A,B,rs,pick",
    [
        # (10, 7, 100, False),
        # (1, 1, 5000, False),
        # (1, 1, 1, False),
        (1, 1, 2, True),
    ],
)
def test_performance_parameters(A: int, B: int, rs: int, pick: bool):
    timings = Times()

    assert B > 0
    assert A >= 0
    assert rs >= 0

    with timings.context("import faebryk"):
        import faebryk.core.faebrykpy as fbrk
        import faebryk.core.graph as graph
        import faebryk.core.node as fabll

    with timings.context("import F"):
        import faebryk.library._F as F

    from faebryk.core.solver.defaultsolver import DefaultSolver
    from faebryk.libs.picker.picker import get_pick_tree, pick_topologically

    def _build_recursive(depth: int) -> fabll._ChildField[F.Expressions.Add]:
        if depth == 1:
            ps = [
                F.Parameters.NumericParameter.MakeChild(unit=F.Units.Dimensionless)
                for _ in range(2)
            ]
        else:
            ps = [_build_recursive(depth - 1) for _ in range(2)]
        out = F.Expressions.Add.MakeChild(*[fabll.RefPath([p]) for p in ps])
        out.add_dependant(*ps, before=True)

        return out

    def _nested_expressions():
        class _App(fabll.Node):
            _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            resistors = [F.Resistor.MakeChild() for _ in range(rs)]

            expressions = [_build_recursive(B) for _ in range(A)]

        return _App

    with timings.context("setup (create graph and typegraph)"):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

    with timings.context("fabll stage0 (capture fields)"):
        app_type = _nested_expressions().bind_typegraph(tg)
        bound_expression = F.Expressions.Add.bind_typegraph(tg)
        bound_parameter = F.Parameters.NumericParameter.bind_typegraph(tg)
        bound_resistor = F.Resistor.bind_typegraph(tg)
        bound_numbers = F.Literals.Numbers.bind_typegraph(tg)
        bound_ohm = F.Units.Ohm.bind_typegraph(tg)

    with timings.context("fabll stage1 (create typegraph)"):
        bound_expression.get_or_create_type()
        bound_parameter.get_or_create_type()
        bound_resistor.get_or_create_type()
        bound_numbers.get_or_create_type()
        bound_ohm.get_or_create_type()

    with timings.context("bind dimless"):
        dimless = F.Units.Dimensionless.bind_typegraph(tg)

    with timings.context("get_or_create_dimless"):
        dimless.get_or_create_type()

    instances = {}
    for n in [app_type, bound_expression, bound_parameter, bound_resistor]:
        tid = n.t._type_identifier()
        with timings.context(f"create_instance -- {tid}"):
            instances[tid] = n.create_instance(g=g)
        if tid == "NumericParameter":
            dimless_inst = dimless.create_instance(g=g)
            with timings.context(f"setup -- {tid}"):
                instances[tid].setup(is_unit=dimless_inst.is_unit.get())

    app = instances[app_type.t._type_identifier()]

    g_copy = graph.GraphView.create()
    g_copy2 = graph.GraphView.create()
    timings.add_seperator()
    dimless_instance = dimless.create_instance(g=g)
    with timings.context("create_instance_dimless"):
        dimless_instance2 = F.Units.Dimensionless.bind_typegraph(tg).create_instance(
            g=g_copy
        )
    with timings.context("copy -- fresh -- dimless"):
        dimless_instance.copy_into(g=g_copy)
    with timings.context("copy -- type dup -- dimless"):
        dimless_instance2.copy_into(g=g_copy)
    with timings.context("copy -- instance dup -- dimless"):
        dimless_instance.copy_into(g=g_copy)
    timings.add_seperator()

    number_literal_instance = bound_numbers.create_instance(g=g).setup_from_min_max(
        min=0, max=1, unit=dimless_instance.is_unit.get()
    )
    with timings.context("create_number_literal"):
        number_literal_instance2 = bound_numbers.create_instance(
            g=g_copy2
        ).setup_from_min_max(min=0, max=1, unit=dimless_instance.is_unit.get())
    with timings.context("copy -- fresh -- number_literal"):
        number_literal_instance.copy_into(g=g_copy2)
    with timings.context("copy -- type dup -- number_literal"):
        number_literal_instance2.copy_into(g=g_copy2)
    with timings.context("copy -- instance dup -- number_literal"):
        number_literal_instance.copy_into(g=g_copy2)
    timings.add_seperator()

    with timings.context("create_numbers"):
        numbers = [bound_numbers.create_instance(g=g) for _ in range(rs)]
    with timings.context("create_ohm"):
        ohms = [bound_ohm.create_instance(g=g) for _ in range(rs)]
    with timings.context("ohm_as_op"):
        ohm_as_op = [o.is_unit.get() for o in ohms]
    with timings.context("setup_numbers"):
        for n, o in zip(numbers, ohm_as_op):
            n.setup_from_center_rel(100 * 1000, 0.1, o)
    with timings.context("as_op"):
        resistors_as_op = [
            r.get().resistance.get().can_be_operand.get() for r in app.resistors
        ]
        numbers_as_op = [n.can_be_operand.get() for n in numbers]
    with timings.context("constrain_resistors"):
        for r, n in zip(resistors_as_op, numbers_as_op):
            F.Expressions.IsSubset.from_operands(
                r,
                n,
                assert_=True,
            )
    with timings.context("constrain_resistors_subset"):
        for r1, r2 in pairwise(resistors_as_op[len(resistors_as_op) // 2 :]):
            F.Expressions.GreaterOrEqual.from_operands(
                F.Expressions.Add.c(
                    r1,
                    r2,
                ),
                F.Literals.Numbers.bind_typegraph(tg)
                .create_instance(g=g)
                .setup_from_center_rel(
                    1,
                    0.1,
                    F.Units.Ohm.bind_typegraph(tg).create_instance(g=g).is_unit.get(),
                )
                .can_be_operand.get(),
                assert_=True,
            )

    with timings.context("print_tg_overview"):
        tg_overview = dict(
            sorted(tg.get_type_instance_overview(), key=lambda x: x[1], reverse=True)
        )
    # print(indented_container(tg_overview))
    print("Total typed nodes:", sum(tg_overview.values()))

    if A > 0:
        with timings.context("print_expr"):
            expr_str = app.expressions[0].get().is_expression.get().compact_repr()
        print("Expr: ", expr_str)

    if rs:
        with timings.context("connect_interfaces"):
            interfaces = [r.get().unnamed[0].get() for r in app.resistors]
            left = interfaces[0]
            left._is_interface.get().connect_to(*interfaces[1:])

    with timings.context("get_all_graph_nodes"):
        nc = g.get_nodes()
    print(f"nc: {len(nc)}")
    print(f"g: {g}")

    with timings.context("get_graph_trait -- is_expression"):
        exprs = fabll.Traits.get_implementors(
            F.Expressions.is_expression.bind_typegraph(tg), g=g
        )
    print(f"exprs: {len(exprs)}")

    with timings.context("get_graph_trait -- is_parameter"):
        params = fabll.Traits.get_implementors(
            F.Parameters.is_parameter.bind_typegraph(tg), g=g
        )
    print(f"params: {len(params)}")

    with timings.context("get_graph_trait -- mif"):
        mifs = fabll.Traits.get_implementors(fabll.is_module.bind_typegraph(tg), g=g)
    print("mifs: ", len(mifs))

    if rs:
        with timings.context("get_connected"):
            bus = (
                app.resistors[0]
                .get()
                .unnamed[0]
                .get()
                ._is_interface.get()
                .get_connected()
            )
        print("bus: ", len(bus))
        assert len(bus) == rs - 1

    for n in (
        app,
        *([app.expressions[0].get()] if A > 0 else []),
        *([app.resistors[0].get()] if rs > 0 else []),
    ):
        n = cast(fabll.Node, n)
        name = n.get_type_name()
        timings.add_seperator()

        with timings.context(f"{name:<10} -- get_node_children_all"):
            n.get_children(direct_only=False, types=fabll.Node)

        with timings.context(f"{name:<10} -- get_node_children_multitype"):
            n.get_children(direct_only=False, types=(F.Resistor, fabll.is_module))

        with timings.context(f"{name:<10} -- get_node_children_direct"):
            n.get_children(direct_only=True, types=fabll.Node)

        with timings.context(
            f"{name:<10} -- get_node_children_direct -- is_expression"
        ):
            c = n.get_children(
                direct_only=True,
                types=fabll.Node,
                required_trait=F.Expressions.is_expression,
            )
        print(f"direct is_expression: {len(c)}")
        with timings.context(f"{name:<10} -- get_node_children_type -- Add"):
            c = n.get_children(
                direct_only=False,
                types=F.Expressions.Add,
            )
        print(f"Adds: {len(c)}")

        with timings.context(f"{name:<10} -- get_node_children_trait -- is_expression"):
            c = n.get_children(
                direct_only=False,
                types=fabll.Node,
                required_trait=F.Expressions.is_expression,
            )
        print(f"recursive is_expression: {len(c)}")
        with timings.context(f"{name:<10} -- get_node_children_trait -- is_parameter"):
            n.get_children(
                direct_only=False,
                types=fabll.Node,
                required_trait=F.Parameters.is_parameter,
            )
        print(f"recursive is_parameter: {len(c)}")

        g_new = graph.GraphView.create()
        with timings.context(f"{name:<10} -- copy"):
            n.copy_into(g=g_new)
        print(f"g_new: {g_new}")

    timings.add_seperator()
    pick_tree = get_pick_tree(app)
    timings.add("pick tree")

    if pick:
        solver = DefaultSolver()
        with timings.as_global("pick_topologically", context=True):
            pick_topologically(pick_tree, solver)
            # solver.simplify(tg, g, terminal=True)

    logger.info(f"Exprs: {A * B}")
    console = Console()
    console.print(timings.to_table())
    per_expr = timings.get("create_instance (App)") / (A * B)
    logger.info(f"----> Avg/expr: {per_expr * 1e3:.2f} ms")
    logger.info(f"----> G: {g}")


if __name__ == "__main__":
    import typer

    from faebryk.libs.logging import setup_basic_logging

    setup_basic_logging()
    typer.run(test_performance_parameters)
