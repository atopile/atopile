import logging
import math
import sys
import warnings
from datetime import timedelta
from functools import partial, reduce
from math import inf
from operator import add, mul, pow, sub, truediv
from typing import Any, Callable, Iterable, NamedTuple

import pytest  # noqa: F401
import typer
from hypothesis import HealthCheck, Phase, example, given, settings
from hypothesis import strategies as st
from hypothesis.control import event
from hypothesis.core import reproduce_failure  # noqa: F401
from hypothesis.errors import NonInteractiveExampleWarning

from faebryk.core.core import Namespace
from faebryk.core.parameter import (
    Abs,
    Add,
    Arithmetic,
    Ceil,
    Cos,
    Differentiate,
    Divide,
    Floor,
    Integrate,
    Log,
    Max,
    Min,
    Multiply,
    Numbers,
    Parameter,
    Power,
    Round,
    Sin,
    Sqrt,
    Subtract,
)
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.core.solver.utils import Contradiction
from faebryk.libs.library.L import Range
from faebryk.libs.sets.numeric_sets import float_round
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval,
    Quantity_Interval_Disjoint,
)
from faebryk.libs.units import Quantity
from faebryk.libs.util import ConfigFlag, ConfigFlagInt

logger = logging.getLogger(__name__)

NUM_STAT_EXAMPLES = ConfigFlagInt(
    "ST_NUMEXAMPLES",
    default=100,
    descr="Number of examples to run for statistics",
)
ENABLE_PROGRESS_TRACKING = ConfigFlag("ST_PROGRESS", default=False)

# canonical operations:
# Add, Multiply, Power, Round, Abs, Sin, Log
# Or, Not
# Intersection, Union, SymmetricDifference
# IsSubset, Is, GreaterThan

# all operations:
# Add, Subtract, Multiply, Divide, Sqrt, Power, Log, Sin, Cos, Abs, Round, Floor, Ceil,
# Min, Max, Integrate, Differentiate
# And, Or, Not, Xor, Implies, IfThenElse
# Union, Intersection, Difference, SymmetricDifference
# LessThan, GreaterThan, LessOrEqual, GreaterOrEqual
# ISSubset, IsSuperset, Cardinality, Is


def lit(val) -> Quantity_Interval_Disjoint:
    return Quantity_Interval_Disjoint.from_value(val)


def p(val):
    return Builders.build_parameter(lit(val))


def abs_close(a: float | Quantity, b: float) -> bool:
    return math.isclose(a, b, abs_tol=1e-15)


class Builders(Namespace):
    @staticmethod
    def build_parameter(quantity) -> Parameter:
        p = Parameter(domain=Numbers(negative=True, zero_allowed=True, integer=False))
        p.alias_is(quantity)
        return p

    @staticmethod
    def operator(op: type[Arithmetic]) -> Callable[[Iterable[Any] | Any], Arithmetic]:
        def f(operands: Iterable[Any] | Any) -> Arithmetic:
            return op(*operands) if isinstance(operands, Iterable) else op(operands)

        # required for good falsifying examples from hypothesis
        f.__name__ = op.__name__

        return f

    # Arithmetic
    Add = operator(Add)
    Subtract = operator(Subtract)
    Multiply = operator(Multiply)
    Divide = operator(Divide)
    Sqrt = operator(Sqrt)
    Power = operator(Power)
    Log = operator(Log)
    Sin = operator(Sin)
    Cos = operator(Cos)
    Abs = operator(Abs)
    Round = operator(Round)
    Floor = operator(Floor)
    Ceil = operator(Ceil)
    Min = operator(Min)
    Max = operator(Max)
    Integrate = operator(Integrate)
    Differentiate = operator(Differentiate)


ValueT = Quantity_Interval_Disjoint | Parameter


class Filters(Namespace):
    @staticmethod
    def _unwrap_param(value: ValueT) -> Quantity_Interval_Disjoint:
        return value.get_literal() if isinstance(value, Parameter) else value

    @staticmethod
    def is_negative(value: ValueT) -> bool:
        value = Filters._unwrap_param(value)
        return value.max_elem < 0

    @staticmethod
    def is_positive(value: ValueT) -> bool:
        value = Filters._unwrap_param(value)
        return value.min_elem > 0

    @staticmethod
    def is_fractional(value: ValueT) -> bool:
        value = Filters._unwrap_param(value)
        return not value.min_elem.is_integer() or not value.max_elem.is_integer()

    @staticmethod
    def is_zero(value: ValueT) -> bool:
        value = Filters._unwrap_param(value)
        return abs_close(value.min_elem, 0) and abs_close(value.max_elem, 0)

    @staticmethod
    def crosses_zero(value: ValueT) -> bool:
        value = Filters._unwrap_param(value)
        return 0 in value or Filters.is_zero(value)

    @staticmethod
    def does_not_cross_zero(value: ValueT) -> bool:
        return not Filters.crosses_zero(value)

    @staticmethod
    def is_empty(value: ValueT) -> bool:
        value = Filters._unwrap_param(value)
        return value.is_empty()

    @staticmethod
    def is_valid_for_power(
        pair: tuple[ValueT, ValueT],
    ) -> bool:
        base, exp = pair
        return (
            # complex
            not (Filters.is_negative(base) and Filters.is_fractional(exp))
            # nan/undefined
            # TODO enable base crossing zero
            and not (Filters.crosses_zero(base) and Filters.crosses_zero(exp))
        )


class st_values(Namespace):
    numeric = st.one_of(
        # [pico, tera]
        st.integers(min_value=int(-1e12), max_value=int(1e12)),
        st.floats(
            allow_nan=False,
            allow_infinity=False,
            min_value=-1e12,
            max_value=1e12,
            allow_subnormal=False,
        ),
    )

    small_numeric = st.one_of(
        st.integers(min_value=-100, max_value=100),
        st.floats(
            allow_nan=False, allow_infinity=False, min_value=-10.0, max_value=10.0
        ),
    )

    ranges = st.builds(
        lambda values: Range(*sorted(values)),
        st.tuples(
            st.one_of(st.just(-inf), numeric),
            st.one_of(st.just(inf), numeric),
        ),
    )

    small_ranges = st.builds(
        lambda values: Range(*sorted(values)), st.tuples(small_numeric, small_numeric)
    )

    quantities = st.one_of(numeric, ranges).map(lit)

    small_quantities = st.one_of(small_numeric, small_ranges).map(lit)

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
        return st.tuples(children, st_values.values.filter(Filters.does_not_cross_zero))

    @staticmethod
    def single_positive(children: st.SearchStrategy[Any]) -> st.SearchStrategy[Any]:
        return children.filter(lambda child: Filters.is_positive(evaluate_expr(child)))


class ExprType(NamedTuple):
    builder: Callable[[Any], Arithmetic]
    strategy: st.SearchStrategy[Any]
    extension_strategy: Callable[[st.SearchStrategy[Any]], st.SearchStrategy[Any]]


EXPR_TYPES = [
    ExprType(Builders.Add, st_values.lists, Extension.tuples),
    ExprType(Builders.Subtract, st_values.pairs, Extension.tuples),
    ExprType(Builders.Multiply, st_values.lists, Extension.tuples),
    ExprType(Builders.Divide, st_values.division_pairs, Extension.tuples_division),
    ExprType(Builders.Sqrt, st_values.positive_values, Extension.single_positive),
    # ExprType(Builders.Power, st_values.power_pairs, Extension.tuples_power),
    ExprType(Builders.Log, st_values.positive_values, Extension.single_positive),
    # TODO: NotImplementedError('sin of interval not implemented yet')
    # ExprType(Builders.Sin, st_values.values, Extension.single),
    # ExprType(Builders.Cos, st_values.values, Extension.single),
    ExprType(Builders.Abs, st_values.values, Extension.single),
    # TODO: round, float, ceil can't handle inf
    ExprType(Builders.Round, st_values.values, Extension.single),
    # ExprType(Builders.Floor, st_values.values, Extension.single),
    # ExprType(Builders.Ceil, st_values.values, Extension.single),
    # ExprType(Builders.Min, st_values.lists, Extension.tuples),
    # ExprType(Builders.Max, st_values.lists, Extension.tuples),
    # ExprType(Builders.Integrate, st_values.lists, Extension.tuples),
    # ExprType(Builders.Differentiate, st_values.lists, Extension.tuples),
]


class st_exprs(Namespace):
    flat = st.one_of(
        *[st.builds(expr_type.builder, expr_type.strategy) for expr_type in EXPR_TYPES]
    )

    # flat
    # op1(flat, flat) | flat
    # op2(op1 | flat, op1 | flat)
    trees = st.recursive(
        flat,
        lambda children: st.one_of(
            *[
                st.builds(expr_type.builder, expr_type.extension_strategy(children))
                for expr_type in EXPR_TYPES
            ]
        ),
        max_leaves=20,
    )


def evaluate_expr(
    expr: Arithmetic | Quantity,
) -> Quantity_Interval_Disjoint:
    operator_map: dict[type[Arithmetic], Callable] = {
        Add: add,
        Subtract: sub,
        Multiply: mul,
        Divide: truediv,
        Sqrt: lambda x: pow(x, 0.5),
        Power: pow,
        Round: float_round,
        Abs: abs,
        Sin: lambda x: x.op_sin(),
        Log: lambda x: x.op_log(),
        Cos: lambda x: (x + math.pi / 2).op_sin(),
        Floor: lambda x: float_round(x - 0.5),
        Ceil: lambda x: float_round(x + 0.5),
        Min: min,
        Max: max,
    }

    match expr:
        # monoids
        case Add() | Multiply() | Min() | Max():
            operands = (evaluate_expr(operand) for operand in expr.operands)
            operator = operator_map[type(expr)]
            return reduce(operator, operands)
        # left/right-associative
        case Subtract() | Divide() | Power():
            operands = [evaluate_expr(operand) for operand in expr.operands]
            operator = operator_map[type(expr)]
            assert len(operands) == 2
            return operator(operands[0], operands[1])
        # unary
        case Sqrt() | Round() | Abs() | Sin() | Log() | Cos() | Floor() | Ceil():
            assert len(expr.operands) == 1
            operand = evaluate_expr(expr.operands[0])
            operator = operator_map[type(expr)]
            return operator(operand)
        case Quantity_Interval():
            # TODO: why are we getting these?
            return lit(expr)
        case Quantity_Interval_Disjoint():
            return expr
        case Parameter():
            return expr.get_literal()
        case _:
            raise ValueError(f"Unknown expression type: {type(expr)}")


@given(st_exprs.trees)
@settings(deadline=timedelta(milliseconds=1000))
def test_can_evaluate_literals(expr: Arithmetic):
    result = evaluate_expr(expr)
    assert isinstance(result, Quantity_Interval_Disjoint)


def _track():
    if not bool(ENABLE_PROGRESS_TRACKING):
        return
    if not hasattr(_track, "count"):
        _track.count = 0
    _track.count += 1
    if _track.count % 10 == 0:
        print(f"track: {_track.count}")
    return _track.count


@pytest.mark.xfail(reason="Still finds problems")
@given(st_exprs.trees)
@settings(
    deadline=None,  # timedelta(milliseconds=1000),
    max_examples=10000,
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
def test_discover_literal_folding(expr: Arithmetic):
    """
    Run with:
    ```bash
    FBRK_STIMEOUT=1 \
    FBRK_SMAX_ITERATIONS=10 \
    FBRK_SPARTIAL=n \
    FBRK_ST_PROGRESS=y \
    ./test/runpytest.sh -k "test_discover_literal_folding"
    ```
    """
    _track()
    solver = DefaultSolver()

    root = Parameter(domain=Numbers(negative=True, zero_allowed=True, integer=False))
    root.alias_is(expr)

    evaluated_expr = evaluate_expr(expr)

    solver_result = solver.inspect_get_known_supersets(root)

    assert isinstance(evaluated_expr, Quantity_Interval_Disjoint)
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
def debug_fix_literal_folding(expr: Arithmetic):
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

    root = Parameter(domain=Numbers(negative=True, zero_allowed=True, integer=False))
    root.alias_is(expr)

    logger.info(f"expr: {expr.compact_repr()}")
    evaluated_expr = evaluate_expr(expr)
    logger.info(f"evaluated_expr: {evaluated_expr}")

    solver_result = solver.inspect_get_known_supersets(root)

    assert isinstance(evaluated_expr, Quantity_Interval_Disjoint)
    correct = solver_result == evaluated_expr

    if not correct:
        logger.error(f"Failing expression: {expr.compact_repr()}")
        logger.error(f"{solver_result} != {evaluated_expr}")
        input()
        return
    logger.warning("PASSES")
    input()


@example(
    expr=Subtract(
        Round(lit(Range(2, 10))),
        Round(lit(Range(2, 10))),
    ),
)
@example(
    expr=Subtract(
        Round(
            Subtract(
                lit(0),
                lit(Range(-999_999_999_905, -0.3333333333333333)),
            ),
        ),
        Subtract(
            lit(-999_999_983_213),
            p(Range(-17297878, 999_999_992_070)),
        ),
    ),
)
@example(Abs(Round(lit(Range(-inf, inf)))))
@example(
    expr=Divide(
        Divide(
            lit(0),
            lit(Range(-1, -2.2250738585072014e-308)),
        ),
        lit(Range(-1, -2.2250738585072014e-308)),
    ),
)
@example(Multiply(Add(lit(0)), Abs(lit(Range(-inf, inf)))))
@example(Add(Add(lit(0)), Abs(p(-1))))
@example(Abs(p(-1)))
@example(
    Add(
        Sqrt(lit(1)),
        Abs(lit(Range(-inf, inf))),
    ),
)
@example(expr=Round(Add(Abs(lit(0)), Round(lit(-1)))))
@example(
    expr=Add(
        Add(lit(0)),
        Multiply(Add(lit(0)), Add(lit(0))),
    )
)
@example(expr=Subtract(lit(1), lit(0))).via("discovered failure")
# --------------------------------------------------------------------------------------
@given(st_exprs.trees)
@settings(
    deadline=None,  # timedelta(milliseconds=1000),
    max_examples=10000,
    report_multiple_bugs=False,
    phases=(
        # Phase.reuse,
        Phase.explicit,
        Phase.target,
        Phase.shrink,
        Phase.explain,
    ),
    suppress_health_check=[
        HealthCheck.data_too_large,
        HealthCheck.too_slow,
        HealthCheck.filter_too_much,
        HealthCheck.large_base_example,
    ],
    print_blob=False,
)
def test_regression_literal_folding(expr: Arithmetic):
    solver = DefaultSolver()

    root = Parameter(domain=Numbers(negative=True, zero_allowed=True, integer=False))
    root.alias_is(expr)

    evaluated_expr = evaluate_expr(expr)

    solver_result = solver.inspect_get_known_supersets(root)

    assert isinstance(evaluated_expr, Quantity_Interval_Disjoint)
    assert solver_result == evaluated_expr


@pytest.mark.slow
@given(st_exprs.trees)
@settings(
    deadline=None,
    max_examples=int(NUM_STAT_EXAMPLES),
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
def test_folding_statistics(expr: Arithmetic):
    """
    Run with:
    ```bash
    FBRK_STIMEOUT=5 \
    FBRK_SPARTIAL=n \
    FBRK_SMAX_ITERATIONS=10 \
    ./test/runpytest.sh -Wignore --hypothesis-show-statistics \
      -k "test_folding_statistics" | grep -v Retried | grep -v "invalid because"
    ```
    """

    event("start")
    solver = DefaultSolver()
    root = Parameter(domain=Numbers(negative=True, zero_allowed=True, integer=False))
    root.alias_is(expr)

    try:
        evaluated_expr = evaluate_expr(expr)
    except NotImplementedError:
        event("not implemented in literals")
        return
    except Exception as e:
        event(f"error in literals: {type(e).__name__}")
        return

    assert isinstance(evaluated_expr, Quantity_Interval_Disjoint)

    try:
        solver_result = solver.inspect_get_known_supersets(root)
    except Contradiction:
        event("contradiction")
        return
    except TimeoutError:
        event("timeout")
        return
    except NotImplementedError:
        event("not implemented in solver")
        return
    except Exception as e:
        event(f"error in solver: {type(e).__name__}")
        return

    if solver_result != evaluated_expr:
        event("incorrect")
        return

    event("correct")


# DEBUG --------------------------------------------------------------------------------


def generate_exprs():
    from rich.console import Console
    from rich.markdown import Markdown

    console = Console()

    console.print(Markdown("# Expressions"))

    for _ in range(50):
        expr = st_exprs.trees.example()
        console.print(Markdown("- " + expr.compact_repr()))


def evaluate_exprs():
    from rich.console import Console
    from rich.table import Table

    table = Table(title="Expression Evaluation Examples")
    table.add_column("Evaluated Result", justify="left")
    table.add_column("Original Expression", justify="left")

    for _ in range(50):
        expr = st_exprs.trees.example()

        try:
            result = evaluate_expr(expr)
        except (NotImplementedError, OverflowError) as e:
            result = repr(e)

        table.add_row(str(result), expr.compact_repr())

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
    typer.run(main)
