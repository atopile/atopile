from math import sin
import warnings
from datetime import timedelta
from functools import partial, reduce
from operator import add, mul
from typing import Any, Callable, Iterable, NamedTuple

from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.errors import NonInteractiveExampleWarning

from faebryk.core.core import Namespace
from faebryk.core.parameter import (
    Abs,
    Add,
    Arithmetic,
    Log,
    Multiply,
    Parameter,
    Power,
    Round,
    Sin,
)
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.core.solver.utils import Contradiction
from faebryk.libs.library.L import Range
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval,
    Quantity_Interval_Disjoint,
)
from faebryk.libs.units import Quantity

# canonical operations:
# Add, Multiply, Power, Round, Abs, Sin, Log
# Or, Not
# Intersection, Union, SymmetricDifference
# IsSubset, Is, GreaterThan


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

    Add = operator(Add)
    Multiply = operator(Multiply)
    Power = operator(Power)
    Round = operator(Round)
    Abs = operator(Abs)
    Sin = operator(Sin)
    Log = operator(Log)


def is_negative(value: Quantity_Interval_Disjoint | Parameter) -> bool:
    match value:
        case Quantity_Interval_Disjoint():
            return value.min_elem < 0 and value.max_elem < 0
        case Parameter():
            literal = value.get_literal()
            assert isinstance(literal, Quantity_Interval_Disjoint)
            return literal.min_elem < 0 and literal.max_elem < 0


def is_fractional(value: Quantity_Interval_Disjoint | Parameter) -> bool:
    literal: Quantity_Interval_Disjoint
    match value:
        case Quantity_Interval_Disjoint():
            literal = value
        case Parameter():
            literal = value.get_literal()
            assert isinstance(literal, Quantity_Interval_Disjoint)

    both_are_integers = literal.min_elem.is_integer() and literal.max_elem.is_integer()
    is_single_integer = (
        literal.min_elem == literal.max_elem and literal.min_elem.is_integer()
    )
    return not (both_are_integers or is_single_integer)


def is_zero(value: Quantity_Interval_Disjoint | Parameter) -> bool:
    match value:
        case Quantity_Interval_Disjoint():
            return bool(value.min_elem == 0) and bool(value.max_elem == 0)
        case Parameter():
            literal = value.get_literal()
            assert isinstance(literal, Quantity_Interval_Disjoint)
            return bool(literal.min_elem == 0) and bool(literal.max_elem == 0)


def is_empty(value: Quantity_Interval_Disjoint | Parameter) -> bool:
    literal: Quantity_Interval_Disjoint
    match value:
        case Quantity_Interval_Disjoint():
            literal = value
        case Parameter():
            literal = value.get_literal()
            assert isinstance(literal, Quantity_Interval_Disjoint)

    return literal.is_empty()


class st_values(Namespace):
    numeric = st.one_of(
        # [pico, tera]
        st.integers(min_value=-1_000_000_000_000, max_value=1_000_000_000_000),
        st.floats(
            allow_nan=False, allow_infinity=False, min_value=-1e12, max_value=1e12
        ),
    )

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

    small_values = st.one_of(
        small_numeric.map(Quantity_Interval_Disjoint.from_value),
        small_ranges.map(Quantity_Interval_Disjoint.from_value),
        small_parameters,
    )

    short_lists = partial(st.lists, min_size=1, max_size=5)

    lists = short_lists(values)

    pairs = st.tuples(values, values)

    power_pairs = st.tuples(values, small_values).filter(
        lambda pair: not (is_negative(pair[0]) and is_fractional(pair[1]))
        and not is_empty(pair[1])
    )


class Extension(Namespace):
    @staticmethod
    def tuples(children: st.SearchStrategy[Any]) -> st.SearchStrategy[Any]:
        return st.tuples(children, children)

    @staticmethod
    def single(children: st.SearchStrategy[Any]) -> st.SearchStrategy[Any]:
        return children


class ExprType(NamedTuple):
    builder: Callable[[Any], Arithmetic]
    strategy: st.SearchStrategy[Any]
    extension_strategy: Callable[[st.SearchStrategy[Any]], st.SearchStrategy[Any]]


EXPR_TYPES = [
    ExprType(Builders.Add, st_values.lists, Extension.tuples),
    ExprType(Builders.Multiply, st_values.lists, Extension.tuples),
    # ExprType(Builders.Power, st_values.power_pairs, Extension.tuples),
    # ExprType(Builders.Round, st_values.values, Extension.single),
    # ExprType(Builders.Abs, st_values.values, Extension.single),
    ExprType(Builders.Sin, st_values.values, Extension.single),
    # ExprType(Builders.Log, st_values.values, Extension.single),
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
        max_leaves=50,
    )


def evaluate_expr(
    expr: Arithmetic | Quantity,
) -> Quantity_Interval_Disjoint:
    match expr:
        case Add():
            operands = [evaluate_expr(operand) for operand in expr.operands]
            print(" + ".join(str(operand) for operand in operands))
            return reduce(add, operands)
        case Multiply():
            operands = [evaluate_expr(operand) for operand in expr.operands]
            print(" * ".join(str(operand) for operand in operands))
            return reduce(mul, operands)
        case Power():
            assert len(expr.operands) == 2
            base, exp = [evaluate_expr(operand) for operand in expr.operands]
            print(f"{base} ^ {exp}")
            print(f"{is_negative(base)=}")
            print(f"{is_fractional(exp)=}")
            return base**exp
        # case Round():
        #     return round(evaluate_expr(expr.operands[0]))
        # case Abs():
        #     return abs(evaluate_expr(expr.operands[0]))
        case Sin():
            assert len(expr.operands) == 1
            return evaluate_expr(expr.operands[0]).op_sin()
        # case Log():
        #     return log(evaluate_expr(expr.operands[0]))
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
