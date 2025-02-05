import logging
import math
import warnings
from datetime import timedelta
from functools import partial, reduce
from operator import add, mul, pow, sub, truediv
from typing import Any, Callable, Iterable, NamedTuple

from hypothesis import given, settings
from hypothesis import strategies as st
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
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval,
    Quantity_Interval_Disjoint,
)
from faebryk.libs.units import Quantity

logger = logging.getLogger(__name__)

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


def abs_close(a: float | Quantity, b: float) -> bool:
    return math.isclose(a, b, abs_tol=1e-15)


class Builders(Namespace):
    @staticmethod
    def build_parameter(quantity) -> Parameter:
        p = Parameter()
        p.alias_is(quantity)
        return p

    @staticmethod
    def operator(op: type[Arithmetic]) -> Callable[[Any], Arithmetic]:
        return (
            lambda operands: op(*operands)
            if isinstance(operands, Iterable)
            else op(operands)
        )

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
        return value.min_elem < 0 and value.max_elem < 0

    @staticmethod
    def is_positive(value: ValueT) -> bool:
        value = Filters._unwrap_param(value)
        return value.min_elem > 0 and value.max_elem > 0

    @staticmethod
    def is_fractional(value: ValueT) -> bool:
        value = Filters._unwrap_param(value)

        both_are_integers = value.min_elem.is_integer() and value.max_elem.is_integer()
        is_single_integer = (
            value.min_elem == value.max_elem and value.min_elem.is_integer()
        )
        return not (both_are_integers or is_single_integer)

    @staticmethod
    def is_zero(value: ValueT) -> bool:
        value = Filters._unwrap_param(value)
        return abs_close(value.min_elem, 0) and abs_close(value.max_elem, 0)

    @staticmethod
    def is_non_zero(value: ValueT) -> bool:
        value = Filters._unwrap_param(value)
        return not (abs_close(value.min_elem, 0) or abs_close(value.max_elem, 0))

    @staticmethod
    def is_empty(value: ValueT) -> bool:
        value = Filters._unwrap_param(value)
        return value.is_empty()

    @staticmethod
    def is_valid_for_power(
        pair: tuple[ValueT, ValueT],
    ) -> bool:
        return (
            not (Filters.is_negative(pair[0]) and Filters.is_fractional(pair[1]))
            and (Filters.is_positive(pair[0]) or Filters.is_negative(pair[0]))
            and (Filters.is_positive(pair[1]) or Filters.is_negative(pair[1]))
        )

    @staticmethod
    def is_valid_for_division(
        pair: tuple[ValueT, ValueT],
    ) -> bool:
        return Filters.is_non_zero(pair[1])


class st_values(Namespace):
    numeric = st.one_of(
        # [pico, tera]
        st.integers(min_value=int(-1e12), max_value=int(1e12)),
        st.floats(
            allow_nan=False, allow_infinity=False, min_value=-1e12, max_value=1e12
        ),
    ).filter(lambda x: x == 0 or abs(x) > 1e-15)

    small_numeric = st.one_of(
        st.integers(min_value=-100, max_value=100),
        st.floats(
            allow_nan=False, allow_infinity=False, min_value=-10.0, max_value=10.0
        ),
    )

    ranges = st.builds(
        lambda values: Range(*sorted(values)), st.tuples(numeric, numeric)
    )

    small_ranges = st.builds(
        lambda values: Range(*sorted(values)), st.tuples(small_numeric, small_numeric)
    )

    quantities = st.one_of(numeric, ranges).map(Quantity_Interval_Disjoint.from_value)

    small_quantities = st.one_of(small_numeric, small_ranges).map(
        Quantity_Interval_Disjoint.from_value
    )

    parameters = st.builds(Builders.build_parameter, quantities)

    small_parameters = st.builds(Builders.build_parameter, small_quantities)

    values = st.one_of(
        numeric.map(Quantity_Interval_Disjoint.from_value),
        ranges.map(Quantity_Interval_Disjoint.from_value),
        parameters,
    )

    positive_values = values.filter(Filters.is_positive)

    small_values = st.one_of(
        small_numeric.map(Quantity_Interval_Disjoint.from_value),
        small_ranges.map(Quantity_Interval_Disjoint.from_value),
        small_parameters,
    )

    short_lists = partial(st.lists, min_size=1, max_size=5)

    lists = short_lists(values)

    pairs = st.tuples(values, values)

    division_pairs = st.tuples(values, values.filter(Filters.is_non_zero))

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
        return st.tuples(children, st_values.values.filter(Filters.is_non_zero))

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
    ExprType(Builders.Round, st_values.values, Extension.single),
    # ExprType(Builders.Floor, st_values.values, Extension.single),
    # ExprType(Builders.Ceil, st_values.values, Extension.single),
    # ExprType(Builders.Min, st_values.lists, Extension.tuples),
    # ExprType(Builders.Max, st_values.lists, Extension.tuples),
    # ExprType(Builders.Integrate, st_values.lists, Extension.tuples),
    # ExprType(Builders.Differentiate, st_values.lists, Extension.tuples),
]


class st_exprs(Namespace):
    one_of = st.one_of(
        *[st.builds(expr_type.builder, expr_type.strategy) for expr_type in EXPR_TYPES]
    )

    trees = st.recursive(
        one_of,
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
        Round: round,
        Abs: abs,
        Sin: lambda x: x.op_sin(),
        Log: lambda x: x.op_log(),
        Cos: lambda x: (x + math.pi / 2).op_sin(),
        Floor: lambda x: round(x - 0.5),  # TODO: handle inf
        Ceil: lambda x: round(x + 0.5),  # TODO: handle inf
        Min: min,
        Max: max,
    }

    match expr:
        # monoids
        case Add() | Multiply() | Min() | Max():
            operands = (evaluate_expr(operand) for operand in expr.operands)
            operator = operator_map.get(type(expr))
            assert operator is not None
            return reduce(operator, operands)
        # left/right-associative
        case Subtract() | Divide() | Power():
            operands = [evaluate_expr(operand) for operand in expr.operands]
            operator = operator_map.get(type(expr))
            assert operator is not None
            assert len(operands) == 2
            return operator(operands[0], operands[1])
        # unary
        case Sqrt() | Round() | Abs() | Sin() | Log() | Cos() | Floor() | Ceil():
            assert len(expr.operands) == 1
            operand = evaluate_expr(expr.operands[0])
            operator = operator_map.get(type(expr))
            assert operator is not None
            return operator(operand)
        case Quantity_Interval():
            # TODO: why are we getting these?
            return Quantity_Interval_Disjoint.from_value(expr)
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


@given(st_exprs.trees)
@settings(deadline=timedelta(milliseconds=1000))
def test_literal_folding(expr: Arithmetic):
    solver = DefaultSolver()

    root = Parameter()
    root.alias_is(expr)

    try:
        solver_result = solver.inspect_get_known_supersets(root)
    except Contradiction:
        # TODO: handle this better
        return

    evaluated_expr = evaluate_expr(expr)
    assert isinstance(evaluated_expr, Quantity_Interval_Disjoint)
    assert solver_result == evaluated_expr


@given(st_exprs.trees)
@settings(deadline=timedelta(milliseconds=1000))
def test_all_folding_implemented(expr: Arithmetic):
    evaluate_expr(expr)


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


if __name__ == "__main__":
    warnings.filterwarnings("ignore", category=NonInteractiveExampleWarning)

    evaluate_exprs()
    # generate_exprs()
