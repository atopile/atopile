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
from faebryk.core.solver.mutator import ExpressionBuilder, Mutator
from faebryk.core.solver.symbolic.invariants import AliasClass
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


def _insert_result_operand(res) -> F.Parameters.can_be_operand | None:
    """
    Convert an invariants.InsertExpressionResult into the canonical operand to use
    as input for subsequent expression builders.

    - For non-predicate expressions: return their alias representative parameter.
    - For predicate expressions: return the expression operand itself.
    """
    out = getattr(res, "out", None)
    if out is None:
        return None
    if out.try_get_sibling_trait(F.Expressions.is_predicate) is not None:
        return out.as_operand.get()
    return AliasClass.of(out.as_operand.get()).representative()


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
    """Check if an operand contains the target variable (recursively).

    Note: the solver's alias invariant means most expression operands are
    representatives (parameters), not direct expression nodes. We follow the
    representative's alias to traverse the underlying expression tree.
    """

    def _uuid(op: F.Parameters.can_be_operand) -> int:
        return fabll.Traits(op).get_obj_raw().instance.node().get_uuid()

    def _try_get_expr(
        op: F.Parameters.can_be_operand,
    ) -> F.Expressions.is_expression | None:
        if direct := op.try_get_sibling_trait(F.Expressions.is_expression):
            return direct

        # Only parameters can be alias representatives; avoid AliasClass.of(...)
        # on plain parameters, which may participate in multiple Is predicates.
        if op.try_get_sibling_trait(F.Parameters.is_parameter) is None:
            return None

        for is_ in op.get_operations(F.Expressions.Is, predicates_only=True):
            try:
                alias = AliasClass.of(is_)
            except AssertionError:
                continue

            rep = alias.representative()
            if _uuid(rep) != _uuid(op):
                continue

            exprs = alias.get_with_trait(F.Expressions.is_expression)
            if len(exprs) == 1:
                return next(iter(exprs))

        return None

    def _rec(op: F.Parameters.can_be_operand, visited: set[int]) -> bool:
        op_uuid = _uuid(op)
        if op_uuid in visited:
            return False
        visited.add(op_uuid)

        if po := op.as_parameter_operatable.try_get():
            if po.is_same(target):
                return True

        if expr := _try_get_expr(op):
            return any(_rec(inner, visited) for inner in expr.get_operands())

        return False

    return _rec(operand, set())


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
    def _uuid(op: F.Parameters.can_be_operand) -> int:
        return fabll.Traits(op).get_obj_raw().instance.node().get_uuid()

    def _try_get_expr(op: F.Parameters.can_be_operand) -> F.Expressions.is_expression | None:
        if direct := op.try_get_sibling_trait(F.Expressions.is_expression):
            return direct

        if op.try_get_sibling_trait(F.Parameters.is_parameter) is None:
            return None

        for is_ in op.get_operations(F.Expressions.Is, predicates_only=True):
            try:
                alias = AliasClass.of(is_)
            except AssertionError:
                continue

            rep = alias.representative()
            if _uuid(rep) != _uuid(op):
                continue

            exprs = alias.get_with_trait(F.Expressions.is_expression)
            if len(exprs) == 1:
                return next(iter(exprs))

        return None

    def _rec(
        op: F.Parameters.can_be_operand, visited: set[int]
    ) -> VariablePath | None:
        op_uuid = _uuid(op)
        if op_uuid in visited:
            return None
        visited.add(op_uuid)

        if po := op.as_parameter_operatable.try_get():
            if po.is_same(target):
                return VariablePath(segments=[], variable=target)

        expr = _try_get_expr(op)
        if expr is None:
            return None

        expr_type = _get_expression_type(expr)
        if expr_type is None:
            return None

        operands = expr.get_operands()
        var_operand_indices = [
            i for i, inner in enumerate(operands) if _contains_variable(inner, target)
        ]

        if len(var_operand_indices) != 1:
            return None

        var_index = var_operand_indices[0]
        var_operand = operands[var_index]
        other_operands = [inner for i, inner in enumerate(operands) if i != var_index]

        sub_path = _rec(var_operand, visited)
        if sub_path is None:
            return None

        segment = PathSegment(
            expr_type=expr_type,
            operand_index=var_index,
            other_operands=other_operands,
        )
        return VariablePath(
            segments=[segment] + sub_path.segments,
            variable=sub_path.variable,
        )

    return _rec(root, set())


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


def _insert_expression_with_alias(
    mutator: Mutator,
    expr_factory: type[F.Expressions.ExpressionNodes],
    *operands: F.Parameters.can_be_operand,
    alias: F.Parameters.is_parameter,
    from_ops: list[F.Parameters.is_parameter_operatable],
    allow_uncorrelated_congruence_match: bool,
) -> "F.Expressions.is_expression | None":
    import faebryk.core.solver.symbolic.invariants as invariants

    res = invariants.wrap_insert_expression(
        mutator,
        ExpressionBuilder(
            expr_factory,
            list(operands),
            assert_=False,
            terminate=False,
            traits=[],
        ),
        alias=alias,
        expr_already_exists_in_old_graph=False,
        allow_uncorrelated_congruence_match=allow_uncorrelated_congruence_match,
    )

    if res.out is None:
        return None

    # Best-effort: keep mutation traceability in line with Mutator.create_* APIs.
    if res.is_new:
        mutator.transformations.created[res.out.as_parameter_operatable.get()] = list(
            set(from_ops)
        )

    return res.out


def _alias_is_for_expression(
    expr: F.Expressions.is_expression,
    alias_param: F.Parameters.is_parameter,
    *,
    mutator: Mutator,
) -> Is | None:
    """
    Find the Is! alias predicate linking `expr` to `alias_param`.

    Note: invariants may copy/merge alias parameters during insertion, so we
    always resolve `alias_param` into `mutator.G_out` before searching.
    """
    alias_out = (
        mutator.get_copy(alias_param.as_operand.get())
        .as_parameter_operatable.force_get()
        .as_parameter.force_get()
    )
    alias_uuid = alias_out.instance.node().get_uuid()
    expr_uuid = expr.instance.node().get_uuid()

    for is_ in alias_out.as_operand.get().get_operations(Is, predicates_only=True):
        e = is_.is_expression.get()
        exprs = e.get_operands_with_trait(F.Expressions.is_expression)
        params = e.get_operands_with_trait(F.Parameters.is_parameter)
        if any(ex.instance.node().get_uuid() == expr_uuid for ex in exprs) and any(
            p.instance.node().get_uuid() == alias_uuid for p in params
        ):
            return is_

    return None


def _apply_inverse_operations_alias_to_variable(
    mutator: Mutator,
    other_side: F.Parameters.can_be_operand,
    path: VariablePath,
    from_ops: list[F.Parameters.is_parameter_operatable],
    alias: F.Parameters.is_parameter,
) -> Is | None:
    """
    Like _apply_inverse_operations, but aliases the final resulting expression to
    `alias` (a parameter), and returns the created Is! alias expression.

    This avoids creating Is!(param, param) which currently triggers unsupported
    subsumption paths in invariants.
    """
    assert path.segments
    current = other_side

    for i, segment in enumerate(path.segments):
        is_last = i == len(path.segments) - 1
        if not is_last:
            current = not_none(_apply_single_inverse(mutator, current, segment, from_ops))
            continue

        if segment.expr_type is Add:
            neg_operands: list[F.Parameters.can_be_operand] = []
            for other in segment.other_operands:
                minus_one = mutator.make_singleton(-1.0).can_be_operand.get()
                neg_result = mutator.create_check_and_insert_expression(
                    Multiply,
                    other,
                    minus_one,
                    from_ops=from_ops,
                )
                neg_operands.append(not_none(_insert_result_operand(neg_result)))

            expr_out = _insert_expression_with_alias(
                mutator,
                Add,
                current,
                *neg_operands,
                alias=alias,
                from_ops=from_ops,
                allow_uncorrelated_congruence_match=True,
            )
        elif segment.expr_type is Multiply:
            inv_operands: list[F.Parameters.can_be_operand] = []
            for other in segment.other_operands:
                minus_one = mutator.make_singleton(-1.0).can_be_operand.get()
                inv_result = mutator.create_check_and_insert_expression(
                    Power,
                    other,
                    minus_one,
                    from_ops=from_ops,
                )
                inv_operands.append(not_none(_insert_result_operand(inv_result)))

            expr_out = _insert_expression_with_alias(
                mutator,
                Multiply,
                current,
                *inv_operands,
                alias=alias,
                from_ops=from_ops,
                allow_uncorrelated_congruence_match=True,
            )
        elif segment.expr_type is Power:
            if segment.operand_index != 0 or len(segment.other_operands) != 1:
                return None
            exponent = segment.other_operands[0]
            minus_one = mutator.make_singleton(-1.0).can_be_operand.get()
            inv_exp_result = mutator.create_check_and_insert_expression(
                Power,
                exponent,
                minus_one,
                from_ops=from_ops,
            )
            inv_exp = not_none(_insert_result_operand(inv_exp_result))

            expr_out = _insert_expression_with_alias(
                mutator,
                Power,
                current,
                inv_exp,
                alias=alias,
                from_ops=from_ops,
                allow_uncorrelated_congruence_match=True,
            )
        else:
            return None

        if expr_out is None:
            return None

        return _alias_is_for_expression(expr_out, alias, mutator=mutator)

    return None


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
            neg_operands.append(not_none(_insert_result_operand(neg_result)))

        add_result = mutator.create_check_and_insert_expression(
            Add,
            current,
            *neg_operands,
            from_ops=from_ops,
        )
        return not_none(_insert_result_operand(add_result))

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
            inv_operands.append(not_none(_insert_result_operand(inv_result)))

        mul_result = mutator.create_check_and_insert_expression(
            Multiply,
            current,
            *inv_operands,
            from_ops=from_ops,
        )
        return not_none(_insert_result_operand(mul_result))

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
                not_none(_insert_result_operand(inv_exp_result)),
                from_ops=from_ops,
            )
            return not_none(_insert_result_operand(pow_result))
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

    if len(operands) < 2:
        return RewriteResult.CANNOT_ISOLATE
    left, right = operands[0], operands[1]

    # Step 1: Determine which side to rewrite.
    #
    # If the Is! is a representative link (exactly one expression operand, exactly
    # one parameter operand), rewrite from the expression side. The parameter
    # side must not be expanded through this same Is!, otherwise every variable
    # inside the expression would appear on both sides and we would block valid
    # isolation (e.g. (A+B) is! C -> A is! (C-B)).
    expr_ops = list(expr.get_operands_with_trait(F.Expressions.is_expression))
    param_ops = list(expr.get_operands_with_trait(F.Parameters.is_parameter))

    # Multi-operand Is!: treat this as an n-ary equality class. Prefer rewriting
    # between *expression* operands, and ignore representative parameters that
    # may also be present in the class.
    if len(expr_ops) >= 2:
        var_expr_ops = [op for op in expr_ops if _contains_variable(op.as_operand.get(), variable)]
        if len(var_expr_ops) != 1:
            return RewriteResult.CANNOT_ISOLATE
        var_side = var_expr_ops[0].as_operand.get()

        other_candidates = [
            op.as_operand.get()
            for op in expr_ops
            if op is not var_expr_ops[0]
            and not _contains_variable(op.as_operand.get(), variable)
        ]
        if not other_candidates:
            return RewriteResult.CANNOT_ISOLATE
        other_side = other_candidates[0]

    elif len(expr_ops) == 1 and len(param_ops) == 1 and len(operands) == 2:
        expr_side = next(iter(expr_ops)).as_operand.get()
        rep_side = next(iter(param_ops)).as_operand.get()

        # If the requested variable is the representative parameter itself, it
        # is already isolated.
        if (
            (var_op := variable.as_operand.get())
            and var_op.is_same(rep_side, allow_different_graph=True)
        ):
            return RewriteResult.ALREADY_ISOLATED

        if not _contains_variable(expr_side, variable):
            return RewriteResult.CANNOT_ISOLATE

        var_side = expr_side
        other_side = rep_side
    else:
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
    alias_param = variable.as_parameter.try_get()
    if alias_param is None:
        return RewriteResult.CANNOT_ISOLATE
    out_is = _apply_inverse_operations_alias_to_variable(
        mutator, other_side, path, from_ops, alias=alias_param
    )
    if out_is is None:
        return RewriteResult.CANNOT_ISOLATE

    return out_is


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
            [
                Mutator,
                dict[str, F.Parameters.can_be_operand],
                Is,
                F.Parameters.is_parameter_operatable,
            ],
            F.Parameters.can_be_operand,
        ]
        | None
    ) = None
    # Expected result type for non-success cases
    expected_result: RewriteResult | None = None
    assert_input: bool = False
    failure_reason: str | None = None


def _build_expected_add_isolate_first(
    m: Mutator,
    p: dict[str, F.Parameters.can_be_operand],
    _canon_is: Is,
    _target_var: F.Parameters.is_parameter_operatable,
) -> F.Parameters.can_be_operand:
    """A + B is C, isolate A -> A is C + (B * -1)"""
    neg_b = not_none(
        _insert_result_operand(
            m.create_check_and_insert_expression(
                Multiply,
                m.get_copy(p["B"]),
                m.make_singleton(-1.0).can_be_operand.get(),
                allow_uncorrelated_congruence_match=True,
            )
        )
    )
    res = m.create_check_and_insert_expression(
        Add,
        m.get_copy(p["C"]),
        neg_b,
        allow_uncorrelated_congruence_match=True,
    )
    return not_none(res.out).as_operand.get()


def _build_expected_add_isolate_second(
    m: Mutator,
    p: dict[str, F.Parameters.can_be_operand],
    _canon_is: Is,
    _target_var: F.Parameters.is_parameter_operatable,
) -> F.Parameters.can_be_operand:
    """A + B is C, isolate B -> B is C + (A * -1)"""
    neg_a = not_none(
        _insert_result_operand(
            m.create_check_and_insert_expression(
                Multiply,
                m.get_copy(p["A"]),
                m.make_singleton(-1.0).can_be_operand.get(),
                allow_uncorrelated_congruence_match=True,
            )
        )
    )
    res = m.create_check_and_insert_expression(
        Add,
        m.get_copy(p["C"]),
        neg_a,
        allow_uncorrelated_congruence_match=True,
    )
    return not_none(res.out).as_operand.get()


def _build_expected_multiply_isolate(
    m: Mutator,
    p: dict[str, F.Parameters.can_be_operand],
    _canon_is: Is,
    _target_var: F.Parameters.is_parameter_operatable,
) -> F.Parameters.can_be_operand:
    """A * B is C, isolate A -> A is C * (B ^ -1)"""
    inv_b = not_none(
        _insert_result_operand(
            m.create_check_and_insert_expression(
                Power,
                m.get_copy(p["B"]),
                m.make_singleton(-1.0).can_be_operand.get(),
                allow_uncorrelated_congruence_match=True,
            )
        )
    )
    res = m.create_check_and_insert_expression(
        Multiply,
        m.get_copy(p["C"]),
        inv_b,
        allow_uncorrelated_congruence_match=True,
    )
    return not_none(res.out).as_operand.get()


def _build_expected_power_base_isolate(
    m: Mutator,
    p: dict[str, F.Parameters.can_be_operand],
    _canon_is: Is,
    _target_var: F.Parameters.is_parameter_operatable,
) -> F.Parameters.can_be_operand:
    """A ^ 2 is B, isolate A -> A is B ^ 0.5"""
    # Note: 2^-1 may be folded to 0.5 literal
    res = m.create_check_and_insert_expression(
        Power,
        m.get_copy(p["B"]),
        m.make_singleton(0.5).can_be_operand.get(),
        allow_uncorrelated_congruence_match=True,
    )
    return not_none(res.out).as_operand.get()


def _build_expected_lit_factor_isolate(
    m: Mutator,
    p: dict[str, F.Parameters.can_be_operand],
    _canon_is: Is,
    _target_var: F.Parameters.is_parameter_operatable,
) -> F.Parameters.can_be_operand:
    """A * 2 is B, isolate A -> A is B * 0.5"""
    res = m.create_check_and_insert_expression(
        Multiply,
        m.get_copy(p["B"]),
        m.make_singleton(0.5).can_be_operand.get(),
        allow_uncorrelated_congruence_match=True,
    )
    return not_none(res.out).as_operand.get()


def _build_expected_nested(
    m: Mutator,
    p: dict[str, F.Parameters.can_be_operand],
    canon_is: Is,
    target_var: F.Parameters.is_parameter_operatable,
) -> F.Parameters.can_be_operand:
    """X + (Y * A) is (B + C), isolate B -> B is (X + (Y * A)) + (C * -1)"""
    expr_ops = list(
        canon_is.is_expression.get().get_operands_with_trait(F.Expressions.is_expression)
    )
    assert len(expr_ops) >= 2
    var_exprs = [
        e for e in expr_ops if _contains_variable(e.as_operand.get(), target_var)
    ]
    assert len(var_exprs) == 1
    other_expr = next(e for e in expr_ops if e is not var_exprs[0])
    other_rep_in = AliasClass.of(
        other_expr.as_operand.get(), allow_non_repr=True
    ).representative()
    other_rep = m.get_copy(other_rep_in)
    # Build (C * -1)
    neg_c = not_none(
        _insert_result_operand(
            m.create_check_and_insert_expression(
                Multiply,
                m.get_copy(p["C"]),
                m.make_singleton(-1.0).can_be_operand.get(),
                allow_uncorrelated_congruence_match=True,
            )
        )
    )
    # Combine
    res = m.create_check_and_insert_expression(
        Add,
        other_rep,
        neg_c,
        allow_uncorrelated_congruence_match=True,
    )
    return not_none(res.out).as_operand.get()


def _build_expected_add_isolate_second_side(
    m: Mutator,
    p: dict[str, F.Parameters.can_be_operand],
    _canon_is: Is,
    _target_var: F.Parameters.is_parameter_operatable,
) -> F.Parameters.can_be_operand:
    """(A + B) is (A + C), isolate B -> B is (A + C) + (A * -1)"""
    neg_a = not_none(
        _insert_result_operand(
            m.create_check_and_insert_expression(
                Multiply,
                m.get_copy(p["A"]),
                m.make_singleton(-1.0).can_be_operand.get(),
                allow_uncorrelated_congruence_match=True,
            )
        )
    )
    a_plus_c = not_none(
        _insert_result_operand(
            m.create_check_and_insert_expression(
                Add,
                m.get_copy(p["A"]),
                m.get_copy(p["C"]),
                allow_uncorrelated_congruence_match=True,
            )
        )
    )
    res = m.create_check_and_insert_expression(
        Add,
        a_plus_c,
        neg_a,
        allow_uncorrelated_congruence_match=True,
    )
    return not_none(res.out).as_operand.get()


def _build_expected_nary_add(
    m: Mutator,
    p: dict[str, F.Parameters.can_be_operand],
    _canon_is: Is,
    _target_var: F.Parameters.is_parameter_operatable,
) -> F.Parameters.can_be_operand:
    """A + B + C + D is E, isolate B -> B is E + (A * -1) + (C * -1) + (D * -1)"""
    neg_a = not_none(
        _insert_result_operand(
            m.create_check_and_insert_expression(
                Multiply,
                m.get_copy(p["A"]),
                m.make_singleton(-1.0).can_be_operand.get(),
                allow_uncorrelated_congruence_match=True,
            )
        )
    )
    neg_c = not_none(
        _insert_result_operand(
            m.create_check_and_insert_expression(
                Multiply,
                m.get_copy(p["C"]),
                m.make_singleton(-1.0).can_be_operand.get(),
                allow_uncorrelated_congruence_match=True,
            )
        )
    )
    neg_d = not_none(
        _insert_result_operand(
            m.create_check_and_insert_expression(
                Multiply,
                m.get_copy(p["D"]),
                m.make_singleton(-1.0).can_be_operand.get(),
                allow_uncorrelated_congruence_match=True,
            )
        )
    )
    res = m.create_check_and_insert_expression(
        Add,
        m.get_copy(p["E"]),
        neg_a,
        neg_c,
        neg_d,
        allow_uncorrelated_congruence_match=True,
    )
    return not_none(res.out).as_operand.get()


def _build_expected_divide_isolate_denominator(
    m: Mutator,
    p: dict[str, F.Parameters.can_be_operand],
    _canon_is: Is,
    _target_var: F.Parameters.is_parameter_operatable,
) -> F.Parameters.can_be_operand:
    """
    A * B^(-1) is C, isolate B -> B is (C * A^(-1))^(-1)

    Math: A * B^(-1) = C  =>  B^(-1) = C * A^(-1)  =>  B = (C * A^(-1))^(-1)
    Note: (C * A^(-1))^(-1) = A * C^(-1) mathematically, but our algorithm
    produces the former structure.
    """
    # B^(-1) = C * A^(-1)
    inv_a = not_none(
        _insert_result_operand(
            m.create_check_and_insert_expression(
                Power,
                m.get_copy(p["A"]),
                m.make_singleton(-1.0).can_be_operand.get(),
                allow_uncorrelated_congruence_match=True,
            )
        )
    )
    c_div_a = not_none(
        _insert_result_operand(
            m.create_check_and_insert_expression(
                Multiply,
                m.get_copy(p["C"]),
                inv_a,
                allow_uncorrelated_congruence_match=True,
            )
        )
    )
    # B = (C * A^(-1))^(-1)
    res = m.create_check_and_insert_expression(
        Power,
        c_div_a,
        m.make_singleton(-1.0).can_be_operand.get(),
        allow_uncorrelated_congruence_match=True,
    )
    return not_none(res.out).as_operand.get()


def _build_expected_deeply_nested(
    m: Mutator,
    p: dict[str, F.Parameters.can_be_operand],
    _canon_is: Is,
    _target_var: F.Parameters.is_parameter_operatable,
) -> F.Parameters.can_be_operand:
    """((A + B) * C) + D is E, isolate A -> A is ((E + (D * -1)) * C^-1) + (B * -1)"""
    # Step 1: E + (D * -1)
    neg_d = not_none(
        _insert_result_operand(
            m.create_check_and_insert_expression(
                Multiply,
                m.get_copy(p["D"]),
                m.make_singleton(-1.0).can_be_operand.get(),
                allow_uncorrelated_congruence_match=True,
            )
        )
    )
    e_minus_d = not_none(
        _insert_result_operand(
            m.create_check_and_insert_expression(
                Add,
                m.get_copy(p["E"]),
                neg_d,
                allow_uncorrelated_congruence_match=True,
            )
        )
    )
    # Step 2: (E + (D * -1)) * C^-1
    inv_c = not_none(
        _insert_result_operand(
            m.create_check_and_insert_expression(
                Power,
                m.get_copy(p["C"]),
                m.make_singleton(-1.0).can_be_operand.get(),
                allow_uncorrelated_congruence_match=True,
            )
        )
    )
    divided_by_c = not_none(
        _insert_result_operand(
            m.create_check_and_insert_expression(
                Multiply,
                e_minus_d,
                inv_c,
                allow_uncorrelated_congruence_match=True,
            )
        )
    )
    # Step 3: ... + (B * -1)
    neg_b = not_none(
        _insert_result_operand(
            m.create_check_and_insert_expression(
                Multiply,
                m.get_copy(p["B"]),
                m.make_singleton(-1.0).can_be_operand.get(),
                allow_uncorrelated_congruence_match=True,
            )
        )
    )
    res = m.create_check_and_insert_expression(
        Add,
        divided_by_c,
        neg_b,
        allow_uncorrelated_congruence_match=True,
    )
    return not_none(res.out).as_operand.get()


TEST_CASES = [
    RewriteTestCase(
        name="add_isolate_first",
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
        name="add_isolate_second",
        setup=lambda E: (
            fabll.Traits(
                E.is_(
                    E.add(A := E.parameter_op(), B := E.parameter_op()),
                    C := E.parameter_op(),
                    assert_=True,
                )
            ).get_obj(Is),
            B.as_parameter_operatable.force_get(),
            {"A": A, "B": B, "C": C},
        ),
        expected_builder=_build_expected_add_isolate_second,
        assert_input=True,
    ),
    RewriteTestCase(
        name="multiply_isolate",
        setup=lambda E: (
            fabll.Traits(
                E.is_(
                    E.multiply(A := E.parameter_op(), B := E.parameter_op()),
                    C := E.parameter_op(),
                    assert_=True,
                )
            ).get_obj(Is),
            A.as_parameter_operatable.force_get(),
            {"A": A, "B": B, "C": C},
        ),
        expected_builder=_build_expected_multiply_isolate,
        assert_input=True,
    ),
    RewriteTestCase(
        name="power_base_isolate",
        setup=lambda E: (
            fabll.Traits(
                E.is_(
                    E.power(A := E.parameter_op(), E.lit_op_single(2.0)),
                    B := E.parameter_op(),
                    assert_=True,
                )
            ).get_obj(Is),
            A.as_parameter_operatable.force_get(),
            {"A": A, "B": B},
        ),
        expected_builder=_build_expected_power_base_isolate,
        assert_input=True,
    ),
    RewriteTestCase(
        name="lit_factor_isolate",
        setup=lambda E: (
            fabll.Traits(
                E.is_(
                    E.multiply(A := E.parameter_op(), E.lit_op_single(2.0)),
                    B := E.parameter_op(),
                    assert_=True,
                )
            ).get_obj(Is),
            A.as_parameter_operatable.force_get(),
            {"A": A, "B": B},
        ),
        expected_builder=_build_expected_lit_factor_isolate,
        assert_input=True,
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
                    assert_=True,
                )
            ).get_obj(Is),
            B.as_parameter_operatable.force_get(),
            {"X": X, "Y": Y, "A": A, "B": B, "C": C},
        ),
        expected_builder=_build_expected_nested,
        assert_input=True,
    ),
    RewriteTestCase(
        name="already_isolated",
        setup=lambda E: (
            fabll.Traits(
                E.is_(
                    A := E.parameter_op(),
                    E.add(B := E.parameter_op(), C := E.parameter_op()),
                    assert_=True,
                )
            ).get_obj(Is),
            A.as_parameter_operatable.force_get(),
            {"A": A, "B": B, "C": C},
        ),
        expected_result=RewriteResult.ALREADY_ISOLATED,
        assert_input=True,
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
                    assert_=True,
                )
            ).get_obj(Is),
            B.as_parameter_operatable.force_get(),
            {"A": A, "B": B, "C": C},
        ),
        expected_builder=_build_expected_add_isolate_second_side,
        assert_input=True,
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
                    assert_=True,
                )
            ).get_obj(Is),
            B.as_parameter_operatable.force_get(),
            {"A": A, "B": B, "C": C, "D": D, "E": EE},
        ),
        expected_builder=_build_expected_nary_add,
        assert_input=True,
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
                    assert_=True,
                )
            ).get_obj(Is),
            B.as_parameter_operatable.force_get(),
            {"A": A, "B": B, "C": C},
        ),
        expected_builder=_build_expected_divide_isolate_denominator,
        assert_input=True,
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
                    assert_=True,
                )
            ).get_obj(Is),
            A.as_parameter_operatable.force_get(),
            {"A": A, "B": B, "C": C, "D": D, "E": EE},
        ),
        expected_builder=_build_expected_deeply_nested,
        assert_input=True,
    ),
    # Note: literal_rhs test removed - Is expression cannot have literal operands
    # Failure cases
    RewriteTestCase(
        name="variable_not_found",
        setup=lambda E: (
            fabll.Traits(
                E.is_(
                    E.add(E.parameter_op(), E.parameter_op()),
                    E.parameter_op(),
                    assert_=True,
                )
            ).get_obj(Is),
            E.parameter_op().as_parameter_operatable.force_get(),
            {},
        ),
        expected_result=RewriteResult.CANNOT_ISOLATE,
        assert_input=True,
        failure_reason="variable not in expression",
    ),
    RewriteTestCase(
        name="variable_both_sides",
        setup=lambda E: (
            fabll.Traits(
                E.is_(
                    E.add(A := E.parameter_op(), E.parameter_op()),
                    E.add(A, E.parameter_op()),
                    assert_=True,
                )
            ).get_obj(Is),
            A.as_parameter_operatable.force_get(),
            {},
        ),
        expected_result=RewriteResult.CANNOT_ISOLATE,
        assert_input=True,
        failure_reason="variable on both sides",
    ),
    RewriteTestCase(
        name="variable_nonlinear",
        setup=lambda E: (
            fabll.Traits(
                E.is_(
                    E.add(
                        A := E.parameter_op(),
                        E.multiply(A, E.parameter_op()),
                    ),
                    E.parameter_op(),
                    assert_=True,
                ),
            ).get_obj(Is),
            A.as_parameter_operatable.force_get(),
            {},
        ),
        expected_result=RewriteResult.CANNOT_ISOLATE,
        assert_input=True,
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
        canon_is = fabll.Traits(canon_expr).get_obj(Is)

        # Run the rewrite
        result = rewrite_equation_for_variable(mutator, canon_is, target_var)

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
            expected = case.expected_builder(mutator, params, canon_is, target_var)

            def _sig(op: F.Parameters.can_be_operand, seen: set[int]) -> tuple:
                obj = fabll.Traits(op).get_obj_raw()
                uuid = obj.instance.node().get_uuid()
                if uuid in seen:
                    return ("cycle", uuid)
                seen.add(uuid)

                if lit := op.try_get_sibling_trait(F.Literals.is_literal):
                    return ("lit", lit.pretty_str())

                # Prefer expressions directly, else expand representative params to their aliased expr.
                if expr_t := op.try_get_sibling_trait(F.Expressions.is_expression):
                    expr_obj = fabll.Traits(expr_t).get_obj_raw()
                    type_name = expr_obj.get_type_name()
                    child_ops = expr_t.get_operands()
                    child_sigs = [_sig(c, seen) for c in child_ops]
                    if expr_t.try_get_sibling_trait(F.Expressions.is_commutative):
                        child_sigs = sorted(child_sigs, key=repr)
                    return ("expr", type_name, tuple(child_sigs))

                if op.try_get_sibling_trait(F.Parameters.is_parameter):
                    try:
                        exprs = AliasClass.of(op, allow_non_repr=True).get_with_trait(
                            F.Expressions.is_expression
                        )
                    except AssertionError:
                        exprs = set()
                    if len(exprs) == 1:
                        return _sig(next(iter(exprs)).as_operand.get(), seen)

                return ("op", uuid)

            assert _sig(other_side, set()) == _sig(expected, set()), (
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
