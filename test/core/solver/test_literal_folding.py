import warnings
from datetime import timedelta
from functools import partial
from operator import add
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
from faebryk.libs.sets.quantity_sets import Quantity_Interval_Disjoint
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


class st_values(Namespace):
    numeric = st.one_of(
        st.floats(allow_nan=False, allow_infinity=False, min_value=0, max_value=1e30),
        st.integers(),
    )

    ranges = st.builds(
        lambda values: Range(*sorted(values)), st.tuples(numeric, numeric)
    )

    quantities = st.one_of(numeric, ranges).map(Quantity_Interval_Disjoint.from_value)

    parameters = st.builds(Builders.build_parameter, quantities)

    values = st.one_of(
        numeric.map(Quantity_Interval_Disjoint.from_value),
        ranges.map(Quantity_Interval_Disjoint.from_value),
        parameters,
    )

    short_lists = partial(st.lists, min_size=1, max_size=5)

    lists = short_lists(values)

    pairs = st.tuples(values, values)


class Extension(Namespace):
    @staticmethod
    def tuples(children: st.SearchStrategy[Any]) -> st.SearchStrategy[Any]:
        return st.tuples(children, children)

    @staticmethod
    def single(children: st.SearchStrategy[Any]) -> st.SearchStrategy[Any]:
        return children


ExprType = NamedTuple(
    "ExprType",
    [
        ("builder", Callable[[Any], Arithmetic]),
        ("strategy", st.SearchStrategy[Any]),
        (
            "extension_strategy",
            Callable[[st.SearchStrategy[Any]], st.SearchStrategy[Any]],
        ),
    ],
)

EXPR_TYPES = [
    ExprType(Builders.Add, st_values.pairs, Extension.tuples),
    # ExprType(Builders.Multiply, st_values.pairs, Extension.tuples),
    # ExprType(Builders.Power, st_values.pairs, Extension.tuples),
    # ExprType(Builders.Round, st_values.values, Extension.single),
    # ExprType(Builders.Abs, st_values.values, Extension.single),
    # ExprType(Builders.Sin, st_values.values, Extension.single),
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


def evaluate_expr(expr: Arithmetic | Quantity):
    match expr:
        case Add():
            return add(*[evaluate_expr(operand) for operand in expr.operands])
        # case Multiply():
        #     return mul(*[evaluate_expr(operand) for operand in expr.operands])
        # case Power():
        #     return pow(*[evaluate_expr(operand) for operand in expr.operands])
        # case Round():
        #     return round(evaluate_expr(expr.operands[0]))
        # case Abs():
        #     return abs(evaluate_expr(expr.operands[0]))
        # case Sin():
        #     return sin(evaluate_expr(expr.operands[0]))
        # case Log():
        #     return log(evaluate_expr(expr.operands[0]))
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
    assert solver_result == evaluated_expr


if __name__ == "__main__":
    warnings.filterwarnings("ignore", category=NonInteractiveExampleWarning)

    from rich.console import Console
    from rich.table import Table

    table = Table(title="Expression Evaluation Examples")
    table.add_column("Evaluated Result", justify="left")
    table.add_column("Original Expression", justify="left")

    for _ in range(20):
        expr = st_exprs.trees.example()
        table.add_row(str(evaluate_expr(expr)), expr.compact_repr())

    console = Console()
    console.print(table)
