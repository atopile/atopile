# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
from collections import Counter
from typing import Callable

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.algorithm import SolverAlgorithm, algorithm
from faebryk.core.solver.mutator import Mutator
from faebryk.core.solver.utils import (
    Contradiction,
)
from faebryk.libs.util import not_none, partition_as_list

logger = logging.getLogger(__name__)

# TODO prettify
# - e.g rename from fold


# Boilerplate ==========================================================================

MERGED = False

fold_algorithms: list[SolverAlgorithm] = []
expr_wise_algos: dict[
    type[fabll.NodeT],
    Callable[[fabll.NodeT, Mutator], None],
] = {}


def fold_literals[T: fabll.NodeT](
    mutator: Mutator, expr_type: type[T], f: Callable[[T, Mutator], None]
):
    """
    Tries to do operations on literals or fold expressions.
    - If possible to do literal operation, aliases expr with result.
    - If fold results in new expr, replaces old expr with new one.
    - If fold results in neutralization, returns operand if not literal else alias.

    Examples:
    ```
    Or(True, B) -> alias: True
    Add(A, B, 5, 10) -> replace: Add(A, B, 15)
    Add(10, 15) -> alias: 25
    Not(Not(A)) -> neutralize=replace: A
    ```
    """
    exprs = mutator.get_typed_expressions(expr_type, sort_by_depth=True, new_only=False)
    for expr in exprs:
        if mutator.has_been_mutated(
            expr.get_trait(F.Parameters.is_parameter_operatable)
        ) or mutator.is_removed(expr.get_trait(F.Parameters.is_parameter_operatable)):
            continue

        # covered by pure literal folding
        if mutator.utils.is_pure_literal_expression(
            expr.get_trait(F.Parameters.can_be_operand)
        ):
            continue

        f(expr, mutator)


@algorithm("Expression-wise", terminal=False)
def expression_wise(mutator: Mutator):
    for expr_type, algo in expr_wise_algos.items():
        exprs = mutator.get_typed_expressions(
            expr_type, sort_by_depth=True, new_only=False
        )
        for expr in exprs:
            if mutator.has_been_mutated(
                expr.get_trait(F.Parameters.is_parameter_operatable)
            ) or mutator.is_removed(
                expr.get_trait(F.Parameters.is_parameter_operatable)
            ):
                continue

            # covered by pure literal folding
            if mutator.utils.is_pure_literal_expression(
                expr.get_trait(F.Parameters.can_be_operand)
            ):
                continue
            algo(expr, mutator)  # type: ignore


def expression_wise_algorithm[T: fabll.NodeT](expr_type: type[T]):
    def wrap(func: Callable[[T, Mutator], None]) -> SolverAlgorithm:
        if MERGED:
            expr_wise_algos[expr_type] = func  # type: ignore
            if expression_wise not in fold_algorithms:
                fold_algorithms.append(expression_wise)
            return expression_wise
        else:

            @algorithm(f"Fold {expr_type.__name__}", terminal=False)
            def wrapped(mutator: Mutator):
                fold_literals(mutator, expr_type, func)

            fold_algorithms.append(wrapped)
            return wrapped

    return wrap


# TODO REMOVE JUST A TEST
@algorithm("NOOOP")
def noop(mutator: Mutator):
    pass


fold_algorithms.append(noop)


# Arithmetic ---------------------------------------------------------------------------


@expression_wise_algorithm(F.Expressions.Add)
def fold_add(expr: F.Expressions.Add, mutator: Mutator):
    """
    A + A + 5 + 10 -> 2*A + 15
    A + 5 + (-5) -> A
    A + (-A) + 5 -> Add(5)
    A + (3 * A) + 5 -> (4 * A) + 5
    A + (A * B * 2) -> A + (A * B * 2)
    #TODO think about -> A * (1 + B * 2) (factorization), not in here tho
    A + (B * 2) -> A + (B * 2)
    A + (A * 2) + (A * 3) -> (6 * A)
    A + (A * 2) + ((A *2 ) * 3) -> (3 * A) + (3 * (A * 2))
    #TODO recheck double match (of last case)
    """

    # A + X, B + X, X = A * 5
    # 6*A
    # (A * 2) + (A * 5)
    e = expr.is_expression.get()
    literal_operands = list(e.get_operand_literals().values())
    p_operands = e.get_operand_operatables()
    non_replacable_nonliteral_operands, _replacable_nonliteral_operands = (
        partition_as_list(
            lambda o: not mutator.has_been_mutated(o),
            p_operands,
        )
    )
    replacable_nonliteral_operands = Counter(_replacable_nonliteral_operands)
    literal_sum = mutator.utils.fold_op(
        literal_operands,
        lambda a, b: a.op_add_intervals(b, g=mutator.G_transient, tg=mutator.tg_out),
        F.Literals.Numbers,
        0,
    )

    new_factors, old_factors = mutator.utils.collect_factors(
        replacable_nonliteral_operands,
        F.Expressions.Multiply,
    )

    # if non-lit factors all 1 and no literal folding, nothing to do
    if not new_factors and len(literal_sum) == len(literal_operands):
        return

    factored_operands = [
        not_none(
            mutator.create_check_and_insert_expression(
                F.Expressions.Multiply,
                n.as_operand.get(),
                m.can_be_operand.get(),
                from_ops=[expr.is_parameter_operatable.get()],
            ).out_operand
        )
        for n, m in new_factors.items()
    ]

    new_operands: list[F.Parameters.can_be_operand] = [
        *factored_operands,
        *(x.as_operand.get() for x in old_factors),
        *(x.as_operand.get() for x in literal_sum),
        *(x.as_operand.get() for x in non_replacable_nonliteral_operands),
    ]

    if new_operands == expr.is_expression.get().get_operands():
        return

    # unpack if single operand (operatable)
    if len(new_operands) == 1 and (
        no_po := new_operands[0].as_parameter_operatable.try_get()
    ):
        mutator.utils.mutate_unpack_expression(e, [no_po])
        return

    mutator.mutate_expression(
        e, operands=new_operands, expression_factory=F.Expressions.Add
    )


@expression_wise_algorithm(F.Expressions.Multiply)
def fold_multiply(expr: F.Expressions.Multiply, mutator: Mutator):
    """
    TODO doc other simplifications
    A * (A + B)^-1 -> 1 + (B * A^-1)^-1
    """

    e = expr.is_expression.get()
    e_po = e.as_parameter_operatable.get()
    literal_operands = list(e.get_operand_literals().values())
    p_operands = e.get_operand_operatables()

    non_replacable_nonliteral_operands, _replacable_nonliteral_operands = (
        partition_as_list(lambda o: not mutator.has_been_mutated(o), p_operands)
    )
    replacable_nonliteral_operands = Counter(_replacable_nonliteral_operands)

    literal_prod = mutator.utils.fold_op(
        literal_operands,
        lambda a, b: a.op_mul_intervals(b, g=mutator.G_transient, tg=mutator.tg_out),
        F.Literals.Numbers,
        1,
    )

    new_powers, old_powers = mutator.utils.collect_factors(
        replacable_nonliteral_operands, F.Expressions.Power
    )

    # if non-lit powers all 1 and no literal folding, nothing to do
    if not (
        not new_powers
        and len(literal_prod) == len(literal_operands)
        and not (
            literal_prod
            and literal_prod[0].op_setic_equals_singleton(0)
            and len(replacable_nonliteral_operands)
            + len(non_replacable_nonliteral_operands)
            > 0
        )
    ):
        # Careful, modifying old graph, but should be ok
        powered_operands = [
            pe
            for n, m in new_powers.items()
            if (
                pe := mutator.create_check_and_insert_expression(
                    F.Expressions.Power,
                    n.as_operand.get(),
                    m.can_be_operand.get(),
                    from_ops=[e_po],
                ).out_operand
            )
        ]

        new_operands: list[F.Parameters.can_be_operand] = [
            *powered_operands,
            *(x.as_operand.get() for x in old_powers),
            *(x.as_operand.get() for x in literal_prod),
            *(x.as_operand.get() for x in non_replacable_nonliteral_operands),
        ]

        # 0 * A -> 0
        if any(
            x_lit.op_setic_equals_singleton(0)
            for x in new_operands
            if (x_lit := mutator.utils.is_literal(x))
        ):
            new_operands = [mutator.make_singleton(0).can_be_operand.get()]
            # convert_operable_aliased_to_single_into_literal takes care of rest

        # unpack if single operand (operatable)
        if len(new_operands) == 1 and (
            no_po := new_operands[0].as_parameter_operatable.try_get()
        ):
            mutator.utils.mutate_unpack_expression(e, [no_po])
            return

        if new_operands != expr.operands:
            mutator.mutate_expression(
                e, operands=new_operands, expression_factory=F.Expressions.Multiply
            )

            return

    # if len(expr.operands) == 2:
    #     # TODO pos independend
    #     A, right = expr.operands
    #     # A * (A + B)^-1 -> (1 + B * A^-1)^-1
    #     if (
    #         isinstance(A, ParameterOperatable)
    #         and isinstance(right, Power)
    #         and right.get_operand_literals().get(1) == -1
    #         and isinstance(inner := right.operands[0], Add)
    #         and len(inner.operands) == 2
    #         and not inner.get_operand_literals()
    #         and A in inner.operands
    #     ):
    #         B = inner.get_other_operand(A)
    #         A_inv = mutator.create_expression(
    #             Power,
    #             A,
    #             make_lit(-1),
    #             from_ops=[expr],
    #         )
    #         mutator.mutate_expression(
    #             expr,
    #             expression_factory=Power,
    #             operands=[
    #                 mutator.create_expression(
    #                     Add,
    #                     make_lit(1),
    #                     mutator.create_expression(Multiply, B, A_inv,
    #                       from_ops=[expr]),
    #                 ),
    #                 make_lit(-1),
    #             ],
    #         )


@expression_wise_algorithm(F.Expressions.Power)
def fold_pow(expr: F.Expressions.Power, mutator: Mutator):
    """
    ```
    A^0 -> 1
    A^1 -> A
    0^A -> 0
    1^A -> 1
    #TODO: (A^B)^C -> A^(B*C)
    #TODO rethink: 0^0 -> 1
    ```
    """

    # TODO if (litex0)^negative -> new predicate

    e = expr.is_expression.get()
    e_op = e.as_operand.get()
    base, exp = expr.is_expression.get().get_operands()

    if exp_lit := mutator.utils.is_literal(exp):
        if exp_lit.op_setic_equals_singleton(1):
            mutator.utils.mutate_unpack_expression(e)
            return

        # in python 0**0 is also 1
        if exp_lit.op_setic_equals_singleton(0):
            mutator.create_check_and_insert_expression(
                F.Expressions.IsSubset,
                e_op,
                mutator.make_singleton(1).can_be_operand.get(),
                terminate=True,
                assert_=True,
            )
            return
    if base_lit := mutator.utils.is_literal(base):
        if base_lit.op_setic_equals_singleton(0):
            mutator.create_check_and_insert_expression(
                F.Expressions.IsSubset,
                e_op,
                mutator.make_singleton(0).can_be_operand.get(),
                terminate=True,
                assert_=True,
            )
            # FIXME: exp >! 0
            return
        if base_lit.op_setic_equals_singleton(1):
            mutator.create_check_and_insert_expression(
                F.Expressions.IsSubset,
                e_op,
                mutator.make_singleton(1).can_be_operand.get(),
                terminate=True,
                assert_=True,
            )
            return


# @expression_wise_algorithm(Log)
def fold_log(expr: F.Expressions.Log, mutator: Mutator):
    """
    # TODO log(A*B) -> log(A) + log(B)
    # TODO log(A^B) -> B*log(A)
    """
    return


# @expression_wise_algorithm(Abs)
def fold_abs(expr: F.Expressions.Abs, mutator: Mutator):
    """
    # TODO |-A| = |A|
    # TODO |A*B| = |A|*|B|
    # TODO |A+B| <= |A|+|B|
    """
    return


# @expression_wise_algorithm(Round)
def fold_round(expr: F.Expressions.Round, mutator: Mutator):
    """
    TODO: Think about round(A + X)
    """
    return


@expression_wise_algorithm(F.Expressions.Sin)
def fold_sin(expr: F.Expressions.Sin, mutator: Mutator):
    """
    Sin ss! [-1, 1]
    #TODO Sin(-A) -> -Sin(A)
    #TODO Sin(A + 2*pi) -> Sin(A)
    #TODO Sin(A+B) -> Sin(A)*Cos(B) + Cos(A)*Sin(B)
    """
    mutator.create_check_and_insert_expression(
        F.Expressions.IsSubset,
        expr.is_expression.get().as_operand.get(),
        mutator.utils.make_number_literal_from_range(-1, 1).can_be_operand.get(),
        from_ops=[expr.is_parameter_operatable.get()],
        assert_=True,
    )


# Constrainable ------------------------------------------------------------------------


@expression_wise_algorithm(F.Expressions.Or)
def fold_or(expr: F.Expressions.Or, mutator: Mutator):
    """
    ```
    Or(A, B, C, True) -> True; if predicate then terminate
    Or(A, B, C, False) -> Or(A, B, C)
    Or(A, B, A) -> Or(A, B)
    Or() -> False
    Or(A, B, {True, False}) -> Or(A, B)
    ```
    """

    # Or(P) -> P implicit (unary identity unpack)
    # Or!(P) -> P! implicit (unary identity unpack)
    # Or(A, B, A) -> Or(A, B) implicit (idempotent)

    e = expr.is_expression.get()
    lits = e.get_operand_literals()
    if not lits:
        return

    # Or(A, B, C, True) -> True
    if any(lit.op_setic_equals_singleton(True) for lit in lits.values()):
        if e.try_get_sibling_trait(F.Expressions.is_predicate):
            return
        mutator.create_check_and_insert_expression(
            F.Expressions.IsSubset,
            e.as_operand.get(),
            mutator.make_singleton(True).can_be_operand.get(),
            terminate=True,
            assert_=True,
        )
        return

    # Or(A, B, C, False/{True, False}) -> Or(A, B, C)
    filtered_operands = [op.as_operand.get() for op in e.get_operand_operatables()]
    # Rebuild without False literals
    mutator.mutate_expression(e, operands=filtered_operands)


@expression_wise_algorithm(F.Expressions.Not)
def fold_not(expr: F.Expressions.Not, mutator: Mutator):
    """
    ```
    ¬(¬A) -> A
    ¬P | P! -> False

    ¬!(¬A v ¬B v C) -> ¬!(¬!A v ¬!B v C), ¬!C
    ¬!A -> A is! False
    ```
    """
    # TODO ¬(A >= B) -> (B > A) ss ¬(A >= B) (only ss because of partial overlap)

    # ¬(¬A) -> A implicit
    # ¬!(¬A) -> !A implicit

    e = expr.is_expression.get()
    expr_po = e.as_parameter_operatable.get()
    assert len(e.get_operands()) == 1
    op = e.get_operands()[0]
    op_po = op.as_parameter_operatable.force_get()
    assert op_po

    # ¬P! -> False
    if op.try_get_sibling_trait(F.Expressions.is_predicate):
        # ¬!P! -> Contradiction
        if expr.try_get_trait(F.Expressions.is_predicate):
            raise Contradiction(
                "¬!P!",
                involved=[op_po],
                mutator=mutator,
            )
        mutator.create_check_and_insert_expression(
            F.Expressions.IsSubset,
            e.as_operand.get(),
            mutator.make_singleton(False).can_be_operand.get(),
            terminate=True,
            assert_=True,
        )
        return

    if not mutator.has_been_mutated(op_po):
        # TODO this is kinda ugly, should be in Or fold if it aliases to false
        # ¬!(¬A v ¬B v C) -> ¬!(¬!A v ¬!B v C), ¬!C
        if pred := expr.try_get_trait(F.Expressions.is_predicate):
            # ¬!( v )
            if op_or := fabll.Traits(op).get_obj_raw().try_cast(F.Expressions.Or):
                # FIXME remove this shortcut
                # should be handle in more general way
                # maybe we need to terminate non-predicates too
                op_or_e = op_or.is_expression.get()
                # TODO this should not be needed
                # ¬!Or() -> True
                if not op_or_e.get_operands():
                    mutator.create_check_and_insert_expression(
                        F.Expressions.IsSubset,
                        e.as_operand.get(),
                        mutator.make_singleton(True).can_be_operand.get(),
                        terminate=True,
                        assert_=True,
                    )
                    mutator.predicate_terminate(pred)

                for inner_op_e in op_or_e.get_operands_with_trait(
                    F.Expressions.is_expression
                ):
                    # ¬!(¬A v ...)
                    if inner_op_e.try_cast(F.Expressions.Not):
                        for not_op in inner_op_e.get_operands():
                            if (
                                (not_op_po := not_op.as_parameter_operatable.try_get())
                                and (not_op_expr := not_op_po.as_expression.try_get())
                                and (not_op_expr.as_assertable.try_get())
                                and not not_op.try_get_sibling_trait(
                                    F.Expressions.is_predicate
                                )
                            ):
                                copy = mutator.get_copy(not_op)
                                if copy:
                                    mutator.assert_(
                                        copy.as_parameter_operatable.force_get()
                                        .as_expression.force_get()
                                        .as_assertable.force_get()
                                    )

                    # ¬!(A v ...)
                    elif inner_op_e.as_assertable.try_get():
                        inner_op_po = inner_op_e.as_parameter_operatable.get()
                        parent_nots = inner_op_po.get_operations(F.Expressions.Not)
                        if parent_nots:
                            for n in parent_nots:
                                mutator.assert_(n.is_assertable.get())
                        else:
                            mutator.create_check_and_insert_expression(
                                F.Expressions.Not,
                                inner_op_e.as_operand.get(),
                                from_ops=[expr_po],
                                assert_=True,
                            )

    if (
        superset := mutator.utils.try_extract_superset(op_po)
    ) is not None and superset.op_setic_is_singleton():
        negated = superset.cast(F.Literals.Booleans).op_not(
            g=mutator.G_transient, tg=mutator.tg_in
        )
        mutator.create_check_and_insert_expression(
            F.Expressions.IsSubset,
            op,
            negated.can_be_operand.get(),
            terminate=True,
            assert_=True,
        )


@expression_wise_algorithm(F.Expressions.Is)
def fold_is(expr: F.Expressions.Is, mutator: Mutator):
    """
    ```
    P is! True -> P!
    ```
    """

    e = expr.is_expression.get()
    is_true_alias = expr.try_get_trait(F.Expressions.is_predicate) and any(
        lit.op_setic_equals_singleton(True) for lit in e.get_operand_literals().values()
    )
    if is_true_alias:
        # P1 is! True -> P1!
        # P1 is! P2!  -> P1! (implicit)
        for p in e.get_operands_with_trait(F.Expressions.is_assertable):
            mutator.assert_(p)


@expression_wise_algorithm(F.Expressions.IsSubset)
def fold_subset(expr: F.Expressions.IsSubset, mutator: Mutator):
    """
    ```
    A is B, A ss B | B non(ex)literal -> repr(B, A)
    # predicates
    P ss! True -> P!
    P ss! False -> ¬!P
    P1 ss! P2! -> P1!
    # literals
    X ss Y -> True / False

    A ss! B, B ss!/is! C -> A ss! C in transitive_subset
    ```
    """

    e = expr.is_expression.get()
    A, B = e.get_operands()

    if not (B_lit := B.as_literal.try_get()):
        return

    if e.try_get_trait(F.Expressions.is_predicate):
        # P1 ss! True -> P1!
        if B_lit.op_setic_equals_singleton(True):
            mutator.assert_(
                A.as_parameter_operatable.force_get()
                .as_expression.force_get()
                .as_assertable.force_get()
            )
        # P ss! False -> ¬!P
        if B_lit.op_setic_equals_singleton(False):
            mutator.create_check_and_insert_expression(
                F.Expressions.Not,
                A,
                from_ops=[expr.is_parameter_operatable.get()],
                assert_=True,
            )


@expression_wise_algorithm(F.Expressions.GreaterOrEqual)
def fold_ge(expr: F.Expressions.GreaterOrEqual, mutator: Mutator):
    """
    ```
    A >= A -> True
    # literals
    X >= Y -> [True] / [False] / [True, False]
    A >=! X | |X| > 1 -> A >=! X.max()
    X >=! A | |X| > 1 -> X.min() >=! A
    # uncorrelated
    A >= B{I|X} -> A >= X.max()
    B{I|X} >= A -> X.min() >= A
    ```
    """
    e = expr.is_expression.get()
    left, right = e.get_operands()
    literal_operands = e.get_operand_literals()

    # A >=! X | |X| > 1 -> A >=! X.max()
    # X >=! A | |X| > 1 -> X.min() >=! A
    if literal_operands and e.try_get_trait(F.Expressions.is_predicate):
        assert len(literal_operands) == 1
        lit = literal_operands[0]
        lit_n = fabll.Traits(lit).get_obj(F.Literals.Numbers)
        if not lit.op_setic_is_singleton() and not lit.op_setic_is_empty():
            lit_op = lit.as_operand.get()
            if left.is_same(lit_op):
                mutator.mutate_expression(
                    e,
                    operands=[
                        lit_n.min_elem(
                            g=mutator.G_transient, tg=mutator.tg_out
                        ).can_be_operand.get(),
                        right,
                    ],
                )
            else:
                assert right.is_same(lit_op)
                mutator.mutate_expression(
                    e,
                    operands=[
                        left,
                        lit_n.max_elem(
                            g=mutator.G_transient, tg=mutator.tg_out
                        ).can_be_operand.get(),
                    ],
                )
        return


# @expression_wise_algorithm(F.Expressions.GreaterThan)
def fold_gt(expr: F.Expressions.GreaterThan, mutator: Mutator):
    """ """
    return
