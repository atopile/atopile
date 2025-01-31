# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import functools
import logging
import operator
from collections import Counter, defaultdict
from collections.abc import Sequence
from typing import Callable, Iterable, cast

from faebryk.core.parameter import (
    Abs,
    Add,
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
    Predicate,
    Round,
    Sin,
    SymmetricDifference,
    Union,
)
from faebryk.core.solver.mutator import Mutator
from faebryk.core.solver.utils import (
    CanonicalNumber,
    CanonicalOperation,
    Contradiction,
    SolverLiteral,
    algorithm,
    alias_is_literal,
    alias_is_literal_and_check_predicate_eval,
    is_literal,
    is_numeric_literal,
    make_lit,
)
from faebryk.libs.sets.quantity_sets import Quantity_Interval_Disjoint
from faebryk.libs.sets.sets import BoolSet, P_Set
from faebryk.libs.util import cast_assert, partition

logger = logging.getLogger(__name__)

# TODO prettify

Literal = SolverLiteral

# Arithmetic ---------------------------------------------------------------------------


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
        # If it's commutative, skip purely literal operations and pick the non-literal
        # operand
        if issubclass(collect_type, Commutative):
            if all(ParameterOperatable.is_literal(o) for o in collect_op.operands):
                continue
            paramop = next(
                o for o in collect_op.operands if not ParameterOperatable.is_literal(o)
            )
        else:
            # For non-commutative, ensure second operand is literal
            if not ParameterOperatable.is_literal(collect_op.operands[1]):
                continue
            paramop = collect_op.operands[0]

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
    powered_operands = [Power(n, m) for n, m in new_powers.items()]

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
    5^3 -> 125
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


# Setic --------------------------------------------------------------------------------
def fold_intersect(
    expr: Intersection,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    """
    Intersection(A) -> A
    """

    # Intersection(A) -> A
    if not literal_operands and len(expr.operands) == 1:
        mutator.mutate_unpack_expression(expr)
        return


def fold_union(
    expr: Union,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    """
    Union(A) -> A
    """

    # Union(A) -> A
    if not literal_operands and len(expr.operands) == 1:
        mutator.mutate_unpack_expression(expr)
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
    Or(P) -> P
    Or!(P) -> P!
    Or() -> False
    ```
    """

    # Or(A, B, C, True) -> True
    if BoolSet(True) in literal_operands:
        alias_is_literal_and_check_predicate_eval(expr, True, mutator)
        return

    # Or(A, B, C, False) -> Or(A, B, C)
    # Or(A, B, A) -> Or(A, B)
    filtered_operands = {op for op in expr.operands if BoolSet(False) != op}
    if len(filtered_operands) != len(expr.operands):
        # Rebuild without False literals and duplicates
        mutator.mutate_expression(expr, operands=filtered_operands)
        return

    # Or(P) -> P
    # Or!(P) -> P!
    if len(expr.operands) == 1:
        mutator.mutate_unpack_expression(expr)
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
        # ¬(¬A) -> A
        # ¬!(¬A) -> !A
        if isinstance(op, Not):
            inner_most = op.operands[0]
            if is_literal(inner_most):
                alias_is_literal(expr, inner_most, mutator, terminate=True)
            else:
                mutator.mutator_neutralize_expressions(expr)
            return

        # TODO this is kinda ugly
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
                                cast_assert(
                                    ConstrainableExpression,
                                    mutator.get_copy(not_op),
                                ).constrain()
                    # ¬(A v ...)
                    elif isinstance(inner_op, ConstrainableExpression):
                        parent_nots = inner_op.get_operations(Not)
                        if parent_nots:
                            for n in parent_nots:
                                n.constrain()
                        else:
                            mutator.create_expression(
                                Not, inner_op, from_ops=[expr]
                            ).constrain()

    if expr.constrained:
        alias_is_literal_and_check_predicate_eval(op, False, mutator)


def if_operands_same_make_true(pred: Predicate, mutator: Mutator) -> bool:
    if pred.operands[0] is not pred.operands[1]:
        return False
    if not isinstance(pred.operands[0], ParameterOperatable):
        return False
    alias_is_literal_and_check_predicate_eval(pred, True, mutator)
    return True


def fold_is(
    expr: Is,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    """
    ```
    A is A -> True
    A is X, A is Y | X != Y, X,Y lit -> Contradiction
    # predicates
    P is! True -> P!
    P is! False -> ¬!P
    P1 is! P2! -> P1!
    A is B | A or B unconstrained -> True
    # literals
    X is Y | X == Y -> True
    X is Y | X != Y -> False
    ```
    """

    # A is B -> R is R
    # A is E -> R is R, R is E
    # A is False, E is False
    #

    # A is A -> A is!! A
    if if_operands_same_make_true(expr, mutator):
        return

    # A is X, A is Y | X != Y -> Contradiction
    # happens automatically because of alias class merge

    if expr.constrained:
        # P1 is! True -> P1!
        # P1 is! P2!  -> P1!
        if BoolSet(True) in literal_operands or any(
            op.constrained
            for op in expr.get_operatable_operands(ConstrainableExpression)
        ):
            for p in expr.get_operatable_operands(ConstrainableExpression):
                p.constrain()
        # P is! False -> ¬!P
        if BoolSet(False) in literal_operands:
            for p in expr.get_operatable_operands(ConstrainableExpression):
                mutator.create_expression(Not, p, from_ops=[expr]).constrain()


def fold_subset(
    expr: IsSubset,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
):
    """
    ```
    A ss A -> True
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

    # A ss A -> True
    if if_operands_same_make_true(expr, mutator):
        return

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
            A.constrain()
        # P ss! False -> ¬!P
        if B == BoolSet(False):
            assert isinstance(A, ConstrainableExpression)
            mutator.create_expression(Not, A, from_ops=[expr]).constrain()


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
    # A >= A
    if if_operands_same_make_true(expr, mutator):
        return

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


# Boilerplate --------------------------------------------------------------------------


def fold(
    expr: CanonicalOperation,
    literal_operands: Sequence[Literal],
    replacable_nonliteral_operands: Counter[ParameterOperatable],
    non_replacable_nonliteral_operands: Sequence[ParameterOperatable],
    mutator: Mutator,
) -> None:
    """
    literal_operands must be actual literals, not the literal the operand is aliased to!
    maybe it would be fine for set literals with one element?
    """

    def get_func[T: CanonicalOperation](
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
            # TODO implement
            return lambda *args: None
        elif isinstance(expr, Abs):
            # TODO implement
            return lambda *args: None
        elif isinstance(expr, Sin):
            # TODO implement
            return lambda *args: None
        elif isinstance(expr, Log):
            # TODO implement
            return lambda *args: None
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


def fold_literals(mutator: Mutator, expr_type: type[CanonicalOperation]):
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
        if all(ParameterOperatable.is_literal(o) for o in expr.operands):
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


def _get_fold_func(expr_type: type[CanonicalOperation]) -> Callable[[Mutator], None]:
    def wrapped(mutator: Mutator):
        fold_literals(mutator, expr_type)

    wrapped.__name__ = f"_fold_{expr_type.__name__}"

    return wrapped


def _multi(op: Callable, init=None) -> Callable:
    def wrapped(*args):
        if init is not None:
            init_lit = make_lit(init)
            args = [init_lit, init_lit, *args]
        assert args
        return functools.reduce(op, args)

    return wrapped


# TODO consider making the oprerator property of the expression type

_CanonicalOperations = {
    Add: _multi(operator.add, 0),
    Multiply: _multi(operator.mul, 1),
    Power: operator.pow,
    Round: round,
    Abs: abs,
    Sin: Quantity_Interval_Disjoint.op_sin,
    Log: Quantity_Interval_Disjoint.op_log,
    Or: _multi(BoolSet.op_or, False),
    Not: BoolSet.op_not,
    Intersection: _multi(operator.and_),
    Union: _multi(operator.or_),
    SymmetricDifference: operator.xor,
    Is: operator.eq,
    GreaterOrEqual: operator.ge,
    GreaterThan: operator.gt,
    IsSubset: P_Set.is_subset_of,
}


fold_algorithms = [
    algorithm(f"Fold {expr_type.__name__}", destructive=False)(
        _get_fold_func(expr_type)
    )
    for expr_type in _CanonicalOperations
]

# Pure literal folding -----------------------------------------------------------------


def _exec_pure_literal_expressions(expr: CanonicalOperation) -> SolverLiteral:
    assert all(ParameterOperatable.is_literal(o) for o in expr.operands)
    return _CanonicalOperations[type(expr)](*expr.operands)


@algorithm("Fold pure literal expressions", destructive=False)
def fold_pure_literal_expressions(mutator: Mutator):
    exprs = mutator.nodes_of_types(
        tuple(_CanonicalOperations.keys()), sort_by_depth=True
    )
    exprs = cast(Iterable[CanonicalOperation], exprs)

    for expr in exprs:
        # TODO is this needed?
        if mutator.has_been_mutated(expr) or mutator.is_removed(expr):
            continue

        if not all(ParameterOperatable.is_literal(o) for o in expr.operands):
            continue

        result = _exec_pure_literal_expressions(expr)
        # type ignore because function sig is not 100% correct
        alias_is_literal_and_check_predicate_eval(expr, result, mutator)  # type: ignore
