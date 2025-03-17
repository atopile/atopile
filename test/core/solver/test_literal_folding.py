import io
import logging
import sys
import warnings
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from functools import partial, reduce
from math import inf
from operator import add, mul, pow, sub, truediv
from typing import Any, Callable, Iterable

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
from faebryk.core.graph import GraphFunctions
from faebryk.core.parameter import (
    Abs,
    Add,
    Arithmetic,
    Ceil,
    Cos,
    Divide,
    Floor,
    Functional,
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
from faebryk.core.solver.utils import Contradiction, get_graphs
from faebryk.libs.library.L import Range
from faebryk.libs.sets.numeric_sets import float_round
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval,
    Quantity_Interval_Disjoint,
)
from faebryk.libs.test.times import Times
from faebryk.libs.units import Quantity
from faebryk.libs.util import ConfigFlag, ConfigFlagInt, groupby, once

logger = logging.getLogger(__name__)

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


operator_map: dict[type[Arithmetic], Callable] = {
    Add: add,
    Subtract: sub,
    Multiply: mul,
    Divide: truediv,
    Sqrt: lambda x: x.op_sqrt(),
    Power: pow,
    Round: float_round,
    Abs: abs,
    Sin: lambda x: x.op_sin(),
    Log: lambda x: x.op_log(),
    Cos: lambda x: x.op_cos(),
    Floor: lambda x: x.op_floor(),
    Ceil: lambda x: x.op_ceil(),
    Min: min,
    Max: max,
}


def lit(val) -> Quantity_Interval_Disjoint:
    return Quantity_Interval_Disjoint.from_value(val)


def p(val):
    return Builders.build_parameter(lit(val))


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
        f.__name__ = f"'{op.__name__}'"

        return f


ValueT = Quantity_Interval_Disjoint | Parameter | Arithmetic


class Filters(Namespace):
    @staticmethod
    def _decorator[
        T: Callable[[ValueT], bool]
        | Callable[[ValueT | Iterable[ValueT]], bool]
        | Callable[[tuple[ValueT, ValueT]], bool]
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
    def _unwrap_param(value: ValueT) -> Quantity_Interval_Disjoint:
        # TODO where is this coming from?
        if isinstance(value, Range):
            return lit(value)
        assert isinstance(value, ValueT)
        if isinstance(value, Parameter):
            return value.get_literal()
        elif isinstance(value, Arithmetic):
            try:
                return evaluate_expr(value)
            except Exception as e:
                raise Filters._EvaluationError(e) from e
        else:
            return value

    @_decorator
    @staticmethod
    def is_negative(value: ValueT) -> bool:
        lit = Filters._unwrap_param(value)
        return lit.max_elem < 0

    @_decorator
    @staticmethod
    def is_positive(value: ValueT) -> bool:
        lit = Filters._unwrap_param(value)
        return lit.min_elem > 0

    @_decorator
    @staticmethod
    def is_fractional(value: ValueT) -> bool:
        lit = Filters._unwrap_param(value)
        return not lit.is_integer

    @_decorator
    @staticmethod
    def is_zero(value: ValueT) -> bool:
        # no need for fancy isclose, already covered by impl
        lit = Filters._unwrap_param(value)
        return lit == 0

    @_decorator
    @staticmethod
    def crosses_zero(value: ValueT) -> bool:
        lit = Filters._unwrap_param(value)
        return 0 in lit or Filters.is_zero(lit)

    @_decorator
    @staticmethod
    def does_not_cross_zero(value: ValueT) -> bool:
        return not Filters.crosses_zero(value)

    @_decorator
    @staticmethod
    def not_empty(value: ValueT) -> bool:
        lit = Filters._unwrap_param(value)
        return not lit.is_empty()

    @_decorator
    @staticmethod
    def within_limits(value: ValueT) -> bool:
        lit = Filters._unwrap_param(value)
        abs_lit = abs(lit)
        return bool(
            (abs_lit.max_elem <= ABS_UPPER_LIMIT or abs_lit.max_elem == inf)
            and abs_lit.min_elem >= ABS_LOWER_LIMIT
        )

    @_decorator
    @staticmethod
    def all_within_limits(values: Iterable[ValueT] | ValueT) -> bool:
        if isinstance(values, ValueT):
            values = [values]
        return all(Filters.within_limits(v) for v in values)

    @staticmethod
    def no_op_overflow(op: Callable):
        @Filters._decorator
        def f(values: Iterable[ValueT] | ValueT) -> bool:
            if isinstance(values, ValueT):
                values = [values]
            lits = [Filters._unwrap_param(v) for v in values]
            try:
                expr = op(*lits)
            except Exception as e:
                raise Filters._EvaluationError(e) from e
            return Filters.within_limits(expr)

        return f

    @_decorator
    @staticmethod
    def is_valid_for_power(
        pair: tuple[ValueT, ValueT],
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
    def _numbers_with_limit(upper_limit: float, lower_limit: float):
        assert 0 <= lower_limit < 1
        ints = st.integers(
            min_value=int(-upper_limit),
            max_value=int(upper_limit),
        )

        def _floats(min_value: float, max_value: float):
            return st.decimals(
                allow_nan=False,
                allow_infinity=False,
                min_value=min_value,
                max_value=max_value,
                places=DIGITS_LOWER_LIMIT,
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
        lambda values: lit(Range(*sorted(values))),
        st.tuples(
            st.one_of(st.just(-inf), numeric),
            st.one_of(st.just(inf), numeric),
        ),
    )

    small_ranges = st.builds(
        lambda values: lit(Range(*sorted(values))),
        st.tuples(small_numeric, small_numeric),
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
    op: type[Arithmetic]
    _strategy: st.SearchStrategy[Any]
    _extension_strategy: Callable[[st.SearchStrategy[Any]], st.SearchStrategy[Any]]
    check_overflow: bool = True
    disable: bool = False

    @property
    @once
    def builder(self) -> Callable[[Any], Arithmetic]:
        return Builders.operator(self.op)

    @property
    def operator(self) -> Callable[[Any, Any], Any]:
        return operator_map[self.op]

    @property
    def strategy(self) -> st.SearchStrategy[Any]:
        out = self._strategy
        if self.check_overflow:
            # TODO why would this be needed?
            out = out.filter(Filters.all_within_limits)
            out = out.filter(Filters.no_op_overflow(self.operator))
        return out

    def extension_strategy(
        self, children: st.SearchStrategy[Any]
    ) -> st.SearchStrategy[Any]:
        out = self._extension_strategy(children)
        if self.check_overflow:
            out = out.filter(Filters.no_op_overflow(self.operator))
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


def test_no_forgotten_expr_types():
    ops = {expr_type.op for expr_type in EXPR_TYPES}
    import faebryk.core.parameter as P

    all_arithmetic_ops = {
        v
        for k, v in vars(P).items()
        if isinstance(v, type)
        and issubclass(v, Arithmetic)
        and not issubclass(v, Functional)
        and getattr(v, "__is_abstract__", False) is not v
    }
    assert ops == set(all_arithmetic_ops)


class st_exprs(Namespace):
    flat = st.one_of(
        *[
            st.builds(expr_type.builder, expr_type.strategy)
            for expr_type in EXPR_TYPES
            if not expr_type.disable
        ]
    )

    @staticmethod
    def _extend_tree(children: st.SearchStrategy[Any]) -> st.SearchStrategy[Any]:
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


def evaluate_expr(
    expr: Arithmetic | Quantity,
) -> Quantity_Interval_Disjoint:
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
def test_discover_literal_folding(expr: Arithmetic):
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

    root = Parameter(domain=Numbers(negative=True, zero_allowed=True, integer=False))
    root.alias_is(expr)

    try:
        evaluated_expr = evaluate_expr(expr)
    except Exception:
        if ALLOW_EVAL_ERROR:
            return
        raise

    solver.update_superset_cache(root)
    solver_result = solver.inspect_get_known_supersets(root)

    assert isinstance(evaluated_expr, Quantity_Interval_Disjoint)
    assert isinstance(solver_result, Quantity_Interval_Disjoint)

    if ALLOW_ROUNDING_ERROR and solver_result != evaluated_expr:
        try:
            deviation_rel = evaluated_expr.op_deviation_to(solver_result, relative=True)
            return
        except Exception:
            pass
        else:
            assert deviation_rel < 0.01, f"Mismatch {evaluated_expr} != {solver_result}"

        deviation = evaluated_expr.op_deviation_to(solver_result)
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

    solver.update_superset_cache(root)
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


@example(Log(Sin(Add(lit(0), lit(1)))))
@example(
    Add(
        Add(lit(0), lit(0)),
        Sqrt(Cos(lit(0))),
    ),
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
    Divide(
        Divide(
            Sqrt(Add(lit(2))),
            lit(2),
        ),
        lit(710038921),
    )
)
@example(
    Sin(
        Sin(
            Subtract(
                lit(1),
                p(Range(-inf, inf)),
            ),
        ),
    ),
)
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

    solver.update_superset_cache(root)
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

        all_exprs = GraphFunctions(*get_graphs(self.exprs)).nodes_of_type(Arithmetic)
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
        expr: Arithmetic,
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
        stats.event("eval exc", expr, exc=e)
        return

    assert isinstance(evaluated_expr, Quantity_Interval_Disjoint)

    try:
        solver.update_superset_cache(root)
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
        stats.event("exc", expr, exc=e)
        return

    if solver_result != evaluated_expr:
        try:
            deviation = solver_result.op_deviation_to(evaluated_expr, relative=True)
        except Exception:
            deviation = solver_result.op_deviation_to(evaluated_expr)
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
