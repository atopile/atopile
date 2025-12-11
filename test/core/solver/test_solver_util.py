# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import sys
from pathlib import Path

import pytest

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.algorithm import algorithm
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.core.solver.mutator import (
    MutationMap,
    MutationStage,
    Mutator,
    Transformations,
)
from faebryk.core.solver.utils import (
    ContradictionByLiteral,
    MutatorUtils,
)
from faebryk.libs.logging import rich_to_string

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
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
    | F.Expressions.Union
    | F.Expressions.Intersection
    | F.Expressions.Difference
)


@pytest.mark.parametrize(
    "op",
    [
        F.Expressions.Add,
        F.Expressions.Multiply,
        F.Expressions.Subtract,
        F.Expressions.Divide,
        F.Expressions.And,
        F.Expressions.Or,
        F.Expressions.Xor,
        F.Expressions.Union,
        F.Expressions.Intersection,
        F.Expressions.Difference,
    ],
)
def test_flatten_associative(op: type[Flattenable]):
    E = BoundExpressions()

    def flatten(is_flattenable: "F.Expressions.is_flattenable"):
        return MutatorUtils.flatten_associative(is_flattenable, lambda _, __: True)

    # TODO: add logic trait to classify logic expressions
    if op in [F.Expressions.And.c, F.Expressions.Or.c, F.Expressions.Xor.c]:
        A, B, C, D, H = [E.bool_parameter_op() for _ in range(5)]
    else:
        A, B, C, D, H = [E.parameter_op() for _ in range(5)]

    to_flatten_op = op.c(op.c(A, B), C, op.c(D, H))
    to_flatten_expression = fabll.Traits(to_flatten_op).get_obj(op)
    res = flatten(to_flatten_expression.is_flattenable.get())

    # Get the parent class from the classmethod
    # (e.g., F.Expressions.Add.c -> F.Expressions.Add)

    if not to_flatten_expression.try_get_trait(F.Expressions.is_flattenable):
        assert len(res.destroyed_operations) == 0
        return

    if not to_flatten_expression.try_get_trait(F.Expressions.is_associative):
        assert set(res.extracted_operands) & {A, B, C}
        assert not set(res.extracted_operands) & {D, E}
        assert len(res.destroyed_operations) == 1
        return

    assert set(res.extracted_operands) == {A, B, C, D, H}
    assert len(res.destroyed_operations) == 2


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
    p0_new = mutator.get_copy(p0)
    alias_new = fabll.Traits(mutator.get_copy(alias)).get_obj(F.Expressions.Is)

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


def test_get_expressions_involved_in():
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()

    E1 = E.add(A, B)

    res = MutatorUtils.get_expressions_involved_in(
        E1.as_parameter_operatable.force_get()
    )
    assert res == set()

    E2 = E.add(E1, A)

    res = MutatorUtils.get_expressions_involved_in(
        E1.as_parameter_operatable.force_get()
    )
    assert res == {fabll.Traits(E2).get_obj_raw()}

    E3 = E.add(E2, B)

    res = MutatorUtils.get_expressions_involved_in(
        E1.as_parameter_operatable.force_get()
    )
    assert res == {fabll.Traits(E2).get_obj_raw(), fabll.Traits(E3).get_obj_raw()}

    res = MutatorUtils.get_expressions_involved_in(
        E2.as_parameter_operatable.force_get()
    )
    assert res == {fabll.Traits(E3).get_obj_raw()}

    res = MutatorUtils.get_expressions_involved_in(
        E2.as_parameter_operatable.force_get(), up_only=False
    )
    assert res == {fabll.Traits(E1).get_obj_raw(), fabll.Traits(E3).get_obj_raw()}

    res = MutatorUtils.get_expressions_involved_in(
        E2.as_parameter_operatable.force_get(),
        up_only=False,
        include_root=True,
    )
    assert res == {
        fabll.Traits(E1).get_obj_raw(),
        fabll.Traits(E2).get_obj_raw(),
        fabll.Traits(E3).get_obj_raw(),
    }


def test_get_correlations_basic():
    E = BoundExpressions()

    A = E.parameter_op()
    B = E.parameter_op()
    C = E.parameter_op()

    # Create correlations between parameters
    # A and B are correlated through an Is expression
    o = E.is_(A, B, assert_=True)

    # Create an expression with correlated operands
    expr = E.add(A, B, C)

    # Test correlations
    correlations = list(
        MutatorUtils.get_correlations(
            expr.as_parameter_operatable.force_get().as_expression.force_get()
        )
    )

    # We expect A and B to be correlated
    assert len(correlations) == 1

    # Unpack the correlation
    op1, op2, overlap_exprs = correlations[0]

    # Check that the correlated operands are A and B
    assert {op1, op2} == {
        A.as_parameter_operatable.force_get(),
        B.as_parameter_operatable.force_get(),
    }
    assert overlap_exprs == {fabll.Traits(o).get_obj_raw()}


def test_get_correlations_nested_uncorrelated():
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()
    C = E.parameter_op()

    o = E.is_(A, B, assert_=True)  # A and B are correlated through an Is expression
    inner = E.add(A, B)
    expr = E.add(inner, C)
    correlations = list(
        MutatorUtils.get_correlations(
            expr.as_parameter_operatable.force_get().as_expression.force_get()
        )
    )
    inner_correlations = list(
        MutatorUtils.get_correlations(
            inner.as_parameter_operatable.force_get().as_expression.force_get()
        )
    )

    # no correlations between C and (A + B)
    assert not correlations

    assert len(inner_correlations) == 1
    op1, op2, overlap_exprs = inner_correlations[0]
    assert {op1, op2} == {
        A.as_parameter_operatable.force_get(),
        B.as_parameter_operatable.force_get(),
    }
    assert overlap_exprs == {fabll.Traits(o).get_obj_raw()}


def test_get_correlations_nested_correlated():
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()
    C = E.parameter_op()

    o = E.is_(A, B, assert_=True)  # A and B are correlated through an Is expression
    inner = E.add(A, C)
    expr = E.add(inner, B)
    correlations = list(
        MutatorUtils.get_correlations(
            expr.as_parameter_operatable.force_get().as_expression.force_get()
        )
    )
    inner_correlations = list(
        MutatorUtils.get_correlations(
            inner.as_parameter_operatable.force_get().as_expression.force_get()
        )
    )

    # no correlations between C and A
    assert not inner_correlations

    assert len(correlations) == 1
    op1, op2, overlap_exprs = correlations[0]
    assert {op1, op2} == {
        inner.as_parameter_operatable.force_get(),
        B.as_parameter_operatable.force_get(),
    }
    assert overlap_exprs == {fabll.Traits(o).get_obj_raw()}


def test_get_correlations_self_correlated():
    E = BoundExpressions()
    A = E.parameter_op()
    expr = F.Expressions.Add.c(A, A)
    correlations = list(
        MutatorUtils.get_correlations(
            expr.as_parameter_operatable.force_get().as_expression.force_get()
        )
    )
    assert len(correlations) == 1
    op1, op2, overlap_exprs = correlations[0]
    assert {op1, op2} == {A.as_parameter_operatable.force_get()}
    assert not overlap_exprs


def test_get_correlations_shared_predicates():
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()

    Ex = E.add(A, B)

    correlations = list(
        MutatorUtils.get_correlations(
            Ex.as_parameter_operatable.force_get().as_expression.force_get()
        )
    )
    assert not correlations

    E2 = E.is_(E.multiply(A, B), E.lit_op_range((0, 10)))

    correlations = list(
        MutatorUtils.get_correlations(
            Ex.as_parameter_operatable.force_get().as_expression.force_get()
        )
    )
    assert not correlations

    E2.as_parameter_operatable.force_get().as_expression.force_get().as_assertable.force_get().assert_()

    correlations = list(
        MutatorUtils.get_correlations(
            Ex.as_parameter_operatable.force_get().as_expression.force_get()
        )
    )
    assert len(correlations) == 1

    op1, op2, overlap_exprs = correlations[0]
    assert {op1, op2} == {
        A.as_parameter_operatable.force_get(),
        B.as_parameter_operatable.force_get(),
    }
    assert overlap_exprs == {fabll.Traits(E2).get_obj_raw()}


def test_get_correlations_correlated_regression():
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()

    E.is_(A, E.lit_op_range((5, 10)), assert_=True)
    E.is_(B, E.lit_op_range((10, 15)), assert_=True)

    # correlate
    o = E.is_(B, E.add(A, E.lit_op_single(5)), assert_=True)

    a_neg = E.multiply(A, E.lit_op_single(-1))
    Ex = E.add(B, a_neg)

    correlations = list(
        MutatorUtils.get_correlations(
            Ex.as_parameter_operatable.force_get().as_expression.force_get()
        )
    )
    assert len(correlations) == 1

    op1, op2, overlap_exprs = correlations[0]
    assert {op1, op2} == {
        a_neg.as_parameter_operatable.force_get(),
        B.as_parameter_operatable.force_get(),
    }
    assert overlap_exprs == {fabll.Traits(o).get_obj_raw()}


def test_mutation_map_compressed_mapping_forwards_identity():
    E = BoundExpressions()
    context, variables = _create_letters(E, 3)

    mapping = MutationMap.bootstrap(E.tg, E.g, print_context=context)

    f = mapping.compressed_mapping_forwards
    assert {k: v.maps_to for k, v in f.items()} == {v: v for v in variables}


def test_mutation_map_compressed_mapping_backwards_identity():
    E = BoundExpressions()
    context, variables = _create_letters(E, 3)

    mapping = MutationMap.bootstrap(E.tg, E.g, print_context=context)

    b = mapping.compressed_mapping_backwards
    assert b == {v: [v] for v in variables}


def test_mutation_map_compressed_mapping_backwards_copy():
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
            print_context=mapping.output_print_context,
            transformations=Transformations(
                input_print_context=mapping.output_print_context,
                mutated=dict(zip(variables, variables_new)),
                copied=set(variables),
            ),
        )
    )

    b = mapping_new.compressed_mapping_backwards
    expected = {v_new: [v] for v, v_new in zip(variables, variables_new)}
    assert b == expected


def test_mutation_map_compressed_mapping_backwards_mutate():
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
            print_context=mapping.output_print_context,
            transformations=Transformations(
                input_print_context=mapping.output_print_context,
                mutated=dict(zip(variables, variables_new)),
            ),
        )
    )

    b = mapping_new.compressed_mapping_backwards
    expected = {v_new: [v] for v, v_new in zip(variables, variables_new)}
    assert b == expected


def test_mutation_map_non_copy_mutated_identity():
    E = BoundExpressions()
    context, variables = _create_letters(E, 3)

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
            print_context=mapping.output_print_context,
            transformations=Transformations(
                input_print_context=mapping.output_print_context,
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
            print_context=mapping.output_print_context,
            transformations=Transformations(
                input_print_context=mapping.output_print_context,
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
            print_context=mapping.output_print_context,
            transformations=Transformations.identity(
                E.tg,
                E.g,
                input_print_context=mapping.output_print_context,
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
            print_context=mapping.output_print_context,
            transformations=Transformations(
                input_print_context=mapping.output_print_context,
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

    solver = DefaultSolver()
    out = solver.simplify_symbolically(E.tg, E.g, print_context=context, terminal=False)

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

    solver = DefaultSolver()
    out = solver.simplify_symbolically(E.tg, E.g, print_context=context, terminal=True)

    A_new = out.data.mutation_map.map_forward(A).maps_to
    assert A_new
    tb = out.data.mutation_map.get_traceback(A_new)
    logger.info(rich_to_string(tb.filtered().as_rich_tree()))

    # A{S|([5, 10])} <-
    #  CONSTRAINED[Transitive subset]  <- A{S|([0, ∞])}
    #   MUTATED[Constrain within]  <- A
    #    MUTATED[Canonical literal]  <- A:  *46E8.A


def test_contradiction_message_subset():
    E = BoundExpressions()
    context, variables = _create_letters(E, 1)
    (A,) = variables

    E.is_subset(A.as_operand.get(), E.lit_op_range((6, 7)), assert_=True)
    E.is_(A.as_operand.get(), E.lit_op_range((4, 5)), assert_=True)

    solver = DefaultSolver()

    with pytest.raises(ContradictionByLiteral, match="is lit not subset of ss lits"):
        solver.simplify_symbolically(E.tg, E.g, print_context=context, terminal=True)


def test_contradiction_message_superset():
    E = BoundExpressions()
    context, variables = _create_letters(E, 1)
    (A,) = variables

    E.is_superset(A.as_operand.get(), E.lit_op_range((0, 10)), assert_=True)
    E.is_(A.as_operand.get(), E.lit_op_range((4, 5)), assert_=True)

    solver = DefaultSolver()

    with pytest.raises(
        ContradictionByLiteral, match="Contradiction: Incompatible literal subsets"
    ):
        solver.simplify_symbolically(E.tg, E.g, print_context=context, terminal=True)


if __name__ == "__main__":
    test_mutation_map_non_copy_mutated_mutate_expression()
