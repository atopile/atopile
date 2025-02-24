# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
from collections import Counter, defaultdict
from collections.abc import Sequence
from typing import Callable, cast

from faebryk.core.parameter import (
    Abs,
    Add,
    CanonicalExpressionR,
    Commutative,
    ConstrainableExpression,
    Differentiate,
    GreaterOrEqual,
    GreaterThan,
    Integrate,
    Intersection,
    Is,
    IsSubset,
    Log,
    Multiply,
    Not,
    Or,
    ParameterOperatable,
    Power,
    Round,
    Sin,
    SymmetricDifference,
    Union,
)
from faebryk.core.solver.mutator import Mutator
from faebryk.core.solver.utils import (
    CanonicalExpression,
    CanonicalNumber,
    Contradiction,
    SolverLiteral,
    algorithm,
    alias_is_literal,
    alias_is_literal_and_check_predicate_eval,
    is_literal,
    is_numeric_literal,
    is_pure_literal_expression,
    make_lit,
    subset_to,
)
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval,
)
from faebryk.libs.sets.sets import BoolSet
from faebryk.libs.util import cast_assert, partition

logger = logging.getLogger(__name__)

# TODO prettify

Literal = SolverLiteral

# Helpers ==============================================================================


def _fold_op(
    operands: Sequence[Literal],
    operator: Callable[[Literal, Literal], Literal],
    identity: Literal,
):
    """
    Return 'sum' of all literals in the iterable, or empty list if sum is identity.
    """
    if not operands:
        return []

    literal_it = iter(operands)
    const_sum = next(literal_it)
    for c in literal_it:
        const_sum = operator(const_sum, c)

    # TODO make work with all the types
    if const_sum == identity:
        return []

    return [const_sum]


def _collect_factors[T: Multiply | Power](
    counter: Counter[ParameterOperatable], collect_type: type[T]
):
    # Convert the counter to a dict for easy manipulation
    factors: dict[ParameterOperatable, ParameterOperatable.NumberLiteral] = dict(
        counter.items()
    )
    # Store operations of type collect_type grouped by their non-literal operand
    same_literal_factors: dict[ParameterOperatable, list[T]] = defaultdict(list)

    # Look for operations matching collect_type and gather them
    for collect_op in set(factors.keys()):
        if not isinstance(collect_op, collect_type):
            continue
        # Skip if operation doesn't have exactly two operands
        # TODO unnecessary strict
        if len(collect_op.operands) != 2:
            continue
        # handled by lit fold first
        if len(collect_op.get_literal_operands()) > 1:
            continue
        if not collect_op.get_literal_operands():
            continue
        # handled by lit fold completely
        if is_pure_literal_expression(collect_op):
            continue
        if not issubclass(collect_type, Commutative):
            if not issubclass(collect_type, Power):
                raise NotImplementedError(
                    f"Non-commutative {collect_type.__name__} not implemented"
                )
            # For power, ensure second operand is literal
            if not is_literal(collect_op.operands[1]):
                continue

        # pick non-literal operand
        paramop = next(iter(collect_op.operatable_operands))
        # Collect these factors under the non-literal operand
        same_literal_factors[paramop].append(collect_op)
        # If this operand isn't in factors yet, initialize it with 0
        if paramop not in factors:
            factors[paramop] = make_lit(0)
        # Remove this operation from the main factors
        del factors[collect_op]

    # new_factors: combined literal counts, old_factors: leftover items
    new_factors = {}
    old_factors = []

    # Combine literals for each non-literal operand
    for var, count in factors.items():
        muls = same_literal_factors[var]
        # If no effective multiplier or only a single factor, treat as leftover
        if count == 0 and len(muls) <= 1:
            old_factors.extend(muls)
            continue

        # If only count=1 and no additional factors, just keep the variable
        if count == 1 and not muls:
            old_factors.append(var)
            continue

        # Extract literal parts from collected operations
        mul_lits = [
            next(o for o in mul.operands if ParameterOperatable.is_literal(o))
            for mul in muls
        ]

        # Sum all literal multipliers plus the leftover count
        new_factors[var] = sum(mul_lits) + make_lit(count)  # type: ignore

    return new_factors, old_factors


# Arithmetic ---------------------------------------------------------------------------


def fold_add(
    expr: Add,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
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

    literal_sum = _fold_op(literal_operands, lambda a, b: a + b, 0)  # type: ignore #TODO

    new_factors, old_factors = _collect_factors(
        replacable_nonliteral_operands, Multiply
    )

    # if non-lit factors all 1 and no literal folding, nothing to do
    if not new_factors and len(literal_sum) == len(literal_operands):
        return

    # Careful, modifying old graph, but should be ok
    factored_operands = [
        mutator.create_expression(Multiply, n, m, from_ops=[expr])
        for n, m in new_factors.items()
    ]

    new_operands = [
        *factored_operands,
        *old_factors,
        *literal_sum,
        *non_replacable_nonliteral_operands,
    ]

    if new_operands == expr.operands:
        return

    # unpack if single operand (operatable)
    if len(new_operands) == 1 and isinstance(new_operands[0], ParameterOperatable):
        new_operands = cast(list[ParameterOperatable], new_operands)
        mutator.mutate_unpack_expression(expr, new_operands)
        return

    new_expr = mutator.mutate_expression(
        expr, operands=new_operands, expression_factory=Add
    )
    # if only one literal operand, equal to it
    if len(new_operands) == 1:
        alias_is_literal(new_expr, new_operands[0], mutator, terminate=True)


def fold_multiply(
    expr: Multiply,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    literal_prod = _fold_op(literal_operands, lambda a, b: a * b, 1)  # type: ignore #TODO

    new_powers, old_powers = _collect_factors(replacable_nonliteral_operands, Power)

    # if non-lit powers all 1 and no literal folding, nothing to do
    if (
        not new_powers
        and len(literal_prod) == len(literal_operands)
        and not (
            literal_prod
            and literal_prod[0] == 0
            and len(replacable_nonliteral_operands)
            + len(non_replacable_nonliteral_operands)
            > 0
        )
    ):
        return

    # Careful, modifying old graph, but should be ok
    powered_operands = [
        mutator.create_expression(Power, n, m, from_ops=[expr])
        for n, m in new_powers.items()
    ]

    new_operands = [
        *powered_operands,
        *old_powers,
        *literal_prod,
        *non_replacable_nonliteral_operands,
    ]

    # 0 * A -> 0
    if 0 in new_operands:
        new_operands = [make_lit(0)]
        # convert_operable_aliased_to_single_into_literal takes care of rest

    # unpack if single operand (operatable)
    if len(new_operands) == 1 and isinstance(new_operands[0], ParameterOperatable):
        new_operands = cast(list[ParameterOperatable], new_operands)
        mutator.mutate_unpack_expression(expr, new_operands)
        return

    new_expr = mutator.mutate_expression(
        expr, operands=new_operands, expression_factory=Multiply
    )

    # if only one literal operand, equal to it
    if len(new_operands) == 1:
        alias_is_literal(new_expr, new_operands[0], mutator, terminate=True)


def fold_pow(
    expr: Power,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
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

    # TODO if (litex0)^negative -> new constraint

    base, exp = expr.operands

    # All literals
    if is_numeric_literal(base) and is_numeric_literal(exp):
        try:
            result = base**exp
        except NotImplementedError:
            # TODO either fix or raise a warning
            return
        alias_is_literal(expr, result, mutator, terminate=True)
        return

    if is_numeric_literal(exp):
        if exp == 1:
            mutator.mutate_unpack_expression(expr)
            return

        # in python 0**0 is also 1
        if exp == 0:
            alias_is_literal(expr, 1, mutator, terminate=True)
            return

    if is_numeric_literal(base):
        if base == 0:
            alias_is_literal(expr, 0, mutator, terminate=True)
            # FIXME: exp >! 0
            return
        if base == 1:
            alias_is_literal(expr, 1, mutator, terminate=True)
            return


def fold_log(
    expr: Log,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    """
    # TODO log(A*B) -> log(A) + log(B)
    # TODO log(A^B) -> B*log(A)
    """
    return


def fold_abs(
    expr: Abs,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    """
    # TODO |-A| = |A|
    # TODO |A*B| = |A|*|B|
    # TODO |A+B| <= |A|+|B|
    """
    return


def fold_round(
    expr: Round,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    """
    TODO: Think about round(A + X)
    """
    return


def fold_sin(
    expr: Sin,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    """
    Sin ss! [-1, 1]
    #TODO Sin(-A) -> -Sin(A)
    #TODO Sin(A + 2*pi) -> Sin(A)
    #TODO Sin(A+B) -> Sin(A)*Cos(B) + Cos(A)*Sin(B)
    """
    subset_to(expr, make_lit(Quantity_Interval(-1, 1)), mutator, from_ops=[expr])


# Setic --------------------------------------------------------------------------------


def fold_intersect(
    expr: Intersection,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    """
    Intersection(A) -> A (implicit)
    """

    return


def fold_union(
    expr: Union,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    """
    Union(A) -> A (implicit)
    """

    return


# Constrainable ------------------------------------------------------------------------


def fold_or(
    expr: Or,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    """
    ```
    Or(A, B, C, True) -> True
    Or(A, B, C, False) -> Or(A, B, C)
    Or(A, B, C, P) | P constrained -> True
    Or(A, B, A) -> Or(A, B)
    Or() -> False
    ```
    """

    # Or(P) -> P implicit (unary identity unpack)
    # Or!(P) -> P! implicit (unary identity unpack)
    # Or(A, B, A) -> Or(A, B) implicit (idempotent)

    # Or(A, B, C, True) -> True
    if BoolSet(True) in literal_operands:
        alias_is_literal_and_check_predicate_eval(expr, True, mutator)
        return

    # Or(A, B, C, False) -> Or(A, B, C)
    filtered_operands = [op for op in expr.operands if BoolSet(False) != op]
    if len(filtered_operands) != len(expr.operands):
        # Rebuild without False literals
        mutator.mutate_expression(expr, operands=filtered_operands)
        return


def fold_not(
    expr: Not,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    """
    ```
    ¬(¬A) -> A
    ¬True -> False
    ¬False -> True
    ¬P | P constrained -> False

    ¬!(¬A v ¬B v C) -> ¬!(¬!A v ¬!B v C), ¬!C
    ¬!A -> A is! False
    ```
    """
    # TODO ¬(A >= B) -> (B > A) ss ¬(A >= B) (only ss because of partial overlap)

    # ¬(¬A) -> A implicit
    # ¬!(¬A) -> !A implicit

    assert len(expr.operands) == 1
    op = expr.operands[0]
    assert isinstance(op, ParameterOperatable)

    # ¬P | P constrained -> False
    if isinstance(op, ConstrainableExpression) and op.constrained:
        # ¬!P! | P constrained -> Contradiction
        if expr.constrained:
            raise Contradiction("¬!P!", involved=[expr])
        alias_is_literal(expr, False, mutator)
        return

    if replacable_nonliteral_operands:
        # TODO this is kinda ugly, should be in Or fold if it aliases to false
        # ¬!(¬A v ¬B v C) -> ¬!(¬!A v ¬!B v C), ¬!C
        if expr.constrained:
            # ¬( v )
            if isinstance(op, Or):
                # FIXME remove this shortcut
                # should be handle in more general way
                # maybe we need to terminate non-predicates too
                if not op.operands:
                    alias_is_literal_and_check_predicate_eval(expr, True, mutator)
                for inner_op in op.operands:
                    # ¬(¬A v ...)
                    if isinstance(inner_op, Not):
                        for not_op in inner_op.operands:
                            if (
                                isinstance(not_op, ConstrainableExpression)
                                and not not_op.constrained
                            ):
                                mutator.constrain(
                                    cast_assert(
                                        ConstrainableExpression,
                                        mutator.get_copy(not_op),
                                    )
                                )
                    # ¬(A v ...)
                    elif isinstance(inner_op, ConstrainableExpression):
                        parent_nots = inner_op.get_operations(Not)
                        if parent_nots:
                            for n in parent_nots:
                                mutator.constrain(n)
                        else:
                            mutator.create_expression(
                                Not, inner_op, from_ops=[expr], constrain=True
                            )

    if expr.constrained:
        alias_is_literal_and_check_predicate_eval(op, False, mutator)


def fold_is(
    expr: Is,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    """
    ```
    P is! True -> P!
    ```
    """

    is_true_alias = expr.constrained and BoolSet(True) in literal_operands
    if is_true_alias:
        # P1 is! True -> P1!
        # P1 is! P2!  -> P1! (implicit)
        for p in expr.get_operatable_operands(ConstrainableExpression):
            mutator.constrain(p)


def fold_subset(
    expr: IsSubset,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    """
    ```
    A is B, A ss B | B non(ex)literal -> repr(B, A)
    A ss ([X]) -> A is ([X])
    A ss {} -> A is {}
    # predicates
    P ss! True -> P!
    P ss! False -> ¬!P
    P1 ss! P2! -> P1!
    # literals
    X ss Y -> True / False

    A ss! B, B ss!/is! C -> A ss! C in transitive_subset
    ```
    """

    A, B = expr.operands

    if not is_literal(B):
        return

    # A ss ([X]) -> A is ([X])
    # A ss {} -> A is {}
    if B.is_single_element() or B.is_empty():
        mutator.mutate_expression(expr, expression_factory=Is)
        return

    if expr.constrained:
        # P1 ss! True -> P1!
        # P1 ss! P2!  -> P1!
        if (
            B == BoolSet(True)
            or isinstance(B, ConstrainableExpression)
            and B.constrained
        ):
            assert isinstance(A, ConstrainableExpression)
            mutator.constrain(A)
        # P ss! False -> ¬!P
        if B == BoolSet(False):
            assert isinstance(A, ConstrainableExpression)
            mutator.create_expression(Not, A, from_ops=[expr], constrain=True)


def fold_ge(
    expr: GreaterOrEqual,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
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
    left, right = expr.operands
    literal_operands = cast(Sequence[CanonicalNumber], literal_operands)

    # A >=! X | |X| > 1 -> A >=! X.max()
    # X >=! A | |X| > 1 -> X.min() >=! A
    if literal_operands and expr.constrained:
        assert len(literal_operands) == 1
        lit = literal_operands[0]
        if not lit.is_single_element() and not lit.is_empty():
            if left is lit:
                mutator.mutate_expression(
                    expr, operands=[make_lit(lit.min_elem), right]
                )
            else:
                assert right is lit
                mutator.mutate_expression(expr, operands=[left, make_lit(lit.max_elem)])
        return


# Boilerplate ==========================================================================


def fold(
    expr: CanonicalExpression,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
) -> None:
    """
    literal_operands must be actual literals, not the literal the operand is aliased to!
    maybe it would be fine for set literals with one element?
    """

    def get_func[T: CanonicalExpression](
        expr: T,
    ) -> Callable[
        [
            T,
            Sequence[Literal],
            Counter[ParameterOperatable],
            Sequence[ParameterOperatable],
            Mutator,
        ],
        None,
    ]:
        # Arithmetic
        if isinstance(expr, Add):
            return fold_add  # type: ignore
        elif isinstance(expr, Multiply):
            return fold_multiply  # type: ignore
        elif isinstance(expr, Power):
            return fold_pow  # type: ignore
        elif isinstance(expr, Round):
            return fold_round  # type: ignore
        elif isinstance(expr, Abs):
            return fold_abs  # type: ignore
        elif isinstance(expr, Sin):
            return fold_sin  # type: ignore
        elif isinstance(expr, Log):
            return fold_log  # type: ignore
        elif isinstance(expr, Integrate):
            # TODO implement
            return lambda *args: None
        elif isinstance(expr, Differentiate):
            # TODO implement
            return lambda *args: None
        # Logic
        elif isinstance(expr, Or):
            return fold_or  # type: ignore
        elif isinstance(expr, Not):
            return fold_not  # type: ignore
        # Equality / Inequality
        elif isinstance(expr, Is):
            return fold_is  # type: ignore
        elif isinstance(expr, GreaterOrEqual):
            return fold_ge  # type: ignore
        elif isinstance(expr, GreaterThan):
            # TODO implement
            return lambda *args: None
        elif isinstance(expr, IsSubset):
            return fold_subset  # type: ignore
        # Sets
        elif isinstance(expr, Intersection):
            return fold_intersect  # type: ignore
        elif isinstance(expr, Union):
            return fold_union  # type: ignore
        elif isinstance(expr, SymmetricDifference):
            # TODO implement
            return lambda *args: None

        raise ValueError(f"unsupported operation: {expr}")

    get_func(expr)(
        expr,
        literal_operands,
        replacable_nonliteral_operands,
        non_replacable_nonliteral_operands,
        mutator,
    )


def fold_literals(mutator: Mutator, expr_type: type[CanonicalExpression]):
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

    exprs = mutator.nodes_of_type(expr_type, sort_by_depth=True)
    for expr in exprs:
        if mutator.has_been_mutated(expr) or mutator.is_removed(expr):
            continue

        # covered by pure literal folding
        if is_pure_literal_expression(expr):
            continue

        operands = expr.operands
        p_operands, literal_operands = partition(
            lambda o: ParameterOperatable.is_literal(o), operands
        )
        p_operands = cast(list[ParameterOperatable], p_operands)
        non_replacable_nonliteral_operands, replacable_nonliteral_operands = partition(
            lambda o: not mutator.has_been_mutated(o), p_operands
        )
        multiplicity = Counter(replacable_nonliteral_operands)

        fold(
            expr,
            literal_operands=list(literal_operands),
            replacable_nonliteral_operands=multiplicity,
            non_replacable_nonliteral_operands=list(non_replacable_nonliteral_operands),
            mutator=mutator,
        )


def _get_fold_func(expr_type: type[CanonicalExpression]) -> Callable[[Mutator], None]:
    def wrapped(mutator: Mutator):
        fold_literals(mutator, expr_type)

    wrapped.__name__ = f"_fold_{expr_type.__name__}"

    return wrapped


fold_algorithms = [
    algorithm(f"Fold {expr_type.__name__}", terminal=False)(_get_fold_func(expr_type))
    for expr_type in CanonicalExpressionR
]
