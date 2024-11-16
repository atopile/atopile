import operator
from collections.abc import Callable

from atopile.expressions import Expression, defer_operation_factory


def test_two_callables():
    a = Expression(symbols={"d"}, lambda_=lambda ctx: ctx["d"])
    b = Expression(symbols=set(), lambda_=lambda ctx: 21)

    c = defer_operation_factory(operator.add, a, b)

    assert isinstance(c, Callable)
    assert c({"d": 157}) == 178


def test_one_callable():
    a = Expression(symbols={"d"}, lambda_=lambda ctx: ctx["d"])
    b = 12

    c = defer_operation_factory(operator.add, a, b)

    assert isinstance(c, Callable)
    assert c({"d": 58}) == 70


def test_no_callables():
    a = 12
    b = 21

    c = defer_operation_factory(operator.add, a, b)

    assert not isinstance(c, Callable)
    assert c == 33


def test_substitute():
    # Test simplification
    a = Expression(symbols={"d"}, lambda_=lambda ctx: ctx["d"])
    assert a.substitute({"d": 12}) == 12

    b = Expression(symbols={"e"}, lambda_=lambda ctx: ctx["e"])

    subbed = a.substitute({"d": b})
    assert callable(subbed)
    assert subbed({"e": 12}) == 12
    assert subbed.symbols == {"e"}
