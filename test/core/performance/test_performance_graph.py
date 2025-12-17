# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import cast

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
from faebryk.libs.test.times import Times
from faebryk.libs.util import indented_container

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("setup_project_config")
def test_performance_parameters(
    A: int = 1, B: int = 1, rs: int = 100, pick: bool = False
):
    timings = Times()

    assert B > 0
    assert A >= 0
    assert rs >= 0

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
        class App(fabll.Node):
            _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            resistors = [F.Resistor.MakeChild() for _ in range(rs)]

            expressions = [_build_recursive(B) for _ in range(A)]

        return App

    with timings.context("setup (create graph and typegraph)"):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

    with timings.context("fabll stage0 (capture fields)"):
        app_type = _nested_expressions().bind_typegraph(tg)
        bound_expression = F.Expressions.Add.bind_typegraph(tg)
        bound_parameter = F.Parameters.NumericParameter.bind_typegraph(tg)
        bound_resistor = F.Resistor.bind_typegraph(tg)

    with timings.context("fabll stage1 (create typegraph)"):
        bound_expression.get_or_create_type()
        bound_parameter.get_or_create_type()
        bound_resistor.get_or_create_type()

    instances = {}
    for n in [app_type, bound_expression, bound_parameter, bound_resistor]:
        tid = n.t._type_identifier()
        with timings.context(f"create_instance -- {tid}"):
            instances[tid] = n.create_instance(g=g)
    app = instances["App"]

    with timings.context("constrain_resistors"):
        for r in app.resistors:
            F.Expressions.IsSubset.from_operands(
                r.get().resistance.get().can_be_operand.get(),
                F.Literals.Numbers.bind_typegraph(tg)
                .create_instance(g=g)
                .setup_from_center_rel(
                    100 * 1000,
                    0.1,
                    F.Units.Ohm.bind_typegraph(tg).create_instance(g=g).is_unit.get(),
                )
                .can_be_operand.get(),
                assert_=True,
            )
    tg_overview = dict(
        sorted(tg.get_type_instance_overview(), key=lambda x: x[1], reverse=True)
    )
    print(indented_container(tg_overview))
    print("Total typed nodes:", sum(tg_overview.values()))

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
        with timings.context(f"{name:<10} -- copy graph"):
            n.copy_into(g_new)
        print(f"g_new: {g_new}")

    timings.add_seperator()
    pick_tree = get_pick_tree(app)
    timings.add("pick tree")

    if pick:
        solver = DefaultSolver()
        pick_topologically(pick_tree, solver)
        timings.add("pick")

    logger.info(f"Exprs: {A * B}")
    logger.info(f"\n\n{timings!r}")
    per_expr = timings.get("create_instance (App)") / (A * B)
    logger.info(f"----> Avg/expr: {per_expr * 1e3:.2f} ms")
    logger.info(f"----> G: {g}")


if __name__ == "__main__":
    import typer

    from faebryk.libs.logging import setup_basic_logging

    setup_basic_logging()

    typer.run(test_performance_parameters)
