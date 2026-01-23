# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
Utilities for rewriting expression trees, particularly for isolating variables
in equations.
"""

import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Callable

import pytest

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.algorithm import algorithm
from faebryk.core.solver.mutator import Mutator
from faebryk.library.Expressions import is_predicate
from faebryk.libs.util import not_none

if TYPE_CHECKING:
    from faebryk.libs.test.boundexpressions import BoundExpressions

logger = logging.getLogger(__name__)

# Type aliases - only canonical arithmetic expressions
# Note: Subtract and Divide are NOT canonical; they get converted to
# Add(x, Multiply(y, -1)) and Multiply(x, Power(y, -1)) respectively
Add = F.Expressions.Add
Multiply = F.Expressions.Multiply
Power = F.Expressions.Power
Is = F.Expressions.Is


@dataclass
class PathSegment:
    """Represents one step in the path from root expression to target variable."""

    expr_type: type[fabll.NodeT]  # Add, Multiply, Power
    operand_index: int  # Which operand contains the variable
    other_operands: list[F.Parameters.can_be_operand]  # Siblings to invert


@dataclass
class VariablePath:
    """Path from expression root to target variable."""

    segments: list[PathSegment]
    variable: F.Parameters.is_parameter_operatable


def _contains_variable(
    operand: F.Parameters.can_be_operand,
    target: F.Parameters.is_parameter_operatable,
) -> bool:
    """Check if an operand contains the target variable (recursively)."""
    # Check if operand IS the target
    if po := operand.as_parameter_operatable.try_get():
        if po.is_same(target):
            return True
        # If it's an expression, check leaves recursively
        if expr := po.as_expression.try_get():
            leaves = expr.get_operand_leaves_operatable()
            return any(leaf.is_same(target) for leaf in leaves)
    return False


def _get_expression_type(
    expr: F.Expressions.is_expression,
) -> type[fabll.NodeT] | None:
    """Get the concrete canonical expression type if invertible."""
    expr_obj = fabll.Traits(expr).get_obj_raw()

    # Only canonical arithmetic expressions are invertible
    for expr_type in [Add, Multiply, Power]:
        if expr_obj.isinstance(expr_type):
            return expr_type

    # Non-invertible or non-canonical expression types
    return None


def _find_path_to_variable(
    root: F.Parameters.can_be_operand,
    target: F.Parameters.is_parameter_operatable,
) -> VariablePath | None:
    """
    Find the path from root to target variable.

    Returns None if:
    - Variable not found
    - Variable appears multiple times (non-linear)
    - Expression type is not invertible
    """
    # Base case: root IS the variable
    if po := root.as_parameter_operatable.try_get():
        if po.is_same(target):
            return VariablePath(segments=[], variable=target)

        # Check if it's an expression we can traverse
        expr = po.as_expression.try_get()
        if expr is None:
            # It's a parameter but not our target
            return None

        # Get expression type for inversion
        expr_type = _get_expression_type(expr)
        if expr_type is None:
            return None  # Not an invertible expression

        # Check which operand(s) contain the variable
        operands = expr.get_operands()
        var_operand_indices = []

        for i, op in enumerate(operands):
            if _contains_variable(op, target):
                var_operand_indices.append(i)

        # Non-linear: variable in multiple operands
        if len(var_operand_indices) != 1:
            return None

        var_index = var_operand_indices[0]
        var_operand = operands[var_index]
        other_operands = [op for i, op in enumerate(operands) if i != var_index]

        # Recursively find path in the operand containing variable
        sub_path = _find_path_to_variable(var_operand, target)
        if sub_path is None:
            return None

        # Prepend this segment
        segment = PathSegment(
            expr_type=expr_type,
            operand_index=var_index,
            other_operands=other_operands,
        )
        return VariablePath(
            segments=[segment] + sub_path.segments,
            variable=sub_path.variable,
        )

    # Literal - can't contain variable
    return None


def _apply_inverse_operations(
    mutator: Mutator,
    other_side: F.Parameters.can_be_operand,
    path: VariablePath,
    from_ops: list[F.Parameters.is_parameter_operatable],
) -> F.Parameters.can_be_operand | None:
    """
    Apply inverse operations to transform other_side based on path.

    For path [Add(idx=0, others=[B,C]), Multiply(idx=1, others=[D])]:
    - other_side = X
    - After Add inversion: (X - B - C)
    - After Multiply inversion: (X - B - C) / D

    Returns None if inversion is not possible (e.g., variable in exponent).
    """
    assert path.segments
    result = other_side

    for segment in path.segments:
        result = _apply_single_inverse(mutator, result, segment, from_ops)
        if result is None:
            return None

    return result


def _apply_single_inverse(
    mutator: Mutator,
    current: F.Parameters.can_be_operand,
    segment: PathSegment,
    from_ops: list[F.Parameters.is_parameter_operatable],
) -> F.Parameters.can_be_operand | None:
    """
    Apply the inverse of one operation.

    Canonical inversions:
    - Add: subtract the other operands -> Add(current, Multiply(other, -1), ...)
    - Multiply: divide by other operands -> Multiply(current, Power(other, -1), ...)
    - Power (base): take root -> Power(current, Power(exponent, -1))
    - Power (exponent): requires Log - not supported, returns None
    """
    if segment.expr_type is Add:
        # current = original + others
        # isolated = current - others
        # In canonical: Add(current, Multiply(other1, -1), Multiply(other2, -1), ...)
        neg_operands: list[F.Parameters.can_be_operand] = []
        for other in segment.other_operands:
            minus_one = mutator.make_singleton(-1.0).can_be_operand.get()
            neg_result = mutator.create_check_and_insert_expression(
                Multiply,
                other,
                minus_one,
                from_ops=from_ops,
            )
            neg_operands.append(neg_result.out_operand)

        add_result = mutator.create_check_and_insert_expression(
            Add,
            current,
            *neg_operands,
            from_ops=from_ops,
        )
        return add_result.out_operand

    elif segment.expr_type is Multiply:
        # current = original * others
        # isolated = current / others
        # In canonical: Multiply(current, Power(other1, -1), Power(other2, -1), ...)
        inv_operands: list[F.Parameters.can_be_operand] = []
        for other in segment.other_operands:
            minus_one = mutator.make_singleton(-1.0).can_be_operand.get()
            inv_result = mutator.create_check_and_insert_expression(
                Power,
                other,
                minus_one,
                from_ops=from_ops,
            )
            inv_operands.append(inv_result.out_operand)

        mul_result = mutator.create_check_and_insert_expression(
            Multiply,
            current,
            *inv_operands,
            from_ops=from_ops,
        )
        return mul_result.out_operand

    elif segment.expr_type is Power:
        if segment.operand_index == 0:
            # Power(var, exp) = current  ->  var = current^(1/exp)
            # In canonical: Power(current, Power(exponent, -1))
            if len(segment.other_operands) != 1:
                return None
            exponent = segment.other_operands[0]
            minus_one = mutator.make_singleton(-1.0).can_be_operand.get()
            inv_exp_result = mutator.create_check_and_insert_expression(
                Power,
                exponent,
                minus_one,
                from_ops=from_ops,
            )

            pow_result = mutator.create_check_and_insert_expression(
                Power,
                current,
                inv_exp_result.out_operand,
                from_ops=from_ops,
            )
            return pow_result.out_operand
        else:
            # Power(base, var) = current  ->  var = log_base(current)
            # TODO
            return None

    return None


class RewriteResult(Enum):
    ALREADY_ISOLATED = auto()
    CANNOT_ISOLATE = auto()


def rewrite_equation_for_variable(
    mutator: Mutator,
    is_expr: Is,
    variable: F.Parameters.is_parameter_operatable,
) -> Is | RewriteResult:
    """
    Rewrite an Is expression to isolate a target variable.

    Example:
        X + (Y * A) is! (B + C), target=B
        ->  B is! X + (Y * A) - C

    Args:
        mutator: The mutator for graph operations
        is_expr: The Is expression to rewrite
        variable: The variable to isolate

    Returns:
        - Is: A new Is expression with the variable isolated on one side
        - RewriteResult.ALREADY_ISOLATED: Variable is already isolated
        - RewriteResult.CANNOT_ISOLATE: Cannot isolate (variable not found,
          on both sides, non-linear, or in exponent position)
    """
    expr = is_expr.is_expression.get()
    operands = expr.get_operands()

    if len(operands) != 2:
        return RewriteResult.CANNOT_ISOLATE
    left, right = operands

    # Step 1: Find which side has the variable
    match (_contains_variable(left, variable), _contains_variable(right, variable)):
        case (True, True):
            # Variable on both sides - cannot isolate simply
            return RewriteResult.CANNOT_ISOLATE
        case (False, False):
            # Variable not found
            return RewriteResult.CANNOT_ISOLATE
        case (True, False):
            var_side = left
            other_side = right
        case (False, True):
            var_side = right
            other_side = left

    # Step 2: Find path to variable
    path = _find_path_to_variable(var_side, variable)
    if path is None:
        return RewriteResult.CANNOT_ISOLATE

    # Step 3: If path is empty, variable is already isolated
    if not path.segments:
        return RewriteResult.ALREADY_ISOLATED

    # Track source expression for debugging
    from_ops = [expr.as_parameter_operatable.get()]

    # Step 4: Apply inverse operations to other side
    transformed_other = _apply_inverse_operations(mutator, other_side, path, from_ops)
    if transformed_other is None:
        return RewriteResult.CANNOT_ISOLATE

    # Step 5: Create new Is expression: var is! transformed_other
    result = mutator.create_check_and_insert_expression(
        Is,
        variable.as_operand.get(),
        transformed_other,
        from_ops=from_ops,
        assert_=expr.try_get_sibling_trait(F.Expressions.is_predicate) is not None,
        allow_uncorrelated_congruence_match=True,
    )

    return (
        fabll.Traits(result.out_operand).get_obj_raw().try_cast(Is)
        or RewriteResult.CANNOT_ISOLATE
    )


@algorithm("permutate equation operands", terminal=False)
def permutate_equation_operands(mutator: Mutator):
    for equation in mutator.get_typed_expressions(Is, required_traits=(is_predicate,)):
        leaves = equation.is_expression.get().get_operand_leaves_operatable()
        if len(leaves) < 2:
            continue
        for p in leaves:
            rewrite_equation_for_variable(mutator, equation, p)


# =============================================================================
# Tests
# =============================================================================


@dataclass
class RewriteTestCase:
    """
    Test case for rewrite_equation_for_variable.

    For success cases: expected_result is None and expected_builder provides expected.
    For already isolated: expected_result is RewriteResult.ALREADY_ISOLATED.
    For failure cases: expected_result is RewriteResult.CANNOT_ISOLATE.
    """

    name: str
    # Creates (is_expr, target_var, params_dict)
    setup: Callable[
        ["BoundExpressions"],
        tuple[
            Is,
            F.Parameters.is_parameter_operatable,
            dict[str, F.Parameters.can_be_operand],
        ],
    ]
    # Builds expected "other side" operand for success cases
    expected_builder: (
        Callable[
            [Mutator, dict[str, F.Parameters.can_be_operand]],
            F.Parameters.can_be_operand,
        ]
        | None
    ) = None
    # Expected result type for non-success cases
    expected_result: RewriteResult | None = None
    assert_input: bool = False
    failure_reason: str | None = None


def _build_expected_add_isolate_first(
    m: Mutator, p: dict[str, F.Parameters.can_be_operand]
) -> F.Parameters.can_be_operand:
    """A + B is C, isolate A -> A is C + (B * -1)"""
    neg_b = m.create_check_and_insert_expression(
        Multiply,
        m.get_copy(p["B"]),
        m.make_singleton(-1.0).can_be_operand.get(),
        allow_uncorrelated_congruence_match=True,
    ).out_operand
    assert neg_b is not None
    result = m.create_check_and_insert_expression(
        Add,
        m.get_copy(p["C"]),
        neg_b,
        allow_uncorrelated_congruence_match=True,
    ).out_operand
    assert result is not None
    return result


def _build_expected_add_isolate_second(
    m: Mutator, p: dict[str, F.Parameters.can_be_operand]
) -> F.Parameters.can_be_operand:
    """A + B is C, isolate B -> B is C + (A * -1)"""
    neg_a = m.create_check_and_insert_expression(
        Multiply,
        m.get_copy(p["A"]),
        m.make_singleton(-1.0).can_be_operand.get(),
        allow_uncorrelated_congruence_match=True,
    ).out_operand
    assert neg_a is not None
    result = m.create_check_and_insert_expression(
        Add,
        m.get_copy(p["C"]),
        neg_a,
        allow_uncorrelated_congruence_match=True,
    ).out_operand
    assert result is not None
    return result


def _build_expected_multiply_isolate(
    m: Mutator, p: dict[str, F.Parameters.can_be_operand]
) -> F.Parameters.can_be_operand:
    """A * B is C, isolate A -> A is C * (B ^ -1)"""
    inv_b = m.create_check_and_insert_expression(
        Power,
        m.get_copy(p["B"]),
        m.make_singleton(-1.0).can_be_operand.get(),
        allow_uncorrelated_congruence_match=True,
    ).out_operand
    assert inv_b is not None
    result = m.create_check_and_insert_expression(
        Multiply,
        m.get_copy(p["C"]),
        inv_b,
        allow_uncorrelated_congruence_match=True,
    ).out_operand
    assert result is not None
    return result


def _build_expected_power_base_isolate(
    m: Mutator, p: dict[str, F.Parameters.can_be_operand]
) -> F.Parameters.can_be_operand:
    """A ^ 2 is B, isolate A -> A is B ^ 0.5"""
    # Note: 2^-1 may be folded to 0.5 literal
    result = m.create_check_and_insert_expression(
        Power,
        m.get_copy(p["B"]),
        m.make_singleton(0.5).can_be_operand.get(),
        allow_uncorrelated_congruence_match=True,
    ).out_operand
    assert result is not None
    return result


def _build_expected_lit_factor_isolate(
    m: Mutator, p: dict[str, F.Parameters.can_be_operand]
) -> F.Parameters.can_be_operand:
    """A * 2 is B, isolate A -> A is B * 0.5"""
    result = m.create_check_and_insert_expression(
        Multiply,
        m.get_copy(p["B"]),
        m.make_singleton(0.5).can_be_operand.get(),
        allow_uncorrelated_congruence_match=True,
    ).out_operand
    assert result is not None
    return result


def _build_expected_nested(
    m: Mutator, p: dict[str, F.Parameters.can_be_operand]
) -> F.Parameters.can_be_operand:
    """X + (Y * A) is (B + C), isolate B -> B is (X + (Y * A)) + (C * -1)"""
    # Build X + (Y * A)
    y_times_a = m.create_check_and_insert_expression(
        Multiply,
        m.get_copy(p["Y"]),
        m.get_copy(p["A"]),
        allow_uncorrelated_congruence_match=True,
    ).out_operand
    assert y_times_a is not None
    x_plus_ya = m.create_check_and_insert_expression(
        Add,
        m.get_copy(p["X"]),
        y_times_a,
        allow_uncorrelated_congruence_match=True,
    ).out_operand
    assert x_plus_ya is not None
    # Build (C * -1)
    neg_c = m.create_check_and_insert_expression(
        Multiply,
        m.get_copy(p["C"]),
        m.make_singleton(-1.0).can_be_operand.get(),
        allow_uncorrelated_congruence_match=True,
    ).out_operand
    assert neg_c is not None
    # Combine
    result = m.create_check_and_insert_expression(
        Add,
        x_plus_ya,
        neg_c,
        allow_uncorrelated_congruence_match=True,
    ).out_operand
    assert result is not None
    return result


def _build_expected_add_isolate_second_side(
    m: Mutator, p: dict[str, F.Parameters.can_be_operand]
) -> F.Parameters.can_be_operand:
    """(A + B) is (A + C), isolate B -> B is (A + C) + (A * -1)"""
    neg_a = m.create_check_and_insert_expression(
        Multiply,
        m.get_copy(p["A"]),
        m.make_singleton(-1.0).can_be_operand.get(),
        allow_uncorrelated_congruence_match=True,
    ).out_operand
    assert neg_a is not None
    result = m.create_check_and_insert_expression(
        Add,
        m.create_check_and_insert_expression(
            Add,
            m.get_copy(p["A"]),
            m.get_copy(p["C"]),
            allow_uncorrelated_congruence_match=True,
        ).out_operand,
        neg_a,
        allow_uncorrelated_congruence_match=True,
    ).out_operand
    assert result is not None
    return result


def _build_expected_nary_add(
    m: Mutator, p: dict[str, F.Parameters.can_be_operand]
) -> F.Parameters.can_be_operand:
    """A + B + C + D is E, isolate B -> B is E + (A * -1) + (C * -1) + (D * -1)"""
    neg_a = m.create_check_and_insert_expression(
        Multiply,
        m.get_copy(p["A"]),
        m.make_singleton(-1.0).can_be_operand.get(),
        allow_uncorrelated_congruence_match=True,
    ).out_operand
    assert neg_a is not None
    neg_c = m.create_check_and_insert_expression(
        Multiply,
        m.get_copy(p["C"]),
        m.make_singleton(-1.0).can_be_operand.get(),
        allow_uncorrelated_congruence_match=True,
    ).out_operand
    assert neg_c is not None
    neg_d = m.create_check_and_insert_expression(
        Multiply,
        m.get_copy(p["D"]),
        m.make_singleton(-1.0).can_be_operand.get(),
        allow_uncorrelated_congruence_match=True,
    ).out_operand
    assert neg_d is not None
    result = m.create_check_and_insert_expression(
        Add,
        m.get_copy(p["E"]),
        neg_a,
        neg_c,
        neg_d,
        allow_uncorrelated_congruence_match=True,
    ).out_operand
    assert result is not None
    return result


def _build_expected_divide_isolate_denominator(
    m: Mutator, p: dict[str, F.Parameters.can_be_operand]
) -> F.Parameters.can_be_operand:
    """
    A * B^(-1) is C, isolate B -> B is (C * A^(-1))^(-1)

    Math: A * B^(-1) = C  =>  B^(-1) = C * A^(-1)  =>  B = (C * A^(-1))^(-1)
    Note: (C * A^(-1))^(-1) = A * C^(-1) mathematically, but our algorithm
    produces the former structure.
    """
    # B^(-1) = C * A^(-1)
    inv_a = m.create_check_and_insert_expression(
        Power,
        m.get_copy(p["A"]),
        m.make_singleton(-1.0).can_be_operand.get(),
        allow_uncorrelated_congruence_match=True,
    ).out_operand
    assert inv_a is not None
    c_div_a = m.create_check_and_insert_expression(
        Multiply,
        m.get_copy(p["C"]),
        inv_a,
        allow_uncorrelated_congruence_match=True,
    ).out_operand
    assert c_div_a is not None
    # B = (C * A^(-1))^(-1)
    result = m.create_check_and_insert_expression(
        Power,
        c_div_a,
        m.make_singleton(-1.0).can_be_operand.get(),
        allow_uncorrelated_congruence_match=True,
    ).out_operand
    assert result is not None
    return result


def _build_expected_deeply_nested(
    m: Mutator, p: dict[str, F.Parameters.can_be_operand]
) -> F.Parameters.can_be_operand:
    """((A + B) * C) + D is E, isolate A -> A is ((E + (D * -1)) * C^-1) + (B * -1)"""
    # Step 1: E + (D * -1)
    neg_d = m.create_check_and_insert_expression(
        Multiply,
        m.get_copy(p["D"]),
        m.make_singleton(-1.0).can_be_operand.get(),
        allow_uncorrelated_congruence_match=True,
    ).out_operand
    assert neg_d is not None
    e_minus_d = m.create_check_and_insert_expression(
        Add,
        m.get_copy(p["E"]),
        neg_d,
        allow_uncorrelated_congruence_match=True,
    ).out_operand
    assert e_minus_d is not None
    # Step 2: (E + (D * -1)) * C^-1
    inv_c = m.create_check_and_insert_expression(
        Power,
        m.get_copy(p["C"]),
        m.make_singleton(-1.0).can_be_operand.get(),
        allow_uncorrelated_congruence_match=True,
    ).out_operand
    assert inv_c is not None
    divided_by_c = m.create_check_and_insert_expression(
        Multiply,
        e_minus_d,
        inv_c,
        allow_uncorrelated_congruence_match=True,
    ).out_operand
    assert divided_by_c is not None
    # Step 3: ... + (B * -1)
    neg_b = m.create_check_and_insert_expression(
        Multiply,
        m.get_copy(p["B"]),
        m.make_singleton(-1.0).can_be_operand.get(),
        allow_uncorrelated_congruence_match=True,
    ).out_operand
    assert neg_b is not None
    result = m.create_check_and_insert_expression(
        Add,
        divided_by_c,
        neg_b,
        allow_uncorrelated_congruence_match=True,
    ).out_operand
    assert result is not None
    return result


TEST_CASES = [
    RewriteTestCase(
        name="add_isolate_first",
        setup=lambda E: (
            fabll.Traits(
                E.is_(
                    E.add(A := E.parameter_op(), B := E.parameter_op()),
                    C := E.parameter_op(),
                )
            ).get_obj(Is),
            A.as_parameter_operatable.force_get(),
            {"A": A, "B": B, "C": C},
        ),
        expected_builder=_build_expected_add_isolate_first,
    ),
    RewriteTestCase(
        name="add_isolate_second",
        setup=lambda E: (
            fabll.Traits(
                E.is_(
                    E.add(A := E.parameter_op(), B := E.parameter_op()),
                    C := E.parameter_op(),
                )
            ).get_obj(Is),
            B.as_parameter_operatable.force_get(),
            {"A": A, "B": B, "C": C},
        ),
        expected_builder=_build_expected_add_isolate_second,
    ),
    RewriteTestCase(
        name="multiply_isolate",
        setup=lambda E: (
            fabll.Traits(
                E.is_(
                    E.multiply(A := E.parameter_op(), B := E.parameter_op()),
                    C := E.parameter_op(),
                )
            ).get_obj(Is),
            A.as_parameter_operatable.force_get(),
            {"A": A, "B": B, "C": C},
        ),
        expected_builder=_build_expected_multiply_isolate,
    ),
    RewriteTestCase(
        name="power_base_isolate",
        setup=lambda E: (
            fabll.Traits(
                E.is_(
                    E.power(A := E.parameter_op(), E.lit_op_single(2.0)),
                    B := E.parameter_op(),
                )
            ).get_obj(Is),
            A.as_parameter_operatable.force_get(),
            {"A": A, "B": B},
        ),
        expected_builder=_build_expected_power_base_isolate,
    ),
    RewriteTestCase(
        name="lit_factor_isolate",
        setup=lambda E: (
            fabll.Traits(
                E.is_(
                    E.multiply(A := E.parameter_op(), E.lit_op_single(2.0)),
                    B := E.parameter_op(),
                )
            ).get_obj(Is),
            A.as_parameter_operatable.force_get(),
            {"A": A, "B": B},
        ),
        expected_builder=_build_expected_lit_factor_isolate,
    ),
    RewriteTestCase(
        name="nested_multiply_in_add",
        setup=lambda E: (
            fabll.Traits(
                E.is_(
                    E.add(
                        X := E.parameter_op(),
                        E.multiply(Y := E.parameter_op(), A := E.parameter_op()),
                    ),
                    E.add(B := E.parameter_op(), C := E.parameter_op()),
                )
            ).get_obj(Is),
            B.as_parameter_operatable.force_get(),
            {"X": X, "Y": Y, "A": A, "B": B, "C": C},
        ),
        expected_builder=_build_expected_nested,
    ),
    RewriteTestCase(
        name="already_isolated",
        setup=lambda E: (
            fabll.Traits(
                E.is_(
                    A := E.parameter_op(),
                    E.add(B := E.parameter_op(), C := E.parameter_op()),
                )
            ).get_obj(Is),
            A.as_parameter_operatable.force_get(),
            {"A": A, "B": B, "C": C},
        ),
        expected_result=RewriteResult.ALREADY_ISOLATED,
    ),
    RewriteTestCase(
        name="assertion_propagated",
        setup=lambda E: (
            fabll.Traits(
                E.is_(
                    E.add(A := E.parameter_op(), B := E.parameter_op()),
                    C := E.parameter_op(),
                    assert_=True,
                )
            ).get_obj(Is),
            A.as_parameter_operatable.force_get(),
            {"A": A, "B": B, "C": C},
        ),
        expected_builder=_build_expected_add_isolate_first,
        assert_input=True,
    ),
    RewriteTestCase(
        name="add_isolate_second_side",
        setup=lambda E: (
            fabll.Traits(
                E.is_(
                    E.add(A := E.parameter_op(), (B := E.parameter_op())),
                    E.add(A, (C := E.parameter_op())),
                )
            ).get_obj(Is),
            B.as_parameter_operatable.force_get(),
            {"A": A, "B": B, "C": C},
        ),
        expected_builder=_build_expected_add_isolate_second_side,
        assert_input=False,
    ),
    # N-ary Add: A + B + C + D is E, isolate B
    RewriteTestCase(
        name="nary_add_isolate",
        setup=lambda E: (
            fabll.Traits(
                E.is_(
                    E.add(
                        A := E.parameter_op(),
                        B := E.parameter_op(),
                        C := E.parameter_op(),
                        D := E.parameter_op(),
                    ),
                    EE := E.parameter_op(),
                )
            ).get_obj(Is),
            B.as_parameter_operatable.force_get(),
            {"A": A, "B": B, "C": C, "D": D, "E": EE},
        ),
        expected_builder=_build_expected_nary_add,
    ),
    # Division pattern (canonical): A * B^(-1) is C, isolate B
    # This is A / B = C in canonical form, so B = A / C = A * C^(-1)
    RewriteTestCase(
        name="divide_isolate_denominator",
        setup=lambda E: (
            fabll.Traits(
                E.is_(
                    E.divide(
                        A := E.parameter_op(),
                        B := E.parameter_op(),
                    ),
                    C := E.parameter_op(),
                )
            ).get_obj(Is),
            B.as_parameter_operatable.force_get(),
            {"A": A, "B": B, "C": C},
        ),
        expected_builder=_build_expected_divide_isolate_denominator,
    ),
    # Deeply nested: ((A + B) * C) + D is E, isolate A
    RewriteTestCase(
        name="deeply_nested",
        setup=lambda E: (
            fabll.Traits(
                E.is_(
                    E.add(
                        E.multiply(
                            E.add(A := E.parameter_op(), B := E.parameter_op()),
                            C := E.parameter_op(),
                        ),
                        D := E.parameter_op(),
                    ),
                    EE := E.parameter_op(),
                )
            ).get_obj(Is),
            A.as_parameter_operatable.force_get(),
            {"A": A, "B": B, "C": C, "D": D, "E": EE},
        ),
        expected_builder=_build_expected_deeply_nested,
    ),
    # Note: literal_rhs test removed - Is expression cannot have literal operands
    # Failure cases
    RewriteTestCase(
        name="variable_not_found",
        setup=lambda E: (
            fabll.Traits(
                E.is_(E.add(E.parameter_op(), E.parameter_op()), E.parameter_op())
            ).get_obj(Is),
            E.parameter_op().as_parameter_operatable.force_get(),
            {},
        ),
        expected_result=RewriteResult.CANNOT_ISOLATE,
        failure_reason="variable not in expression",
    ),
    RewriteTestCase(
        name="variable_both_sides",
        setup=lambda E: (
            fabll.Traits(
                E.is_(
                    E.add(A := E.parameter_op(), E.parameter_op()),
                    E.add(A, E.parameter_op()),
                )
            ).get_obj(Is),
            A.as_parameter_operatable.force_get(),
            {},
        ),
        expected_result=RewriteResult.CANNOT_ISOLATE,
        failure_reason="variable on both sides",
    ),
    RewriteTestCase(
        name="variable_nonlinear",
        setup=lambda E: (
            fabll.Traits(
                E.is_(E.multiply(A := E.parameter_op(), A), E.parameter_op())
            ).get_obj(Is),
            A.as_parameter_operatable.force_get(),
            {},
        ),
        expected_result=RewriteResult.CANNOT_ISOLATE,
        failure_reason="variable appears multiple times (non-linear)",
    ),
]


class TestRewriteEquation:
    """Parametrized tests for rewrite_equation_for_variable."""

    @pytest.mark.parametrize(
        "case",
        TEST_CASES,
        ids=[c.name for c in TEST_CASES],
    )
    def test_rewrite(self, case: RewriteTestCase):
        """Test equation rewriting (both success and failure cases)."""

        from faebryk.core.solver.algorithm import algorithm
        from faebryk.core.solver.mutator import MutationMap
        from faebryk.libs.test.boundexpressions import BoundExpressions

        E = BoundExpressions()
        is_expr, target_var, params = case.setup(E)

        # Print test info
        print(f"\n{'=' * 60}")
        print(f"Test: {case.name}")
        is_expr_str = is_expr.is_expression.get().compact_repr(no_lit_suffix=True)
        print(f"Original: {is_expr_str}")
        print(f"Isolating: {target_var.compact_repr(no_lit_suffix=True)}")

        # Verify input assertion state
        input_expr = is_expr.is_expression.get()
        input_is_asserted = (
            input_expr.try_get_sibling_trait(F.Expressions.is_predicate) is not None
        )
        assert input_is_asserted == case.assert_input, (
            f"Input assertion mismatch: expected {case.assert_input}, "
            f"got {input_is_asserted}"
        )

        # Create mutator
        @algorithm("test")
        def test_algo(mutator: Mutator):
            pass

        param = E.parameter_op()
        mut_map = MutationMap.bootstrap(param.tg, param.g)
        mutator = Mutator(
            mut_map,
            algo=test_algo,
            iteration=0,
            terminal=True,
        )
        canon_expr = not_none(
            mut_map.map_forward(is_expr.is_parameter_operatable.get()).maps_to
        ).as_expression.force_get()
        print(f"Canonicalized: {canon_expr.compact_repr(no_lit_suffix=True)}")
        target_var = not_none(mut_map.map_forward(target_var).maps_to)

        # Run the rewrite
        result = rewrite_equation_for_variable(
            mutator, fabll.Traits(canon_expr).get_obj(Is), target_var
        )

        if case.expected_result is not None:
            # Expected a RewriteResult enum value
            print(f"Expected: {case.expected_result.name}")
            if case.failure_reason:
                print(f"  Reason: {case.failure_reason}")
            assert result == case.expected_result, (
                f"Expected {case.expected_result}, got {result}"
            )
            print(f"Result:   {result.name} (as expected)")
        else:
            # Success case - expected an Is expression
            assert isinstance(result, Is), f"Expected Is expression, got {result}"
            result_str = result.is_expression.get().compact_repr(no_lit_suffix=True)
            print(f"Result:   {result_str}")

            # Find the isolated variable and other side
            operands = result.is_expression.get().get_operands()
            assert len(operands) == 2, f"Is should have 2 operands, got {len(operands)}"

            # Find which side has the isolated variable
            isolated_side = None
            other_side = None
            for i, op in enumerate(operands):
                if po := op.as_parameter_operatable.try_get():
                    if (
                        po.get_obj().instance.node().get_uuid()
                        == target_var.get_obj().instance.node().get_uuid()
                    ):
                        isolated_side = op
                        other_side = operands[1 - i]
                        break

            assert isolated_side is not None, "Variable should be isolated on one side"
            assert other_side is not None

            # Build expected and check congruence
            assert case.expected_builder is not None
            expected = case.expected_builder(mutator, params)
            assert other_side.is_same(expected), (
                f"Result structure mismatch:\n"
                f"  Got:      {other_side.pretty()}\n"
                f"  Expected: {expected.pretty()}"
            )

            # Verify assertion propagation
            if case.assert_input:
                output_expr = result.is_expression.get()
                output_is_asserted = (
                    output_expr.try_get_sibling_trait(F.Expressions.is_predicate)
                    is not None
                )
                assert output_is_asserted, (
                    "Output should be asserted when input is asserted"
                )

        print(f"{'=' * 60}")
