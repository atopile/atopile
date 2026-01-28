# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import sys
from pathlib import Path

import pytest

import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.logging import BaseLogger
from faebryk.core.solver.algorithm import algorithm
from faebryk.core.solver.mutator import (
    MutationMap,
    MutationStage,
    Mutator,
    Transformations,
    is_irrelevant,
    is_relevant,
)
from faebryk.core.solver.solver import Solver
from faebryk.core.solver.utils import (
    ContradictionByLiteral,
)

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

    @algorithm("")
    def algo(mutator: Mutator):
        pass

    mutator = Mutator(
        MutationMap.bootstrap(p0.tg, p0.g),
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
    _ = _create_letters(E, 3)

    mapping = MutationMap.bootstrap(E.tg, E.g)

    f = mapping.compressed_mapping_forwards
    assert set(f.keys()) == mapping.input_operables
    assert all(v.maps_to in mapping.output_operables for v in f.values())


def test_mutation_map_compressed_mapping_backwards_identity():
    E = BoundExpressions()
    _ = _create_letters(E, 3)

    mapping = MutationMap.bootstrap(E.tg, E.g)

    expected = {
        out_op: [in_op]
        for in_op, out_op in mapping.compressed_mapping_forwards_complete.items()
    }
    assert mapping.compressed_mapping_backwards == expected


def test_mutation_map_compressed_mapping_backwards_copy():
    E = BoundExpressions()
    _ = _create_letters(E, 3)
    mapping = MutationMap.bootstrap(E.tg, E.g)
    variables_mid = list(mapping.output_operables)

    E2 = BoundExpressions()
    variables_new = _create_letters(E2, 3)

    mapping_new = mapping.extend(
        MutationStage(
            tg_in=mapping.tg_out,
            tg_out=E2.tg,
            G_in=mapping.G_out,
            G_out=E2.g,
            algorithm="Test",
            iteration=0,
            transformations=Transformations(
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
    _ = _create_letters(E, 3)
    mapping = MutationMap.bootstrap(E.tg, E.g)
    variables_mid = list(mapping.output_operables)

    E2 = BoundExpressions()
    variables_new = _create_letters(E2, 3)

    mapping_new = mapping.extend(
        MutationStage(
            tg_in=mapping.tg_out,
            tg_out=E2.tg,
            G_in=mapping.G_out,
            G_out=E2.g,
            algorithm="Test",
            iteration=0,
            transformations=Transformations(
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
    _ = _create_letters(E, 3)

    mapping = MutationMap.bootstrap(E.tg, E.g)

    res = mapping.non_trivial_mutated_expressions
    assert res == set()


def test_mutation_map_non_copy_mutated_mutate():
    E = BoundExpressions()
    variables = _create_letters(E, 3)
    variables = [v for v in variables]

    mapping = MutationMap.bootstrap(E.tg, E.g)

    E2 = BoundExpressions()
    variables_new = _create_letters(E2, 3)

    mapping_new = mapping.extend(
        MutationStage(
            tg_in=E.tg,
            tg_out=E2.tg,
            G_in=E.g,
            G_out=E2.g,
            algorithm="Test",
            iteration=0,
            transformations=Transformations(
                mutated=dict(zip(variables, variables_new)),
            ),
        )
    )

    res = mapping_new.non_trivial_mutated_expressions
    assert res == set()


def test_mutation_map_non_copy_mutated_mutate_expression():
    E = BoundExpressions()
    variables = _create_letters(E, 2)
    op = E.add(*[v.as_operand.get() for v in variables])

    mapping = MutationMap.bootstrap(E.tg, E.g)

    E2 = BoundExpressions()
    variables_new = _create_letters(E2, 2)
    op_new = E2.multiply(*[v.as_operand.get() for v in variables_new])

    mapping_new = mapping.extend(
        MutationStage(
            tg_in=E.tg,
            tg_out=E2.tg,
            G_in=E.g,
            G_out=E2.g,
            algorithm="Test",
            iteration=0,
            transformations=Transformations(
                mutated=dict(zip(variables, variables_new)) | {op: op_new},  # type: ignore
            ),
        )
    )

    res = mapping_new.non_trivial_mutated_expressions
    assert res == {op_new.as_parameter_operatable.force_get().as_expression.force_get()}


def test_mutation_map_submap():
    E = BoundExpressions()
    variables = _create_letters(E, 2)
    op = E.add(*[v.as_operand.get() for v in variables])

    mapping = MutationMap.bootstrap(E.tg, E.g)

    E2 = BoundExpressions()
    variables_new = _create_letters(E2, 2)
    op_new = E2.multiply(*[v.as_operand.get() for v in variables_new])

    mapping_new = mapping.extend(  # noqa: F841
        MutationStage(
            tg_in=E.tg,
            tg_out=E2.tg,
            G_in=E.g,
            G_out=E2.g,
            algorithm="Test",
            iteration=0,
            transformations=Transformations.identity(E.tg, E.g),
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
            transformations=Transformations(
                mutated=dict(zip(variables, variables_new)) | {op: op_new},  # type: ignore
            ),
        )
    )

    # TODO


def test_traceback_filtering_chain():
    E = BoundExpressions()
    variables = _create_letters(E, 3)
    A, B, C = variables

    E1 = E.add(A.as_operand.get(), B.as_operand.get())
    E2 = E.add(E1, A.as_operand.get())

    solver = Solver()
    out = solver.simplify(E.tg, E.g, terminal=False)

    E2_new = out.data.mutation_map.map_forward(
        E2.as_parameter_operatable.force_get()
    ).maps_to
    assert E2_new
    tb = out.data.mutation_map.get_traceback(E2_new)
    logger.info(tb.filtered())


def test_traceback_filtering_tree():
    E = BoundExpressions()
    variables = _create_letters(E, 3)
    A, B, C = variables

    E.is_subset(B.as_operand.get(), E.lit_op_range((0, 10)), assert_=True)
    E.is_subset(C.as_operand.get(), E.lit_op_range((5, 15)), assert_=True)

    E.is_subset(A.as_operand.get(), B.as_operand.get(), assert_=True)
    E.is_subset(A.as_operand.get(), C.as_operand.get(), assert_=True)

    solver = Solver()
    out = solver.simplify(E.tg, E.g, terminal=True)

    A_new = out.data.mutation_map.map_forward(A).maps_to
    assert A_new
    tb = out.data.mutation_map.get_traceback(A_new)
    logger.info(BaseLogger.rich_to_string(tb.filtered().as_rich_tree()))

    # A{⊆|([5, 10])} <-
    #  CONSTRAINED[Transitive subset]  <- A{⊆|([0, ∞])}
    #   MUTATED[Constrain within]  <- A
    #    MUTATED[Canonical literal]  <- A:  *46E8.A


def test_contradiction_message_subset():
    E = BoundExpressions()
    variables = _create_letters(E, 1)
    (A,) = variables

    E.is_subset(A.as_operand.get(), E.lit_op_range((6, 7)), assert_=True)
    E.is_subset(A.as_operand.get(), E.lit_op_range((4, 5)), assert_=True)

    solver = Solver()

    with pytest.raises(ContradictionByLiteral, match="Empty superset"):
        solver.simplify(E.tg, E.g, terminal=True)


@pytest.mark.skip(reason="to_fix")  # FIXME
def test_contradiction_message_superset():
    E = BoundExpressions()
    variables = _create_letters(E, 1)
    (A,) = variables

    E.is_superset(A.as_operand.get(), E.lit_op_range((0, 10)), assert_=True)
    E.is_subset(A.as_operand.get(), E.lit_op_range((4, 5)), assert_=True)

    solver = Solver()

    with pytest.raises(ContradictionByLiteral, match=r"P!\{⊆\|False\}"):
        solver.simplify(E.tg, E.g, terminal=True)


def test_name_preserved_through_bootstrap_copy():
    """Composition-based parameter names (no has_name_override) are preserved
    when parameters are copied through the bootstrap relevance-set path.
    """
    E = BoundExpressions()

    _domain = F.NumberDomain.Args(negative=True)

    class _App(fabll.Node):
        voltage = F.Parameters.NumericParameter.MakeChild(unit=E.U.dl, domain=_domain)
        current = F.Parameters.NumericParameter.MakeChild(unit=E.U.dl, domain=_domain)

    app = _App.bind_typegraph(tg=E.tg).create_instance(g=E.g)
    v_po = app.voltage.get().is_parameter_operatable.get()
    i_po = app.current.get().is_parameter_operatable.get()

    # Precondition: names come from composition, not has_name_override
    assert not fabll.Traits(v_po).get_obj_raw().has_trait(F.has_name_override)
    assert fabll.Traits(v_po).get_obj_raw().get_name() == "voltage"
    assert fabll.Traits(i_po).get_obj_raw().get_name() == "current"

    # Add a constraint so there's a predicate for the relevance set
    v_op = v_po.as_operand.get()
    E.is_subset(v_op, E.lit_op_range((1, 5)), assert_=True)

    mutation_map = MutationMap._with_relevance_set(
        g=E.g, tg=E.tg, relevant=[v_po.as_operand.get()]
    )

    fwd = mutation_map.map_forward(v_po)
    assert fwd.maps_to is not None
    new_p = fwd.maps_to.as_parameter.force_get()
    actual_name = fabll.Traits(new_p).get_obj_raw().get_name()
    assert actual_name == "voltage", f"Expected name 'voltage' but got '{actual_name}'"


def test_name_preserved_through_mutate_parameter():
    """Composition-based parameter names are preserved through mutate_parameter."""
    E = BoundExpressions()

    class _App(fabll.Node):
        resistance = F.Parameters.NumericParameter.MakeChild(
            unit=E.U.dl, domain=F.NumberDomain.Args(negative=True)
        )

    app = _App.bind_typegraph(tg=E.tg).create_instance(g=E.g)
    r_po = app.resistance.get().is_parameter_operatable.get()

    # Precondition: name from composition only
    assert not fabll.Traits(r_po).get_obj_raw().has_trait(F.has_name_override)
    assert fabll.Traits(r_po).get_obj_raw().get_name() == "resistance"

    results: dict[str, str] = {}

    @algorithm("test")
    def algo(mutator: Mutator):
        r_p = r_po.as_parameter.force_get()
        new_r = mutator.mutate_parameter(r_p)
        new_obj = fabll.Traits(new_r).get_obj_raw()
        results["resistance"] = new_obj.get_name()

    Mutator(
        MutationMap._identity(E.tg, E.g), algo=algo, iteration=0, terminal=False
    ).run()

    assert results["resistance"] == "resistance", (
        f"Expected 'resistance' but got '{results['resistance']}'"
    )


def test_compact_repr_relevance_indicators():
    """Test that compact_repr shows ★ for is_relevant and ⊘ for is_irrelevant."""
    E = BoundExpressions()
    variables = _create_letters(E, 3)
    p_normal, p_relevant, p_irrelevant = variables

    # Mark p_relevant as relevant
    fabll.Traits.create_and_add_instance_to(
        fabll.Traits(p_relevant).get_obj_raw(), is_relevant
    )

    # Mark p_irrelevant as irrelevant
    fabll.Traits.create_and_add_instance_to(
        fabll.Traits(p_irrelevant).get_obj_raw(), is_irrelevant
    )

    # Check compact_repr output
    normal_repr = p_normal.compact_repr()
    relevant_repr = p_relevant.compact_repr()
    irrelevant_repr = p_irrelevant.compact_repr()

    # Normal should have neither indicator
    assert "★" not in normal_repr, f"Normal param should not have ★: {normal_repr}"
    assert "⊘" not in normal_repr, f"Normal param should not have ⊘: {normal_repr}"

    # Relevant should have ★ but not ⊘
    assert "★" in relevant_repr, f"Relevant param should have ★: {relevant_repr}"
    assert "⊘" not in relevant_repr, (
        f"Relevant param should not have ⊘: {relevant_repr}"
    )

    # Irrelevant should have ⊘ but not ★
    assert "⊘" in irrelevant_repr, f"Irrelevant param should have ⊘: {irrelevant_repr}"
    assert "★" not in irrelevant_repr, (
        f"Irrelevant param should not have ★: {irrelevant_repr}"
    )


if __name__ == "__main__":
    test_mutation_map_non_copy_mutated_mutate_expression()
