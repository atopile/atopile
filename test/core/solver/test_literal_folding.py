import io
import logging
import math
import sys
import warnings
from collections import defaultdict
from datetime import timedelta
from functools import partial, reduce
from math import inf
from operator import add, mul, pow, sub, truediv
from typing import Any, Callable, Iterable, NamedTuple

import pytest  # noqa: F401
import typer
from hypothesis import HealthCheck, Phase, example, given, settings
from hypothesis import strategies as st
from hypothesis.core import reproduce_failure  # noqa: F401
from hypothesis.errors import NonInteractiveExampleWarning
from hypothesis.strategies._internal.lazy import LazyStrategy
from rich.console import Console
from rich.table import Table

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
from faebryk.libs.test.times import Times
from faebryk.libs.units import Quantity
from faebryk.libs.util import ConfigFlag, ConfigFlagInt, groupby

logger = logging.getLogger(__name__)

NUM_STAT_EXAMPLES = ConfigFlagInt(
    "ST_NUMEXAMPLES",
    default=100,
    descr="Number of examples to run for statistics",
)
ENABLE_PROGRESS_TRACKING = ConfigFlag("ST_PROGRESS", default=False)

# TODO set to something reasonable again
ABS_UPPER_LIMIT = 1e4  # Terra/pico or inf
ABS_LOWER_LIMIT = 1e-6  # micro


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


ValueT = Quantity_Interval_Disjoint | Parameter | Arithmetic


class Filters(Namespace):
    @staticmethod
    def _unwrap_param(value: ValueT) -> Quantity_Interval_Disjoint:
        assert isinstance(value, ValueT)
        if isinstance(value, Parameter):
            return value.get_literal()
        elif isinstance(value, Arithmetic):
            return evaluate_expr(value)
        else:
            return value

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
    def within_limits(value: ValueT) -> bool:
        value = Filters._unwrap_param(value)
        return bool(
            (value.min_elem >= -ABS_UPPER_LIMIT or value.min_elem == -inf)
            and (value.max_elem <= ABS_UPPER_LIMIT or value.max_elem == inf)
        )

    @staticmethod
    def no_op_overflow(
        op: Callable[[Any, Any], Any],
    ):
        def f(values: tuple[ValueT, ValueT]) -> bool:
            return Filters.within_limits(
                op(
                    Filters._unwrap_param(values[0]),
                    Filters._unwrap_param(values[1]),
                )
            )

        return f

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
    @staticmethod
    def _numbers_with_limit(upper_limit: float, lower_limit: float):
        assert 0 <= lower_limit < 1
        ints = st.integers(
            min_value=int(-upper_limit),
            max_value=int(upper_limit),
        )

        def _floats(min_value: float, max_value: float):
            return st.floats(
                allow_nan=False,
                allow_infinity=False,
                min_value=min_value,
                max_value=max_value,
                allow_subnormal=False,
            )

        if lower_limit == 0:
            floats = _floats(-upper_limit, upper_limit)
        else:
            floats = st.one_of(
                _floats(lower_limit, upper_limit),
                _floats(-upper_limit, -lower_limit),
            )

        return st.one_of(ints, floats)

    numeric = _numbers_with_limit(ABS_UPPER_LIMIT, ABS_LOWER_LIMIT)

    small_numeric = _numbers_with_limit(1e2, 1e-1)

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

    @staticmethod
    def no_overflow_pairs(op: Callable[[Any, Any], Any]):
        return st.tuples(st_values.values, st_values.values).filter(
            Filters.no_op_overflow(op)
        )

    division_pairs = st.tuples(
        values, values.filter(Filters.does_not_cross_zero)
    ).filter(Filters.no_op_overflow(truediv))

    power_pairs = (
        st.tuples(values, small_values)
        .filter(Filters.is_valid_for_power)
        .filter(Filters.no_op_overflow(pow))
    )


class Extension(Namespace):
    @staticmethod
    def tuples(children: st.SearchStrategy[Any]) -> st.SearchStrategy[Any]:
        return st.tuples(children, children)

    @staticmethod
    def tuples_no_overflow(op: Callable[[Any, Any], Any]):
        def f(children: st.SearchStrategy[Any]) -> st.SearchStrategy[Any]:
            return st.tuples(children, children).filter(Filters.no_op_overflow(op))

        return f

    @staticmethod
    def single(children: st.SearchStrategy[Any]) -> st.SearchStrategy[Any]:
        return children

    @staticmethod
    def tuples_power(children: st.SearchStrategy[Any]) -> st.SearchStrategy[Any]:
        return (
            st.tuples(children, st_values.small_values)
            .filter(Filters.is_valid_for_power)
            .filter(Filters.no_op_overflow(pow))
        )

    @staticmethod
    def tuples_division(children: st.SearchStrategy[Any]) -> st.SearchStrategy[Any]:
        # TODO: exprs on the right side
        return st.tuples(
            children,
            st_values.values.filter(Filters.does_not_cross_zero),
        ).filter(Filters.no_op_overflow(truediv))

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
    ExprType(
        Builders.Multiply,
        st_values.no_overflow_pairs(mul),
        Extension.tuples_no_overflow(mul),
    ),
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

    @staticmethod
    def _extend_tree(children: st.SearchStrategy[Any]) -> st.SearchStrategy[Any]:
        return st.one_of(
            *[
                st.builds(expr_type.builder, expr_type.extension_strategy(children))
                for expr_type in EXPR_TYPES
            ]
        )

    # flat
    # op1(flat, flat) | flat
    # op2(op1 | flat, op1 | flat)
    trees = st.recursive(base=flat, extend=_extend_tree, max_leaves=20)


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
    if _track.count % 100 == 0:
        print(f"track: {_track.count}")
    return _track.count


@pytest.mark.not_in_ci
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


# TODO: rounding
@example(
    Divide(
        Divide(
            Sqrt(Add(lit(2))),
            lit(2),
        ),
        lit(710038921),
    )
)
@example(
    Add(
        Subtract(lit(-999_999_935_634), lit(-999_999_999_992)),
        Subtract(lit(-82408), lit(-999_998_999_993)),
    )
)
@example(
    Divide(
        Divide(
            Add(Sqrt(lit(2.0)), Subtract(lit(0), lit(0))),
            lit(891895568.0),
        ),
        lit(2.0),
    ),
)
@example(
    Subtract(
        Multiply(lit(-999_992_989_829), lit(-999_992_989_829)),
        Multiply(lit(-999_991_993_022), lit(-999_991_989_837)),
    )
)
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
        logger.error(f"Solver {solver_result} != {evaluated_expr} Literal")
        input()
        return
    logger.warning("PASSES")
    input()


@example(
    Divide(
        Add(
            Subtract(lit(0), lit(1)),
            Abs(lit(Range(-inf, inf))),
        ),
        lit(1),
    ),
)
@example(
    Add(
        lit(1),
        Abs(
            Add(p(Range(-inf, inf)), p(Range(-inf, inf))),
        ),
    ),
)
@example(
    Add(
        Sqrt(lit(1)),
        Abs(lit(Range(-inf, inf))),
    ),
)
@example(
    expr=Add(
        Add(lit(-999_999_950_000)),
        Subtract(lit(50000), lit(-999_997_650_001)),
    ),
)
@example(
    expr=Subtract(
        Add(
            Add(lit(0)),
            Subtract(
                Add(lit(0)),
                Add(lit(1)),
            ),
        ),
        Add(lit(1)),
    )
)
@example(
    expr=Subtract(
        Subtract(
            lit(1),
            lit(Range(-inf, inf)),
        ),
        Add(lit(0)),
    ),
)
@example(
    Subtract(
        Abs(p(Range(-inf, inf))),
        Abs(p(Range(-inf, inf))),
    )
)
@example(Subtract(Abs(p(Range(5, 6))), Abs(p(Range(5, 6)))))
@example(
    expr=Multiply(
        Sqrt(Sqrt(lit(2))),
        Sqrt(Sqrt(lit(2))),
    )
)
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


class Stats:
    singleton: "Stats | None" = None

    @classmethod
    def get(cls) -> "Stats":
        if Stats.singleton is None:
            Stats.singleton = cls()
        return Stats.singleton

    def __init__(self):
        self.exprs: dict[Arithmetic, set[str]] = defaultdict(set)
        self.events: dict[str, set[Arithmetic]] = defaultdict(set)
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

        all_exprs = [
            e
            for root in self.exprs
            for e in root.get_children(
                direct_only=False, types=Arithmetic, include_root=True
            )
        ]
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

    def event(self, name: str, expr: Arithmetic, terminal: bool = True):
        # from hypothesis.control import event
        # event(name)
        self.exprs[expr].add(name)
        self.events[name].add(expr)
        self.times.add(name)

        if terminal and len(self.exprs) % 1000 == 0:
            self.print()


@pytest.fixture
def cleanup_stats():
    # Workaround: for large repr generation of hypothesis strategies,
    # LimitedStrategy.__repr__ = lambda self: str(id(self))
    LazyStrategy.__repr__ = lambda self: str(id(self))

    yield
    Stats.get().finish()


@pytest.mark.slow
@pytest.mark.usefixtures("cleanup_stats")
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
    ./test/runpytest.sh  \
    -k "test_folding_statistics"
    ```
    """
    stats = Stats.get()
    stats.event("generate", expr, terminal=False)
    solver = DefaultSolver()
    root = Parameter(domain=Numbers(negative=True, zero_allowed=True, integer=False))
    root.alias_is(expr)

    try:
        evaluated_expr = evaluate_expr(expr)
        stats.event("evaluate", expr, terminal=False)
    except NotImplementedError:
        stats.event("not implemented in literals", expr)
        return
    except Exception as e:
        stats.event(f"error in literals: {type(e).__name__}", expr)
        return

    assert isinstance(evaluated_expr, Quantity_Interval_Disjoint)

    try:
        solver_result = solver.inspect_get_known_supersets(root)
        assert isinstance(solver_result, Quantity_Interval_Disjoint)
    except Contradiction:
        stats.event("contradiction", expr)
        return
    except TimeoutError:
        stats.event("timeout", expr)
        return
    except NotImplementedError:
        stats.event("not implemented in solver", expr)
        return
    except Exception as e:
        stats.event(f"exc {type(e).__name__}", expr)
        return

    if solver_result != evaluated_expr:
        try:
            deviation = solver_result.op_deviation_to(evaluated_expr, relative=True)
        except Exception as e:
            stats.event(f"incorrect {type(e).__name__}", expr)
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
