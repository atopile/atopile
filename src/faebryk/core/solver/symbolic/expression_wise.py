# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
from collections import Counter, defaultdict
from typing import Callable

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.algorithm import SolverAlgorithm, algorithm
from faebryk.core.solver.mutator import Mutator
from faebryk.core.solver.symbolic.invariants import AliasClass
from faebryk.core.solver.utils import (
    MutatorUtils,
)
from faebryk.libs.util import not_none, partition_as_list

logger = logging.getLogger(__name__)

# TODO prettify
# - e.g rename from fold


# Boilerplate ==========================================================================

MERGED = True

fold_algorithms: list[SolverAlgorithm] = []
expr_wise_algos: dict[
    type[fabll.NodeT],
    Callable[[fabll.NodeT, Mutator], None],
] = {}


def fold_expression_type[T: fabll.NodeT](
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
    exprs = mutator.get_typed_expressions(expr_type)
    for expr in exprs:
        if mutator.utils.is_pure_literal_expression(
            expr.get_trait(F.Parameters.can_be_operand)
        ):
            continue
        f(expr, mutator)


@algorithm("Expression-wise", terminal=False)
def expression_wise(mutator: Mutator):
    for expr_type, algo in expr_wise_algos.items():
        fold_expression_type(mutator, expr_type, algo)


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
                fold_expression_type(mutator, expr_type, func)

            fold_algorithms.append(wrapped)
            return wrapped

    return wrap


# Arithmetic ---------------------------------------------------------------------------


def _collect_factors[T: F.Expressions.Multiply | F.Expressions.Power](
    mutator: Mutator,
    counter: Counter[F.Parameters.is_parameter_operatable],
    collect_type: type[T],
) -> tuple[
    dict[F.Parameters.is_parameter_operatable, F.Literals.Numbers],
    list[F.Parameters.is_parameter_operatable],
]:
    # Convert the counter to a dict for easy manipulation
    factors: dict[
        F.Parameters.is_parameter_operatable,
        F.Literals.Numbers,
    ] = {op: mutator.make_singleton(count) for op, count in counter.items()}
    # Store operations of type collect_type grouped by their non-literal operand
    same_literal_factors: dict[
        F.Parameters.is_parameter_operatable,
        list[F.Parameters.is_parameter_operatable],
    ] = defaultdict(list)

    # Look for operations matching collect_type and gather them
    for collect_op in set(factors.keys()):
        if not collect_op.get_obj().isinstance(collect_type):
            continue
        expr = collect_op.as_expression.force_get()
        # Skip if operation doesn't have exactly two operands
        # TODO unnecessary strict
        if len(expr.get_operands()) != 2:
            continue
        # handled by lit fold first
        if len(expr.get_operand_literals()) > 1:
            continue
        if not expr.get_operand_literals():
            continue
        # handled by lit fold completely
        if MutatorUtils.is_pure_literal_expression(collect_op.as_operand.get()):
            continue
        if not F.Expressions.is_commutative.is_commutative_type(
            collect_type.bind_typegraph(mutator.tg_in).get_or_create_type()
        ):
            if collect_type is not F.Expressions.Power:
                raise NotImplementedError(
                    f"Non-commutative {collect_type.__name__} not implemented"
                )
            # For power, ensure second operand is literal
            if not MutatorUtils.is_literal(expr.get_operands()[1]):
                continue

        # pick non-literal operand
        paramop = next(iter(expr.get_operand_operatables()))
        # Collect these factors under the non-literal operand
        same_literal_factors[paramop].append(collect_op)
        # If this operand isn't in factors yet, initialize it with 0
        if paramop not in factors:
            factors[paramop] = mutator.make_singleton(0)
        # Remove this operation from the main factors
        del factors[collect_op]

    # new_factors: combined literal counts, old_factors: leftover items
    new_factors: dict[F.Parameters.is_parameter_operatable, F.Literals.Numbers] = {}
    old_factors = list[F.Parameters.is_parameter_operatable]()

    # Combine literals for each non-literal operand
    for var, count in factors.items():
        muls = same_literal_factors[var]
        # If no effective multiplier or only a single factor, treat as leftover
        if count.try_get_single() == 0 and len(muls) <= 1:
            old_factors.extend(muls)
            continue

        # If only count=1 and no additional factors, just keep the variable
        if count.try_get_single() == 1 and not muls:
            old_factors.append(var)
            continue

        # Extract literal parts from collected operations
        mul_lits = [
            next(
                fabll.Traits(o_lit).get_obj(F.Literals.Numbers)
                for o_lit in mul.as_expression.force_get()
                .get_operand_literals()
                .values()
            )
            for mul in muls
        ]

        # Sum all literal multipliers plus the leftover count
        new_factors[var] = count.op_add_intervals(*mul_lits)

    return new_factors, old_factors


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

    nonlit_ops = Counter(p_operands)
    literal_sum = mutator.utils.fold_op(
        literal_operands,
        lambda a, b: a.op_add_intervals(b, g=mutator.G_transient, tg=mutator.tg_out),
        F.Literals.Numbers,
        0,
    )

    new_factors, old_factors = _collect_factors(
        mutator, nonlit_ops, F.Expressions.Multiply
    )

    # if non-lit factors all 1 and no literal folding, nothing to do
    if not new_factors and len(literal_operands) <= 1:
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
        *([literal_sum.as_operand.get()] if literal_sum else []),
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
    # TODO
    return

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

    new_powers, old_powers = _collect_factors(
        mutator, replacable_nonliteral_operands, F.Expressions.Power
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


# @expression_wise_algorithm(F.Expressions.Power)
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
    # A^1 -> A
    if (
        exp := expr.is_expression.get().get_operand_literals().get(1)
    ) and exp.op_setic_equals_singleton(1):
        mutator.utils.mutate_unpack_expression(expr.is_expression.get())

    # TODO if (litex0)^negative -> new predicate


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
    operatables = e.get_operand_operatables()

    # ¬!(¬A v ¬B v C) -> ¬!(¬!A v ¬!B v C), ¬!C
    if (
        (superset := AliasClass.of(expr.can_be_operand.get()).try_get_superset())
        and superset.op_setic_equals_singleton(False)
        and operatables
    ):
        for op in operatables:
            mutator.create_check_and_insert_expression(
                F.Expressions.IsSubset,
                op.as_operand.get(),
                mutator.make_singleton(False).can_be_operand.get(),
                # TODO terminate or not?
                terminate=True,
                assert_=True,
            )
