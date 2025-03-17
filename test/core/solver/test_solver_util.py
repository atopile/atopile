# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import pytest

from faebryk.core.cpp import Graph
from faebryk.core.node import Node
from faebryk.core.parameter import (
    Add,
    And,
    Difference,
    Divide,
    Expression,
    Intersection,
    Is,
    Logic,
    Multiply,
    Or,
    Parameter,
    ParameterOperatable,
    Subtract,
    Union,
    Xor,
)
from faebryk.core.solver.algorithm import algorithm
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.core.solver.mutator import (
    MutationMap,
    MutationStage,
    Mutator,
    Transformations,
)
from faebryk.core.solver.utils import (
    Associative,
    ContradictionByLiteral,
    FullyAssociative,
    MutatorUtils,
)
from faebryk.libs.library import L
from faebryk.libs.logging import rich_to_string
from faebryk.libs.units import P
from faebryk.libs.util import cast_assert, times

logger = logging.getLogger(__name__)


def _create_letters(
    n: int,
) -> tuple[ParameterOperatable.ReprContext, list[Parameter], Graph]:
    context = ParameterOperatable.ReprContext()

    out = []

    class App(Node):
        def __preinit__(self) -> None:
            for _ in range(n):
                p = Parameter()
                name = p.compact_repr(context)
                self.add(p, name)
                out.append(p)

    app = App()
    return context, out, app.get_graph()


@pytest.mark.parametrize(
    "op",
    [
        Add,
        Multiply,
        Subtract,
        Divide,
        And,
        Or,
        Xor,
        Union,
        Intersection,
        Difference,
    ],
)
def test_flatten_associative(op: type[Expression]):
    def flatten(op):
        return MutatorUtils.flatten_associative(op, lambda _, __: True)

    if issubclass(op, Logic):
        domain = L.Domains.BOOL()
    else:
        domain = L.Domains.Numbers.REAL()

    A, B, C, D, E = times(5, lambda: Parameter(domain=domain))

    to_flatten = op(op(A, B), C, op(D, E))
    res = flatten(to_flatten)

    if not issubclass(op, Associative):
        assert len(res.destroyed_operations) == 0
        assert set(res.extracted_operands) == set(to_flatten.operands)
        return

    if not issubclass(op, FullyAssociative):
        assert set(res.extracted_operands) & {A, B, C}
        assert not set(res.extracted_operands) & {D, E}
        assert len(res.destroyed_operations) == 1
        return

    assert set(res.extracted_operands) == {A, B, C, D, E}
    assert len(res.destroyed_operations) == 2


def test_mutator_no_graph_merge():
    p0 = Parameter(units=P.V)
    p1 = Parameter(units=P.A)
    p2 = Parameter(units=P.W)
    alias = p2.alias_is(p0 * p1)

    p3 = Parameter(units=P.V)

    context = ParameterOperatable.ReprContext()

    @algorithm("")
    def algo(mutator: Mutator):
        pass

    mutator = Mutator(
        MutationMap.identity(p0.get_graph(), print_context=context),
        algo=algo,
        iteration=0,
        terminal=True,
    )
    p0_new = cast_assert(Parameter, mutator.get_copy(p0))
    p3_new = cast_assert(Parameter, mutator.get_copy(p3))
    alias_new = cast_assert(Is, mutator.get_copy(alias))

    G = p0.get_graph()
    G_new = p0_new.get_graph()

    assert G is not G_new
    assert alias_new.get_graph() is G_new
    assert p3_new.get_graph() is not G_new
    assert cast_assert(Parameter, mutator.get_mutated(p1)).get_graph() is G_new


def test_get_expressions_involved_in():
    A = Parameter()
    B = Parameter()

    E1 = A + B

    res = MutatorUtils.get_expressions_involved_in(E1)
    assert res == set()

    E2 = E1 + A

    res = MutatorUtils.get_expressions_involved_in(E1)
    assert res == {E2}

    E3 = E2 + B

    res = MutatorUtils.get_expressions_involved_in(E1)
    assert res == {E2, E3}

    res = MutatorUtils.get_expressions_involved_in(E2)
    assert res == {E3}

    res = MutatorUtils.get_expressions_involved_in(E2, up_only=False)
    assert res == {E1, E3}

    res = MutatorUtils.get_expressions_involved_in(E2, up_only=False, include_root=True)
    assert res == {E1, E2, E3}


def test_get_correlations_basic():
    A = Parameter()
    B = Parameter()
    C = Parameter()

    # Create correlations between parameters
    o = A.alias_is(B)  # A and B are correlated through an Is expression

    # Create an expression with correlated operands
    expr = Add(A, B, C)

    # Test correlations
    correlations = list(MutatorUtils.get_correlations(expr))

    # We expect A and B to be correlated
    assert len(correlations) == 1

    # Unpack the correlation
    op1, op2, overlap_exprs = correlations[0]

    # Check that the correlated operands are A and B
    assert {op1, op2} == {A, B}
    assert overlap_exprs == {o}


def test_get_correlations_nested_uncorrelated():
    A = Parameter()
    B = Parameter()
    C = Parameter()

    o = A.alias_is(B)  # A and B are correlated through an Is expression
    inner = A + B
    expr = inner + C
    correlations = list(MutatorUtils.get_correlations(expr))
    inner_correlations = list(MutatorUtils.get_correlations(inner))

    # no correlations between C and (A + B)
    assert not correlations

    assert len(inner_correlations) == 1
    op1, op2, overlap_exprs = inner_correlations[0]
    assert {op1, op2} == {A, B}
    assert overlap_exprs == {o}


def test_get_correlations_nested_correlated():
    A = Parameter()
    B = Parameter()
    C = Parameter()

    o = A.alias_is(B)  # A and B are correlated through an Is expression
    inner = A + C
    expr = inner + B
    correlations = list(MutatorUtils.get_correlations(expr))
    inner_correlations = list(MutatorUtils.get_correlations(inner))

    # no correlations between C and A
    assert not inner_correlations

    assert len(correlations) == 1
    op1, op2, overlap_exprs = correlations[0]
    assert {op1, op2} == {inner, B}
    assert overlap_exprs == {o}


def test_get_correlations_self_correlated():
    A = Parameter()
    E = A + A
    correlations = list(MutatorUtils.get_correlations(E))
    assert len(correlations) == 1
    op1, op2, overlap_exprs = correlations[0]
    assert {op1, op2} == {A}
    assert not overlap_exprs


def test_get_correlations_shared_predicates():
    A = Parameter()
    B = Parameter()

    E = A + B

    correlations = list(MutatorUtils.get_correlations(E))
    assert not correlations

    E2 = Is(A * B, L.Range(0, 10))

    correlations = list(MutatorUtils.get_correlations(E))
    assert not correlations

    E2.constrain()

    correlations = list(MutatorUtils.get_correlations(E))
    assert len(correlations) == 1

    op1, op2, overlap_exprs = correlations[0]
    assert {op1, op2} == {A, B}
    assert overlap_exprs == {E2}


def test_get_correlations_correlated_regression():
    A = Parameter()
    B = Parameter()

    A.alias_is(L.Range(5, 10))
    B.alias_is(L.Range(10, 15))

    # correlate
    o = B.alias_is(A + 5)

    a_neg = A * -1
    E = B + a_neg

    correlations = list(MutatorUtils.get_correlations(E))
    assert len(correlations) == 1

    op1, op2, overlap_exprs = correlations[0]
    assert {op1, op2} == {a_neg, B}
    assert overlap_exprs == {o}


def test_mutation_map_compressed_mapping_forwards_identity():
    context, variables, graph = _create_letters(3)

    mapping = MutationMap.identity(graph, print_context=context)

    f = mapping.compressed_mapping_forwards
    assert {k: v.maps_to for k, v in f.items()} == {v: v for v in variables}


def test_mutation_map_compressed_mapping_backwards_identity():
    context, variables, graph = _create_letters(3)

    mapping = MutationMap.identity(graph, print_context=context)

    b = mapping.compressed_mapping_backwards
    assert b == {v: [v] for v in variables}


def test_mutation_map_compressed_mapping_backwards_copy():
    context, variables, graph = _create_letters(3)

    mapping = MutationMap.identity(graph, print_context=context)

    _, variables_new, graph_new = _create_letters(3)

    mapping_new = mapping.extend(
        MutationStage(
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
    context, variables, graph = _create_letters(3)

    mapping = MutationMap.identity(graph, print_context=context)

    _, variables_new, graph_new = _create_letters(3)

    mapping_new = mapping.extend(
        MutationStage(
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
    context, variables, graph = _create_letters(3)

    mapping = MutationMap.identity(graph, print_context=context)

    res = mapping.non_trivial_mutated_expressions
    assert res == set()


def test_mutation_map_non_copy_mutated_mutate():
    context, variables, graph = _create_letters(3)

    mapping = MutationMap.identity(graph, print_context=context)

    _, variables_new, graph_new = _create_letters(3)

    mapping_new = mapping.extend(
        MutationStage(
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
    context, variables, graph = _create_letters(2)
    op = Add(*variables)

    mapping = MutationMap.identity(graph, print_context=context)

    _, variables_new, graph_new = _create_letters(2)
    op_new = Multiply(*variables_new)

    mapping_new = mapping.extend(
        MutationStage(
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
    assert res == {op_new}


def test_mutation_map_submap():
    context, variables, graph = _create_letters(2)
    op = Add(*variables)

    mapping = MutationMap.identity(graph, print_context=context)

    _, variables_new, graph_new = _create_letters(2)
    op_new = Multiply(*variables_new)

    mapping_new = mapping.extend(  # noqa: F841
        MutationStage(
            algorithm="Test",
            iteration=0,
            print_context=mapping.output_print_context,
            transformations=Transformations.identity(
                graph,
                input_print_context=mapping.output_print_context,
            ),
        )
    )
    mapping_new2 = mapping.extend(  # noqa: F841
        MutationStage(
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
    context, variables, graph = _create_letters(3)
    A, B, C = variables

    E = A + B
    E2 = E + A

    solver = DefaultSolver()
    out = solver.simplify_symbolically(E2, print_context=context, terminal=False)

    E2_new = out.data.mutation_map.map_forward(E2).maps_to
    assert E2_new
    tb = out.data.mutation_map.get_traceback(E2_new)
    logger.info(tb.filtered())


def test_traceback_filtering_tree():
    context, variables, graph = _create_letters(3)
    A, B, C = variables

    B.constrain_subset(L.Range(0, 10))
    C.constrain_subset(L.Range(5, 15))

    A.constrain_subset(B)
    A.constrain_subset(C)

    solver = DefaultSolver()
    out = solver.simplify_symbolically(A, print_context=context, terminal=True)

    A_new = out.data.mutation_map.map_forward(A).maps_to
    assert A_new
    tb = out.data.mutation_map.get_traceback(A_new)
    logger.info(rich_to_string(tb.filtered().as_rich_tree()))

    # A{S|([5, 10])} <-
    #  CONSTRAINED[Transitive subset]  <- A{S|([0, ∞])}
    #   MUTATED[Constrain within]  <- A
    #    MUTATED[Canonical literal]  <- A:  *46E8.A


def test_contradiction_message_subset():
    context, variables, graph = _create_letters(1)
    (A,) = variables

    A.constrain_subset(L.Range(6, 7))
    A.alias_is(L.Range(4, 5))

    solver = DefaultSolver()

    with pytest.raises(ContradictionByLiteral, match="is lit not subset of ss lits"):
        solver.simplify_symbolically(A, print_context=context, terminal=True)


def test_contradiction_message_superset():
    context, variables, graph = _create_letters(1)
    (A,) = variables

    A.constrain_superset(L.Range(0, 10))
    A.alias_is(L.Range(4, 5))

    solver = DefaultSolver()

    with pytest.raises(
        ContradictionByLiteral, match="Contradiction: Incompatible literal subsets"
    ):
        solver.simplify_symbolically(A, print_context=context, terminal=True)
