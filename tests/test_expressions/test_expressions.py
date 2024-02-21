import operator
from collections.abc import Callable

from atopile.expressions import Expression, defer_operation_factory


def test_two_callables():
    a = Expression(symbols=set(), lambda_=lambda ctx: ctx["d"])
    b = Expression(symbols=set(), lambda_=lambda ctx: 21)

    c = defer_operation_factory(a, operator.add, b)

    assert isinstance(c, Callable)
    assert c({"d": 157}) == 178


def test_one_callable():
    a = Expression(symbols=set(), lambda_=lambda ctx: ctx["d"])
    b = 12

    c = defer_operation_factory(a, operator.add, b)

    assert isinstance(c, Callable)
    assert c({"d": 58}) == 70


def test_no_callables():
    a = 12
    b = 21

    c = defer_operation_factory(a, operator.add, b)

    assert not isinstance(c, Callable)
    assert c == 33
