import io
import logging
import sys
import warnings
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from functools import partial
from math import inf
from typing import Any, Callable, Iterable

import pytest  # noqa: F401
import typer
from hypothesis import HealthCheck, Phase, example, given, settings
from hypothesis import strategies as st
from hypothesis.errors import NonInteractiveExampleWarning
from hypothesis.strategies._internal.lazy import LazyStrategy
from rich.console import Console
from rich.table import Table

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.core import Namespace
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.core.solver.utils import Contradiction
from faebryk.libs.test.boundexpressions import BoundExpressions
from faebryk.libs.test.times import Times
from faebryk.libs.util import (
    ConfigFlag,
    ConfigFlagInt,
    groupby,
    once,
)

logger = logging.getLogger(__name__)

Add = F.Expressions.Add
Subtract = F.Expressions.Subtract
Multiply = F.Expressions.Multiply
Divide = F.Expressions.Divide
Sqrt = F.Expressions.Sqrt
Power = F.Expressions.Power
Round = F.Expressions.Round
Abs = F.Expressions.Abs
Sin = F.Expressions.Sin
Log = F.Expressions.Log
Cos = F.Expressions.Cos
Floor = F.Expressions.Floor
Ceil = F.Expressions.Ceil
Min = F.Expressions.Min
Max = F.Expressions.Max

# Workaround: for large repr generation of hypothesis strategies,
LazyStrategy.__repr__ = lambda self: str(id(self))

NUM_EXAMPLES = ConfigFlagInt(
    "ST_NUMEXAMPLES",
    default=100,
    descr="Number of examples to run for fuzzer",
)
ENABLE_PROGRESS_TRACKING = ConfigFlag("ST_PROGRESS", default=False)
CATCH_EVALUATION_ERRORS = True

ABS_UPPER_LIMIT = 1e12  # Terra or inf
DIGITS_LOWER_LIMIT = 12  # pico
ABS_LOWER_LIMIT = 10**-DIGITS_LOWER_LIMIT
ALLOW_ROUNDING_ERROR = True
ALLOW_EVAL_ERROR = True


g: graph.GraphView = graph.GraphView.create()
tg: fbrk.TypeGraph = fbrk.TypeGraph.create(g=g)


def eval_pure_literal_expression(
    expr_type: type[F.Expressions.ExpressionNodes],
    operands: list[F.Parameters.can_be_operand],
) -> F.Literals.Numbers:
    """
    Evaluate a pure literal expression and return the number literal.

    Maps expression types to their corresponding Literals.Numbers operations.
    """
    print(f"expr_type: {expr_type}")
    print(f"operands: {operands}")
    operands_literals = []
    for op in operands:
        obj = fabll.Traits(op).get_obj_raw()
        # Check if it's a Numbers literal
        if num := obj.try_cast(F.Literals.Numbers):
            operands_literals.append(num)
            print(f"num: {num}")
        # Check if it's a nested expression - recursively evaluate
        elif expr_trait := obj.try_get_trait(F.Expressions.is_expression):
            nested_result = eval_pure_literal_expression(
                type(expr_trait.switch_cast()), expr_trait.get_operands()
            )
            print(f"nested_result: {nested_result}")
            operands_literals.append(nested_result)
        else:
            raise ValueError(f"Operand {obj} is neither a literal nor an expression")

    print(f"operands_literals: {operands_literals}")

    # Arithmetic operations (variadic/binary)
    if expr_type is Add:
        return F.Literals.Numbers.op_add_intervals(*operands_literals, g=g, tg=tg)
    elif expr_type is Subtract:
        return F.Literals.Numbers.op_subtract_intervals(*operands_literals, g=g, tg=tg)
    elif expr_type is Multiply:
        return F.Literals.Numbers.op_mul_intervals(*operands_literals, g=g, tg=tg)
    elif expr_type is Divide:
        return F.Literals.Numbers.op_div_intervals(*operands_literals, g=g, tg=tg)
    elif expr_type is Power:
        return F.Literals.Numbers.op_pow_intervals(*operands_literals, g=g, tg=tg)
    # # Unary operations
    elif expr_type is Sqrt:
        return operands_literals[0].op_sqrt(g=g, tg=tg)
    elif expr_type is Log:
        return operands_literals[0].op_log(g=g, tg=tg)
    elif expr_type is Sin:
        return operands_literals[0].op_sin(g=g, tg=tg)
    elif expr_type is Cos:
        return operands_literals[0].op_cos(g=g, tg=tg)
    elif expr_type is Abs:
        return operands_literals[0].op_abs(g=g, tg=tg)
    elif expr_type is Round:
        return operands_literals[0].op_round(g=g, tg=tg)
    elif expr_type is Floor:
        return operands_literals[0].op_floor(g=g, tg=tg)
    elif expr_type is Ceil:
        return operands_literals[0].op_ceil(g=g, tg=tg)
    # Variadic operations (currently disabled in EXPR_TYPES)
    elif expr_type is Min:
        raise NotImplementedError("Min not yet implemented in Literals.Numbers")
    elif expr_type is Max:
        raise NotImplementedError("Max not yet implemented in Literals.Numbers")
    else:
        raise NotImplementedError(f"Expression type {expr_type} not supported")


def lit(*values: float) -> F.Parameters.can_be_operand:
    if len(values) == 1:
        dimless = (
            F.Units.Dimensionless.bind_typegraph(tg=tg).create_instance(g=g).setup()
        )
        return (
            F.Literals.Numbers.bind_typegraph(tg=tg)
            .create_instance(g=g)
            .setup_from_singleton(value=values[0], unit=dimless.is_unit.get())
        ).can_be_operand.get()
    elif len(values) == 2:
        dimless = (
            F.Units.Dimensionless.bind_typegraph(tg=tg).create_instance(g=g).setup()
        )
        return (
            F.Literals.Numbers.bind_typegraph(tg=tg)
            .create_instance(g=g)
            .setup_from_min_max(
                min=values[0], max=values[1], unit=dimless.is_unit.get()
            )
        ).can_be_operand.get()
    else:
        raise ValueError(f"Expected 1 or 2 values, got {len(values)}")


def lit_op_single(val: float) -> F.Parameters.can_be_operand:
    dimless = F.Units.Dimensionless.bind_typegraph(tg=tg).create_instance(g=g).setup()
    return (
        F.Literals.Numbers.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup_from_singleton(value=val, unit=dimless.is_unit.get())
    ).can_be_operand.get()


def lit_op_range_op(
    *values: F.Parameters.can_be_operand,
) -> F.Parameters.can_be_operand:
    floats = [fabll.Traits(v).get_obj(F.Literals.Numbers).get_single() for v in values]
    return lit_op_range(*floats)


def lit_op_range(*values: float) -> F.Parameters.can_be_operand:
    lower, upper = sorted(values)
    dimless = F.Units.Dimensionless.bind_typegraph(tg=tg).create_instance(g=g).setup()
    return (
        F.Literals.Numbers.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup_from_min_max(
            min=lower,
            max=upper,
            unit=dimless.is_unit.get(),
        )
    ).can_be_operand.get()


def op(x: fabll.NodeT) -> F.Parameters.can_be_operand:
    return x.get_trait(F.Parameters.can_be_operand)


def p(val):
    return Builders.build_parameter(op(lit(val)))


class Builders(Namespace):
    @staticmethod
    def build_parameter(
        literal: F.Parameters.can_be_operand,
    ) -> F.Parameters.can_be_operand:
        E = BoundExpressions(g=g, tg=tg)
        p = E.parameter_op()

        F.Expressions.Is.from_operands(
            p,
            literal,
        )
        return p

    @staticmethod
    def operator(
        op: type[F.Expressions.ExpressionNodes],
    ) -> Callable[
        [Iterable[F.Parameters.can_be_operand] | F.Parameters.can_be_operand],
        F.Parameters.can_be_operand,
    ]:
        def f(
            operands: Iterable[F.Parameters.can_be_operand]
            | F.Parameters.can_be_operand,
        ) -> F.Parameters.can_be_operand:
            ops = operands if isinstance(operands, Iterable) else (operands,)

            for o in ops:
                assert isinstance(o, F.Parameters.can_be_operand)
            return op.c(*ops, g=g, tg=tg)

        # required for good falsifying examples from hypothesis
        f.__name__ = f"'{op.__name__}'"

        return f


class Filters(Namespace):
    @staticmethod
    def _decorator[
        T: Callable[[F.Parameters.can_be_operand], bool]
        | Callable[
            [F.Parameters.can_be_operand | Iterable[F.Parameters.can_be_operand]], bool
        ]
        | Callable[
            [tuple[F.Parameters.can_be_operand, F.Parameters.can_be_operand]], bool
        ]
    ](
        func: T,
    ) -> T:
        if not CATCH_EVALUATION_ERRORS:
            return func

        def _wrap(*args, **kwargs) -> bool:
            try:
                return func(*args, **kwargs)
            except Filters._EvaluationError:
                return False

        return _wrap  # type: ignore

    class _EvaluationError(Exception):
        pass

    @staticmethod
    def _unwrap_param(value: F.Parameters.can_be_operand) -> F.Literals.Numbers:
        # # TODO where is this coming from?
        # if isinstance(value, fabll.Range):
        #     return lit(value)
        assert isinstance(value, F.Parameters.can_be_operand)
        obj = fabll.Traits(value).get_obj_raw()
        if np := obj.try_cast(F.Parameters.NumericParameter):
            try:
                return np.force_extract_literal()
            except Exception as e:
                raise Filters._EvaluationError(e) from e
        elif expr := obj.try_get_trait(F.Expressions.is_expression):
            try:
                return fabll.Traits(expr.get_operand_literals()[0]).get_obj(
                    F.Literals.Numbers
                )
            except Exception as e:
                raise Filters._EvaluationError(e) from e
        else:
            return obj.cast(F.Literals.Numbers)

    @_decorator
    @staticmethod
    def is_negative(value: F.Parameters.can_be_operand) -> bool:
        lit = Filters._unwrap_param(value)
        return lit.get_max_value() < 0

    @_decorator
    @staticmethod
    def is_positive(value: F.Parameters.can_be_operand) -> bool:
        lit = Filters._unwrap_param(value)
        return lit.get_min_value() > 0

    @_decorator
    @staticmethod
    def is_fractional(value: F.Parameters.can_be_operand) -> bool:
        lit = Filters._unwrap_param(value)
        return not lit.is_integer()

    @_decorator
    @staticmethod
    def is_zero(value: F.Parameters.can_be_operand) -> bool:
        # no need for fancy isclose, already covered by impl
        lit = Filters._unwrap_param(value)
        return lit.get_min_value() == 0 and lit.get_max_value() == 0

    @_decorator
    @staticmethod
    def crosses_zero(value: F.Parameters.can_be_operand) -> bool:
        lit = Filters._unwrap_param(value)
        return lit.contains_value(0.0) or Filters.is_zero(value)

    @_decorator
    @staticmethod
    def does_not_cross_zero(value: F.Parameters.can_be_operand) -> bool:
        return not Filters.crosses_zero(value)

    @_decorator
    @staticmethod
    def not_empty(value: F.Parameters.can_be_operand) -> bool:
        lit = Filters._unwrap_param(value)
        return not lit.is_empty()

    @_decorator
    @staticmethod
    def within_limits(value: F.Parameters.can_be_operand) -> bool:
        lit = Filters._unwrap_param(value)
        if lit.is_empty():
            return False
        abs_lit = lit.op_abs(g=g, tg=tg)
        return bool(
            (
                abs_lit.get_max_value() <= ABS_UPPER_LIMIT
                or abs_lit.get_max_value() == inf
            )
            and abs_lit.get_min_value() >= ABS_LOWER_LIMIT
        )

    @_decorator
    @staticmethod
    def all_within_limits(
        values: Iterable[F.Parameters.can_be_operand] | F.Parameters.can_be_operand,
    ) -> bool:
        if isinstance(values, F.Parameters.can_be_operand):
            values = [values]
        return all(Filters.within_limits(v) for v in values)

    @staticmethod
    def no_op_overflow(op: type[F.Expressions.ExpressionNodes]):
        @Filters._decorator
        def f(
            values: Iterable[F.Parameters.can_be_operand] | F.Parameters.can_be_operand,
        ) -> bool:
            if isinstance(values, F.Parameters.can_be_operand):
                values = [values]
            lits = [Filters._unwrap_param(v) for v in values]
            try:
                expr = eval_pure_literal_expression(
                    op, [lit.can_be_operand.get() for lit in lits]
                )
            except Exception as e:
                raise Filters._EvaluationError(e) from e
            return Filters.within_limits(expr.can_be_operand.get())

        return f

    @_decorator
    @staticmethod
    def is_valid_for_power(
        pair: tuple[F.Parameters.can_be_operand, F.Parameters.can_be_operand],
    ) -> bool:
        base, exp = pair
        return (
            # nan/undefined
            not (Filters.crosses_zero(base) and not Filters.is_positive(exp))
            # TODO: complex
            and not (Filters.is_fractional(exp) and not Filters.is_positive(base))
            # TODO: not impl yet
            and not Filters.crosses_zero(exp)
        )


class st_values(Namespace):
    @staticmethod
    def _floats_with_limit(upper_limit: float, lower_limit: float):
        # assert 0 <= lower_limit < 1
        # ints = st.integers(
        #     min_value=int(-upper_limit),
        #     max_value=int(upper_limit),
        # )

        def _floats(min_value: float, max_value: float):
            return st.floats(
                allow_nan=False,
                allow_infinity=False,
                min_value=min_value,
                max_value=max_value,
                # TODO: do we need this?
                # places=DIGITS_LOWER_LIMIT,
            )

        if lower_limit == 0:
            floats = _floats(-upper_limit, upper_limit)
        else:
            floats = st.one_of(
                _floats(lower_limit, upper_limit),
                _floats(-upper_limit, -lower_limit),
            )

        return st.one_of(floats).map(lit)

    numeric = _floats_with_limit(ABS_UPPER_LIMIT, ABS_LOWER_LIMIT)

    small_numeric = _floats_with_limit(1e2, 1e-1)

    ranges = st.builds(
        lambda values: lit_op_range_op(*values),
        st.tuples(
            st.one_of(st.just(lit_op_single(-inf)), numeric),
            st.one_of(st.just(lit_op_single(inf)), numeric),
        ),
    )

    small_ranges = st.builds(
        lambda values: lit_op_range_op(*values),
        st.tuples(small_numeric, small_numeric),
    )

    quantities = st.one_of(numeric, ranges)

    small_quantities = st.one_of(small_numeric, small_ranges)

    parameters = st.builds(Builders.build_parameter, quantities)

    small_parameters = st.builds(Builders.build_parameter, small_quantities)

    values = st.one_of(quantities, parameters)

    positive_values = values.filter(Filters.is_positive)

    small_values = st.one_of(small_quantities, small_parameters)

    _short_lists = partial(st.lists, min_size=1, max_size=5)
    lists = _short_lists(values)

    pairs = st.tuples(values, values)

    division_pairs = st.tuples(values, values.filter(Filters.does_not_cross_zero))

    power_pairs = st.tuples(values, small_values).filter(Filters.is_valid_for_power)


class Extension(Namespace):
    @staticmethod
    def tuples(children: st.SearchStrategy[Any]) -> st.SearchStrategy[Any]:
        return st.tuples(children, children)

    @staticmethod
    def single(children: st.SearchStrategy[Any]) -> st.SearchStrategy[Any]:
        return children

    @staticmethod
    def tuples_power(children: st.SearchStrategy[Any]) -> st.SearchStrategy[Any]:
        return st.tuples(children, st_values.small_values).filter(
            Filters.is_valid_for_power
        )

    @staticmethod
    def tuples_division(children: st.SearchStrategy[Any]) -> st.SearchStrategy[Any]:
        # TODO: exprs on the right side
        return st.tuples(
            children,
            st_values.values.filter(Filters.does_not_cross_zero),
        )

    @staticmethod
    def single_positive(
        children: st.SearchStrategy[Any],
    ) -> st.SearchStrategy[Any]:
        return children.filter(Filters.is_positive)


@dataclass
class ExprType:
    op: type[F.Expressions.ExpressionNodes]
    _strategy: (
        st.SearchStrategy[F.Parameters.can_be_operand]
        | st.SearchStrategy[
            tuple[F.Parameters.can_be_operand, F.Parameters.can_be_operand]
        ]
        | st.SearchStrategy[list[F.Parameters.can_be_operand]]
    )
    _extension_strategy: Callable[
        [st.SearchStrategy[F.Parameters.can_be_operand]],
        st.SearchStrategy[F.Parameters.can_be_operand],
    ]
    check_overflow: bool = True
    disable: bool = False

    @property
    @once
    def builder(
        self,
    ) -> Callable[[F.Parameters.can_be_operand], F.Parameters.can_be_operand]:
        return Builders.operator(self.op)

    @property
    def strategy(self) -> st.SearchStrategy[F.Parameters.can_be_operand]:
        out = self._strategy
        if self.check_overflow:
            # TODO why would this be needed?
            out = out.filter(Filters.all_within_limits)
            out = out.filter(Filters.no_op_overflow(self.op))
        return out

    def extension_strategy(
        self, children: st.SearchStrategy[F.Parameters.can_be_operand]
    ) -> st.SearchStrategy[F.Parameters.can_be_operand]:
        out = self._extension_strategy(children)
        if self.check_overflow:
            out = out.filter(Filters.no_op_overflow(self.op))
        return out


EXPR_TYPES = [
    ExprType(Add, st_values.pairs, Extension.tuples, check_overflow=False),
    ExprType(Subtract, st_values.pairs, Extension.tuples, check_overflow=False),
    ExprType(Multiply, st_values.pairs, Extension.tuples),
    ExprType(Divide, st_values.division_pairs, Extension.tuples_division),
    ExprType(Sqrt, st_values.positive_values, Extension.single_positive),
    ExprType(Power, st_values.power_pairs, Extension.tuples_power),
    ExprType(Log, st_values.positive_values, Extension.single_positive),
    ExprType(Sin, st_values.values, Extension.single, check_overflow=False),
    ExprType(Cos, st_values.values, Extension.single, check_overflow=False),
    ExprType(Abs, st_values.values, Extension.single, check_overflow=False),
    ExprType(Round, st_values.values, Extension.single, check_overflow=False),
    ExprType(Floor, st_values.values, Extension.single, check_overflow=False),
    ExprType(Ceil, st_values.values, Extension.single, check_overflow=False),
    # TODO
    ExprType(Min, st_values.lists, Extension.tuples, disable=True),
    ExprType(Max, st_values.lists, Extension.tuples, disable=True),
]


# def test_no_forgotten_expr_types():
#     ops = {expr_type.op for expr_type in EXPR_TYPES}
#     import faebryk.core.parameter as P

#     all_arithmetic_ops = {
#         v
#         for k, v in vars(P).items()
#         if isinstance(v, type)
#         and issubclass(v, F.Expressions.is_expression)
#         and not issubclass(v, Functional)
#         and getattr(v, "__is_abstract__", False) is not v
#     }
#     assert ops == set(all_arithmetic_ops)


class st_exprs(Namespace):
    flat: st.SearchStrategy[F.Parameters.can_be_operand] = st.one_of(
        *[
            st.builds(expr_type.builder, expr_type.strategy)
            for expr_type in EXPR_TYPES
            if not expr_type.disable
        ]
    )

    @staticmethod
    def _extend_tree(
        children: st.SearchStrategy[F.Parameters.can_be_operand],
    ) -> st.SearchStrategy[F.Parameters.can_be_operand]:
        return st.one_of(
            *[
                st.builds(expr_type.builder, expr_type.extension_strategy(children))
                for expr_type in EXPR_TYPES
                if not expr_type.disable
            ]
        )

    # flat
    # op1(flat, flat) | flat
    # op2(op1 | flat, op1 | flat)
    trees = st.recursive(base=flat, extend=_extend_tree, max_leaves=20)


def evaluate_e_p_l(operand: F.Parameters.can_be_operand) -> F.Literals.Numbers:
    obj = fabll.Traits(operand).get_obj_raw()
    if np := obj.try_cast(F.Literals.Numbers):
        return np

    if p := obj.try_cast(F.Parameters.NumericParameter):
        return p.force_extract_literal()

    expr = operand.get_sibling_trait(F.Expressions.is_expression).switch_cast()

    print(f"expr: {expr}")
    return eval_pure_literal_expression(
        type(expr), expr.is_expression.get().get_operands()
    )


@given(st_exprs.trees)
@settings(deadline=timedelta(milliseconds=1000))
def test_can_evaluate_literals(expr: F.Parameters.can_be_operand):
    result = evaluate_e_p_l(expr)
    assert isinstance(result, F.Literals.Numbers)


def _track():
    if not bool(ENABLE_PROGRESS_TRACKING):
        return
    if not hasattr(_track, "count"):
        _track.count = 0
    _track.count += 1
    if _track.count % 100 == 0:
        print(f"track: {_track.count}")
    return _track.count


@given(st_exprs.trees)
@settings(
    deadline=None,  # timedelta(milliseconds=1000),
    max_examples=int(NUM_EXAMPLES),
    report_multiple_bugs=False,
    phases=(
        Phase.generate,
        Phase.reuse,
        Phase.explicit,
        Phase.target,
        Phase.shrink,
        # Phase.explain,
    ),
    suppress_health_check=[
        HealthCheck.data_too_large,
        HealthCheck.too_slow,
        HealthCheck.filter_too_much,
        HealthCheck.large_base_example,
    ],
    print_blob=True,
)
def test_discover_literal_folding(expr: F.Parameters.can_be_operand):
    """
    Disble xfail and
    run with:
    ```bash
    FBRK_ST_NUMEXAMPLES=10000 \
    FBRK_STIMEOUT=1 \
    FBRK_SMAX_ITERATIONS=10 \
    FBRK_SPARTIAL=n \
    FBRK_ST_PROGRESS=y \
    ./test/runpytest.sh -k "test_discover_literal_folding"
    ```
    """
    _track()
    solver = DefaultSolver()

    test_g = graph.GraphView.create()
    test_g.insert_subgraph(subgraph=tg.get_type_subgraph())
    test_expr = expr.copy_into(test_g)
    test_tg = test_expr.tg

    E = BoundExpressions(g=test_g, tg=test_tg)
    root = E.parameter_op()
    E.is_(root, test_expr, assert_=True)

    try:
        evaluated_expr = evaluate_e_p_l(test_expr)
    except Exception:
        if ALLOW_EVAL_ERROR:
            return
        raise

    solver.update_superset_cache(root)
    solver_result = solver.inspect_get_known_supersets(
        root.get_sibling_trait(F.Parameters.is_parameter)
    )

    assert isinstance(evaluated_expr, F.Literals.Numbers)
    assert isinstance(solver_result, F.Literals.Numbers)

    if ALLOW_ROUNDING_ERROR and solver_result != evaluated_expr:
        try:
            deviation_rel = evaluated_expr.op_deviation_to(
                solver_result, relative=True, g=test_g, tg=test_tg
            )
            return
        except Exception:
            pass
        else:
            assert deviation_rel < 0.01, f"Mismatch {evaluated_expr} != {solver_result}"

        deviation = evaluated_expr.op_deviation_to(
            solver_result, g=test_g, tg=test_tg
        ).get_single()
        assert deviation <= 1, f"Mismatch {solver_result} != {evaluated_expr}"
    else:
        assert solver_result == evaluated_expr


# Examples -----------------------------------------------------------------------------
# --------------------------------------------------------------------------------------
@given(st_exprs.trees)
@settings(
    deadline=None,  # timedelta(milliseconds=1000),
    report_multiple_bugs=False,
    phases=(
        # Phase.reuse,
        Phase.explicit,
        Phase.target,
        # Phase.shrink,
        # Phase.explain,
    ),
    suppress_health_check=[
        HealthCheck.data_too_large,
        HealthCheck.too_slow,
        HealthCheck.filter_too_much,
        HealthCheck.large_base_example,
    ],
    print_blob=False,
)
def debug_fix_literal_folding(expr: F.Parameters.can_be_operand):
    """
    Run with:
    ```bash
    FBRK_SPARTIAL=n
    FBRK_LOG_PICK_SOLVE=y
    FBRK_SLOG=y
    FBRK_SMAX_ITERATIONS=10
    FBRK_LOG_FMT=y
    python ./test/runtest.py -k "debug_fix_literal_folding"
    ```
    """
    solver = DefaultSolver()
    test_g = graph.GraphView.create()
    test_g.insert_subgraph(subgraph=tg.get_type_subgraph())
    test_expr = expr.copy_into(test_g)
    test_tg = test_expr.tg
    expr_ctx = BoundExpressions(g=test_g, tg=test_tg)
    root = expr_ctx.parameter_op()
    expr_ctx.is_(root, test_expr)

    logger.info(
        f"expr: {expr.get_sibling_trait(F.Parameters.is_parameter).compact_repr()}"
    )
    evaluated_expr = evaluate_e_p_l(test_expr)
    logger.info(f"evaluated_expr: {evaluated_expr}")

    solver.update_superset_cache(root)
    solver_result = solver.inspect_get_known_supersets(
        root.get_sibling_trait(F.Parameters.is_parameter)
    )

    assert isinstance(evaluated_expr, F.Literals.Numbers)
    correct = solver_result == evaluated_expr

    if not correct:
        logger.error(
            f"Failing expression: {
                test_expr.get_sibling_trait(F.Expressions.is_expression).compact_repr()
            }"
        )
        logger.error(f"Solver {solver_result} != {evaluated_expr} Literal")
        input()
        return
    logger.warning("PASSES")
    input()


@example(
    Log.c(
        Sin.c(
            Add.c(
                lit_op_single(0),
                lit_op_single(1),
            )
        )
    )
)
@example(
    Add.c(
        Add.c(lit_op_single(0), lit_op_single(0)),
        Sqrt.c(Cos.c(lit_op_single(0))),
    ),
)
@example(
    Divide.c(
        Divide.c(
            Add.c(
                Sqrt.c(lit_op_single(2.0)),
                Subtract.c(lit_op_single(0), lit_op_single(0)),
            ),
            lit_op_single(891895568.0),
        ),
        lit_op_single(2.0),
    ),
)
@example(
    Divide.c(
        Divide.c(
            Sqrt.c(Add.c(lit_op_single(2))),
            lit_op_single(2),
        ),
        lit_op_single(710038921),
    )
)
@example(
    Sin.c(
        Sin.c(
            Subtract.c(
                lit_op_single(1),
                lit_op_range(-inf, inf),
            ),
        ),
    ),
)
@example(
    Divide.c(
        Add.c(
            Subtract.c(lit_op_single(0), lit_op_single(1)),
            Abs.c(lit_op_range(-inf, inf)),
        ),
        lit_op_single(1),
    ),
)
@example(
    Add.c(
        lit_op_single(1),
        Abs.c(
            Add.c(
                lit_op_range(-inf, inf),
                lit_op_range(-inf, inf),
            ),
        ),
    ),
)
@example(
    Add.c(
        Sqrt.c(lit_op_single(1)),
        Abs.c(lit_op_range(-inf, inf)),
    ),
)
@example(
    expr=Add.c(
        Add.c(lit_op_single(-999_999_950_000)),
        Subtract.c(lit_op_single(50000), lit_op_single(-999_997_650_001)),
    ),
)
@example(
    expr=Subtract.c(
        Add.c(
            Add.c(lit_op_single(0)),
            Subtract.c(
                Add.c(lit_op_single(0)),
                Add.c(lit_op_single(1)),
            ),
        ),
        Add.c(lit_op_single(1)),
    )
)
@example(
    expr=Subtract.c(
        Subtract.c(
            lit_op_single(1),
            lit_op_range(-inf, inf),
        ),
        Add.c(lit_op_single(0)),
    ),
)
@example(
    Subtract.c(
        Abs.c(lit_op_range(-inf, inf)),
        Abs.c(lit_op_range(-inf, inf)),
    )
)
@example(
    Subtract.c(
        Abs.c(lit_op_range(5, 6)),
        Abs.c(lit_op_range(5, 6)),
    )
)
@example(
    expr=Multiply.c(
        Sqrt.c(Sqrt.c(lit_op_single(2))),
        Sqrt.c(Sqrt.c(lit_op_single(2))),
    )
)
@example(
    expr=Subtract.c(
        Round.c(lit_op_range(2, 10)),
        Round.c(lit_op_range(2, 10)),
    ),
)
@example(
    expr=Subtract.c(
        Round.c(
            Subtract.c(
                lit_op_single(0),
                lit_op_range(-999_999_999_905, -0.3333333333333333),
            ),
        ),
        Subtract.c(
            lit_op_single(-999_999_983_213),
            lit_op_range(-17297878, 999_999_992_070),
        ),
    ),
)
@example(Abs.c(Round.c(lit_op_range(-inf, inf))))
@example(
    expr=Divide.c(
        Divide.c(
            lit_op_single(0),
            lit_op_range(-1, -2.2250738585072014e-308),
        ),
        lit_op_range(-1, -2.2250738585072014e-308),
    ),
)
@example(
    Multiply.c(
        Add.c(lit_op_single(0)),
        Abs.c(lit_op_range(-inf, inf)),
    )
)
@example(Add.c(Add.c(lit_op_single(0)), Abs.c(lit_op_single(-1))))
@example(Abs.c(lit_op_single(-1)))
@example(
    expr=Round.c(
        Add.c(
            Abs.c(lit_op_single(0)),
            Round.c(lit_op_single(-1)),
        )
    )
)
@example(
    expr=Add.c(
        Add.c(lit_op_single(0)),
        Multiply.c(Add.c(lit_op_single(0)), Add.c(lit_op_single(0))),
    )
)
@example(expr=F.Expressions.Subtract.c(lit_op_single(1), lit_op_single(0))).via(
    "discovered failure"
)
# --------------------------------------------------------------------------------------
# @given(st_exprs.trees)
# @settings(
#     deadline=None,  # timedelta(milliseconds=1000),
#     max_examples=10000,
#     report_multiple_bugs=False,
#     phases=(
#         # Phase.reuse,
#         Phase.explicit,
#         Phase.target,
#         Phase.shrink,
#         Phase.explain,
#     ),
#     suppress_health_check=[
#         HealthCheck.data_too_large,
#         HealthCheck.too_slow,
#         HealthCheck.filter_too_much,
#         HealthCheck.large_base_example,
#     ],
#     print_blob=False,
# )
def test_regression_literal_folding(expr: F.Parameters.can_be_operand):
    solver = DefaultSolver()

    test_g = graph.GraphView.create()
    test_g.insert_subgraph(subgraph=tg.get_type_subgraph())

    print(f"expr: {expr}")
    print(f"expr type: {type(expr)}")
    print("Copying expression into graph...")
    # Get the expression node that owns the can_be_operand trait, then copy that
    expr_node = fabll.Traits(expr).get_obj_raw()
    test_expr_node = expr_node.copy_into(test_g)
    test_expr = test_expr_node.get_trait(F.Parameters.can_be_operand)
    test_tg = test_expr_node.tg
    E = BoundExpressions(g=test_g, tg=test_tg)
    root = E.parameter_op()
    E.is_(root, test_expr, assert_=True)

    print("Evaluating expression...")
    evaluated_expr = evaluate_e_p_l(test_expr)
    print(f"evaluated_expr: {evaluated_expr}")
    solver.update_superset_cache(root)
    print("Updating superset cache...")
    solver_result = solver.inspect_get_known_supersets(
        root.get_sibling_trait(F.Parameters.is_parameter)
    )

    # Debug printing
    print("=" * 70)
    print(f"Expression Type: {type(test_expr_node).__name__}")
    print(f"Expression:      {test_expr_node}")
    print("-" * 70)
    assert isinstance(evaluated_expr, F.Literals.Numbers)
    solver_result_num = fabll.Traits(solver_result).get_obj(F.Literals.Numbers)
    print(f"Solver Result:   {solver_result_num}")
    print(f"Test Evaluated:  {evaluated_expr}")
    match = solver_result.equals(evaluated_expr)
    print(f"Match: {match}")
    print("=" * 70)
    assert match, f"Solver: {solver_result_num} != Test: {evaluated_expr}"


class Stats:
    singleton: "Stats | None" = None

    @classmethod
    def get(cls) -> "Stats":
        if Stats.singleton is None:
            Stats.singleton = cls()
        return Stats.singleton

    def __init__(self):
        self.exprs: dict[F.Expressions.is_expression, set[str]] = defaultdict(set)
        self.events: dict[str, set[F.Expressions.is_expression]] = defaultdict(set)
        self.times = Times(multi_sample_strategy=Times.MultiSampleStrategy.ALL)
        self._total = self.times.context("total")
        self._total.__enter__()

    def print(self):
        table = Table(title="Statistics")
        table.add_column("Event", justify="left")
        table.add_column("Count", justify="right")
        table.add_column("%", justify="right")
        total = len(self.exprs)
        for name, exprs in self.events.items():
            count = len(exprs)
            percent = count / total
            table.add_row(name, str(count), f"{percent:.2%}")
        console = Console(record=True, file=io.StringIO())
        console.print(table)
        logger.info(console.export_text(styles=True))

        table = Table(title="Expressions")
        table.add_column("Type", justify="left")
        table.add_column("count", justify="right")

        # TODO is this correct to get tg like this?
        if not total:
            return
        tg = next(iter(self.exprs.keys())).tg
        all_exprs = fabll.Node.bind_typegraph(tg).nodes_of_type(
            F.Expressions.is_expression
        )
        expr_types = groupby(all_exprs, type)
        for expr_type, exprs_for_type in expr_types.items():
            table.add_row(expr_type.__name__, str(len(exprs_for_type)))
        console = Console(record=True, file=io.StringIO())
        console.print(table)
        logger.info(console.export_text(styles=True))

        logger.info(self.times)

    def finish(self):
        self._total.__exit__(None, None, None)
        self.print()
        self.singleton = None

    def event(
        self,
        name: str,
        expr: F.Expressions.is_expression,
        terminal: bool = True,
        exc: Exception | None = None,
    ):
        if exc:
            name = f"{name} {type(exc).__name__}"
        self.exprs[expr].add(name)
        self.events[name].add(expr)
        self.times.add(name)

        if terminal and len(self.exprs) % 1000 == 0:
            self.print()


@pytest.fixture
def cleanup_stats():
    yield
    Stats.get().finish()


@pytest.mark.slow
@pytest.mark.usefixtures("cleanup_stats")
@given(st_exprs.trees)
@settings(
    deadline=None,
    max_examples=int(NUM_EXAMPLES),
    phases=(
        Phase.generate,
        # Phase.reuse,
        # Phase.explicit,
        Phase.target,
        # Phase.shrink,
        # Phase.explain,
    ),
    suppress_health_check=[
        HealthCheck.data_too_large,
        HealthCheck.too_slow,
        HealthCheck.filter_too_much,
        HealthCheck.large_base_example,
    ],
)
def test_folding_statistics(expr: F.Expressions.is_expression):
    """
    Run with:
    ```bash
    FBRK_STIMEOUT=5 \
    FBRK_SPARTIAL=n \
    FBRK_SMAX_ITERATIONS=10 \
    ./test/runpytest.sh  \
    -k "test_folding_statistics"
    ```
    """
    stats = Stats.get()
    test_g = graph.GraphView.create()
    test_g.insert_subgraph(subgraph=tg.get_type_subgraph())
    test_expr = expr.copy_into(test_g)
    test_tg = test_expr.tg
    stats.event("generate", test_expr, terminal=False)
    solver = DefaultSolver()
    E = BoundExpressions(g=test_g, tg=test_tg)
    root = E.parameter_op()
    E.is_(root, test_expr.get_sibling_trait(F.Parameters.can_be_operand), assert_=True)

    try:
        evaluated_expr = evaluate_e_p_l(
            test_expr.get_sibling_trait(F.Parameters.can_be_operand)
        )
        stats.event("evaluate", test_expr, terminal=False)
    except NotImplementedError:
        stats.event("not implemented in literals", test_expr)
        return
    except Exception as e:
        stats.event("eval exc", test_expr, exc=e)
        return

    assert isinstance(evaluated_expr, F.Literals.Numbers)

    try:
        solver.update_superset_cache(root)
        solver_result = solver.inspect_get_known_supersets(
            root.get_sibling_trait(F.Parameters.is_parameter)
        )
        assert isinstance(solver_result, F.Literals.Numbers)
    except Contradiction:
        stats.event("contradiction", test_expr)
        return
    except TimeoutError:
        stats.event("timeout", test_expr)
        return
    except NotImplementedError:
        stats.event("not implemented in solver", test_expr)
        return
    except Exception as e:
        stats.event("exc", test_expr, exc=e)
        return

    if solver_result != evaluated_expr:
        try:
            deviation = solver_result.op_deviation_to(
                evaluated_expr, relative=True, g=g, tg=tg
            ).get_single()
        except Exception:
            deviation = solver_result.op_deviation_to(
                evaluated_expr, g=g, tg=tg
            ).get_single()
            if deviation <= 1:
                stats.event("incorrect <= 1 ", expr)
            else:
                stats.event("incorrect > 1 ", expr)
            return
        if deviation < 0.01:
            stats.event("incorrect <1% dev", expr)
        elif deviation < 0.1:
            stats.event("incorrect <10% dev", expr)
        else:
            stats.event("incorrect >10% dev", expr)
        return

    stats.event("correct", expr)


# DEBUG --------------------------------------------------------------------------------


def generate_exprs():
    from rich.console import Console
    from rich.markdown import Markdown

    console = Console()

    console.print(Markdown("# Expressions"))

    for _ in range(50):
        expr = st_exprs.trees.example()
        console.print(
            Markdown(
                "- "
                # TODO always po?
                + expr.as_parameter_operatable.force_get().compact_repr()
            )
        )


def evaluate_exprs():
    from rich.console import Console
    from rich.table import Table

    table = Table(title="Expression Evaluation Examples")
    table.add_column("Evaluated Result", justify="left")
    table.add_column("Original Expression", justify="left")

    for _ in range(50):
        expr = st_exprs.trees.example()

        try:
            result = evaluate_e_p_l(expr).pretty_str()
        except (NotImplementedError, OverflowError) as e:
            result = repr(e)

        table.add_row(
            str(result),
            # TODO is this always a po?
            expr.as_parameter_operatable.force_get().compact_repr(),
        )

    console = Console()
    console.print(table)


def main(target: str):
    warnings.filterwarnings("ignore", category=NonInteractiveExampleWarning)

    match target:
        case "evaluate":
            evaluate_exprs()
        case "generate":
            generate_exprs()
        case _:
            raise ValueError(f"Unknown command: {sys.argv[1]}")


if __name__ == "__main__":
    import typer

    from faebryk.libs.logging import setup_basic_logging

    # expr = F.Expressions.Log.c(
    #     F.Expressions.Sin.c(
    #         F.Expressions.Add.c(
    #             lit_op_single(1),
    #             lit_op_single(1),
    #         )
    #     )
    # )
    # expr = F.Expressions.Sin.c(
    #     F.Expressions.Add.c(
    #         lit_op_single(1),
    #         lit_op_single(1),
    #     )
    # )

    # expr = Sin.c(
    #     Sin.c(
    #         Subtract.c(
    #             lit_op_single(1),
    #             lit_op_range(-inf, inf),
    #         ),
    #     ),
    # )
    # expr = Sin.c(Sin.c(lit_op_range(-10, 10)))
    expr = Sin.c(lit_op_range(-1, 1))

    setup_basic_logging()
    typer.run(lambda: test_regression_literal_folding(expr))
