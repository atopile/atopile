# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import sys
from pathlib import Path

import pytest

import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.logging import rich_to_string
from faebryk.core.solver.algorithm import algorithm
from faebryk.core.solver.mutator import (
    MutationMap,
    MutationStage,
    Mutator,
    Transformations,
)
from faebryk.core.solver.solver import Solver
from faebryk.core.solver.utils import ContradictionByLiteral

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from faebryk.libs.util import not_none
from test.core.solver.test_solver import BoundExpressions, _create_letters

logger = logging.getLogger(__name__)

Flattenable = (
    F.Expressions.Add
    | F.Expressions.Multiply
    | F.Expressions.Subtract
    | F.Expressions.Divide
    | F.Expressions.And
    | F.Expressions.Or
    | F.Expressions.Xor
)


def test_mutator_no_graph_merge():
    E = BoundExpressions()
    p0 = E.parameter_op(units=E.U.V)
    p1 = E.parameter_op(units=E.U.A)
    p2 = E.parameter_op(units=E.U.W)
    alias = E.is_(p2, E.multiply(p0, p1), assert_=True)

    context = F.Parameters.ReprContext()

    @algorithm("")
    def algo(mutator: Mutator):
        pass

    mutator = Mutator(
        MutationMap.bootstrap(p0.tg, p0.g, print_context=context),
        algo=algo,
        iteration=0,
        terminal=True,
    )
    p0_new = not_none(mutator.get_copy(p0))
    alias_new = fabll.Traits(not_none(mutator.get_copy(alias))).get_obj(
        F.Expressions.Is
    )

    G = p0.tg
    G_new = p0_new.tg

    assert fabll.Node(p0_new.tg.get_self_node()).is_same(
        other=fabll.Node(G_new.get_self_node())
    )
    assert not fabll.Node(G.get_self_node()).is_same(
        other=fabll.Node(G_new.get_self_node())
    )
    assert fabll.Node(alias_new.tg.get_self_node()).is_same(
        other=fabll.Node(G_new.get_self_node())
    )
    assert fabll.Node(
        mutator.get_mutated(p1.as_parameter_operatable.force_get()).tg.get_self_node()
    ).is_same(other=fabll.Node(G_new.get_self_node()))


# def test_get_expressions_involved_in():
#     E = BoundExpressions()
#     A = E.parameter_op()
#     B = E.parameter_op()

#     E1 = E.add(A, B)

#     res = MutatorUtils.get_expressions_involved_in(
#         E1.as_parameter_operatable.force_get()
#     )
#     assert res == set()

#     E2 = E.add(E1, A)

#     res = MutatorUtils.get_expressions_involved_in(
#         E1.as_parameter_operatable.force_get()
#     )
#     assert res == {fabll.Traits(E2).get_obj_raw()}

#     E3 = E.add(E2, B)

#     res = MutatorUtils.get_expressions_involved_in(
#         E1.as_parameter_operatable.force_get()
#     )
#     assert res == {fabll.Traits(E2).get_obj_raw(), fabll.Traits(E3).get_obj_raw()}

#     res = MutatorUtils.get_expressions_involved_in(
#         E2.as_parameter_operatable.force_get()
#     )
#     assert res == {fabll.Traits(E3).get_obj_raw()}

#     res = MutatorUtils.get_expressions_involved_in(
#         E2.as_parameter_operatable.force_get(), up_only=False
#     )
#     assert res == {fabll.Traits(E1).get_obj_raw(), fabll.Traits(E3).get_obj_raw()}

#     res = MutatorUtils.get_expressions_involved_in(
#         E2.as_parameter_operatable.force_get(),
#         up_only=False,
#         include_root=True,
#     )
#     assert res == {
#         fabll.Traits(E1).get_obj_raw(),
#         fabll.Traits(E2).get_obj_raw(),
#         fabll.Traits(E3).get_obj_raw(),
#     }


def test_mutation_map_compressed_mapping_forwards_identity():
    E = BoundExpressions()
    context, _ = _create_letters(E, 3)

    mapping = MutationMap.bootstrap(E.tg, E.g, print_context=context)

    f = mapping.compressed_mapping_forwards
    assert set(f.keys()) == mapping.input_operables
    assert all(v.maps_to in mapping.output_operables for v in f.values())


def test_mutation_map_compressed_mapping_backwards_identity():
    E = BoundExpressions()
    context, _ = _create_letters(E, 3)

    mapping = MutationMap.bootstrap(E.tg, E.g, print_context=context)

    expected = {
        out_op: [in_op]
        for in_op, out_op in mapping.compressed_mapping_forwards_complete.items()
    }
    assert mapping.compressed_mapping_backwards == expected


def test_mutation_map_compressed_mapping_backwards_copy():
    E = BoundExpressions()
    context, _ = _create_letters(E, 3)
    mapping = MutationMap.bootstrap(E.tg, E.g, print_context=context)
    variables_mid = list(mapping.output_operables)

    E2 = BoundExpressions()
    _, variables_new = _create_letters(E2, 3)
    variables_new = [v for v in variables_new]

    mapping_new = mapping.extend(
        MutationStage(
            tg_in=mapping.tg_out,
            tg_out=E2.tg,
            G_in=mapping.G_out,
            G_out=E2.g,
            algorithm="Test",
            iteration=0,
            print_ctx=mapping.print_ctx,
            transformations=Transformations(
                print_ctx=mapping.print_ctx,
                mutated=dict(zip(variables_mid, variables_new)),
                copied=set(variables_mid),
            ),
        )
    )

    expected = {
        v_new: [v_orig]
        for v_new, v_orig in zip(
            variables_new, [mapping.map_backward(v_mid)[0] for v_mid in variables_mid]
        )
    }
    assert mapping_new.compressed_mapping_backwards == expected


def test_mutation_map_compressed_mapping_backwards_mutate():
    E = BoundExpressions()
    context, _ = _create_letters(E, 3)
    mapping = MutationMap.bootstrap(E.tg, E.g, print_context=context)
    variables_mid = list(mapping.output_operables)

    E2 = BoundExpressions()
    _, variables_new = _create_letters(E2, 3)
    variables_new = [v for v in variables_new]

    mapping_new = mapping.extend(
        MutationStage(
            tg_in=mapping.tg_out,
            tg_out=E2.tg,
            G_in=mapping.G_out,
            G_out=E2.g,
            algorithm="Test",
            iteration=0,
            print_ctx=mapping.print_ctx,
            transformations=Transformations(
                print_ctx=mapping.print_ctx,
                mutated=dict(zip(variables_mid, variables_new)),
            ),
        )
    )

    expected = {
        v_new: [v_orig]
        for v_new, v_orig in zip(
            variables_new, [mapping.map_backward(v_mid)[0] for v_mid in variables_mid]
        )
    }
    assert mapping_new.compressed_mapping_backwards == expected


def test_mutation_map_non_copy_mutated_identity():
    E = BoundExpressions()
    context, _ = _create_letters(E, 3)

    mapping = MutationMap.bootstrap(E.tg, E.g, print_context=context)

    res = mapping.non_trivial_mutated_expressions
    assert res == set()


def test_mutation_map_non_copy_mutated_mutate():
    E = BoundExpressions()
    context, variables = _create_letters(E, 3)
    variables = [v for v in variables]

    mapping = MutationMap.bootstrap(E.tg, E.g, print_context=context)

    E2 = BoundExpressions()
    _, variables_new = _create_letters(E2, 3)
    variables_new = [v for v in variables_new]

    mapping_new = mapping.extend(
        MutationStage(
            tg_in=E.tg,
            tg_out=E2.tg,
            G_in=E.g,
            G_out=E2.g,
            algorithm="Test",
            iteration=0,
            print_ctx=mapping.print_ctx,
            transformations=Transformations(
                print_ctx=mapping.print_ctx,
                mutated=dict(zip(variables, variables_new)),
            ),
        )
    )

    res = mapping_new.non_trivial_mutated_expressions
    assert res == set()


def test_mutation_map_non_copy_mutated_mutate_expression():
    E = BoundExpressions()
    context, variables = _create_letters(E, 2)
    op = E.add(*[v.as_operand.get() for v in variables])

    mapping = MutationMap.bootstrap(E.tg, E.g, print_context=context)

    E2 = BoundExpressions()
    _, variables_new = _create_letters(E2, 2)
    op_new = E2.multiply(*[v.as_operand.get() for v in variables_new])

    mapping_new = mapping.extend(
        MutationStage(
            tg_in=E.tg,
            tg_out=E2.tg,
            G_in=E.g,
            G_out=E2.g,
            algorithm="Test",
            iteration=0,
            print_ctx=mapping.print_ctx,
            transformations=Transformations(
                print_ctx=mapping.print_ctx,
                mutated=dict(zip(variables, variables_new)) | {op: op_new},  # type: ignore
            ),
        )
    )

    res = mapping_new.non_trivial_mutated_expressions
    assert res == {op_new.as_parameter_operatable.force_get().as_expression.force_get()}


def test_mutation_map_submap():
    E = BoundExpressions()
    context, variables = _create_letters(E, 2)
    op = E.add(*[v.as_operand.get() for v in variables])

    mapping = MutationMap.bootstrap(E.tg, E.g, print_context=context)

    E2 = BoundExpressions()
    _, variables_new = _create_letters(E2, 2)
    op_new = E2.multiply(*[v.as_operand.get() for v in variables_new])

    mapping_new = mapping.extend(  # noqa: F841
        MutationStage(
            tg_in=E.tg,
            tg_out=E2.tg,
            G_in=E.g,
            G_out=E2.g,
            algorithm="Test",
            iteration=0,
            print_ctx=mapping.print_ctx,
            transformations=Transformations.identity(
                E.tg,
                E.g,
                input_print_context=mapping.print_ctx,
            ),
        )
    )
    mapping_new2 = mapping.extend(  # noqa: F841
        MutationStage(
            tg_in=E.tg,
            tg_out=E2.tg,
            G_in=E.g,
            G_out=E2.g,
            algorithm="Test",
            iteration=0,
            print_ctx=mapping.print_ctx,
            transformations=Transformations(
                print_ctx=mapping.print_ctx,
                mutated=dict(zip(variables, variables_new)) | {op: op_new},  # type: ignore
            ),
        )
    )

    # TODO


def test_traceback_filtering_chain():
    E = BoundExpressions()
    context, variables = _create_letters(E, 3)
    A, B, C = variables

    E1 = E.add(A.as_operand.get(), B.as_operand.get())
    E2 = E.add(E1, A.as_operand.get())

    solver = Solver()
    out = solver.simplify(E.tg, E.g, print_context=context, terminal=False)

    E2_new = out.data.mutation_map.map_forward(
        E2.as_parameter_operatable.force_get()
    ).maps_to
    assert E2_new
    tb = out.data.mutation_map.get_traceback(E2_new)
    logger.info(tb.filtered())


def test_traceback_filtering_tree():
    E = BoundExpressions()
    context, variables = _create_letters(E, 3)
    A, B, C = variables

    E.is_subset(B.as_operand.get(), E.lit_op_range((0, 10)), assert_=True)
    E.is_subset(C.as_operand.get(), E.lit_op_range((5, 15)), assert_=True)

    E.is_subset(A.as_operand.get(), B.as_operand.get(), assert_=True)
    E.is_subset(A.as_operand.get(), C.as_operand.get(), assert_=True)

    solver = Solver()
    out = solver.simplify(E.tg, E.g, print_context=context, terminal=True)

    A_new = out.data.mutation_map.map_forward(A).maps_to
    assert A_new
    tb = out.data.mutation_map.get_traceback(A_new)
    logger.info(rich_to_string(tb.filtered().as_rich_tree()))

    # A{⊆|([5, 10])} <-
    #  CONSTRAINED[Transitive subset]  <- A{⊆|([0, ∞])}
    #   MUTATED[Constrain within]  <- A
    #    MUTATED[Canonical literal]  <- A:  *46E8.A


def test_contradiction_message_subset():
    E = BoundExpressions()
    context, variables = _create_letters(E, 1)
    (A,) = variables

    E.is_subset(A.as_operand.get(), E.lit_op_range((6, 7)), assert_=True)
    E.is_subset(A.as_operand.get(), E.lit_op_range((4, 5)), assert_=True)

    solver = Solver()

    with pytest.raises(ContradictionByLiteral, match="Empty superset"):
        solver.simplify(E.tg, E.g, print_context=context, terminal=True)


@pytest.mark.skip(reason="to_fix")  # FIXME
def test_contradiction_message_superset():
    E = BoundExpressions()
    context, variables = _create_letters(E, 1)
    (A,) = variables

    E.is_superset(A.as_operand.get(), E.lit_op_range((0, 10)), assert_=True)
    E.is_subset(A.as_operand.get(), E.lit_op_range((4, 5)), assert_=True)

    solver = Solver()

    with pytest.raises(ContradictionByLiteral, match=r"P!\{⊆\|False\}"):
        solver.simplify(E.tg, E.g, print_context=context, terminal=True)


if __name__ == "__main__":
    test_mutation_map_non_copy_mutated_mutate_expression()
