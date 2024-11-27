# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from itertools import pairwise
from typing import cast

import pytest

import faebryk.library._F as F
from faebryk.core.node import Node
from faebryk.core.parameter import (
    Additive,
    And,
    Expression,
    Not,
    Parameter,
    ParameterOperatable,
)
from faebryk.libs.library import L
from faebryk.libs.library.L import Range
from faebryk.libs.logging import setup_basic_logging
from faebryk.libs.units import P
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


def test_new_definitions():
    _ = Parameter(
        units=P.ohm,
        domain=L.Domains.Numbers.REAL(negative=False),
        soft_set=Range(1 * P.ohm, 10 * P.Mohm),
        likely_constrained=True,
    )


def test_compact_repr():
    p1 = Parameter(units=P.V)
    p2 = Parameter(units=P.V)
    context = ParameterOperatable.ReprContext()
    expr = cast(Expression, (p1 + p2 + (5 * P.V)) * 10)  # type: ignore
    exprstr = expr.compact_repr(context)
    assert exprstr == "((A volt + B volt) + 5 volt) * 10"
    expr2 = p2 + p1
    expr2str = expr2.compact_repr(context)
    assert expr2str == "B volt + A volt"

    p3 = Parameter(domain=L.Domains.BOOL())
    expr3 = Not(p3)
    expr3str = expr3.compact_repr(context)
    assert expr3str == "¬C"

    expr4 = And(expr3, (expr > 10 * P.V))
    expr4str = expr4.compact_repr(context)
    assert expr4str == "¬C ∧ ((((A volt + B volt) + 5 volt) * 10) > 10 volt)"

    manyps = times(22, Parameter)
    Additive.sum(manyps).compact_repr(context)

    pZ = Parameter()
    assert pZ.compact_repr(context) == "Z"

    pa = Parameter()
    assert pa.compact_repr(context) == "a"

    manyps2 = times(25, Parameter)
    Additive.sum(manyps2).compact_repr(context)
    palpha = Parameter()
    assert palpha.compact_repr(context) == "α"
    pbeta = Parameter()
    assert pbeta.compact_repr(context) == "β"

    manyps3 = times(22, Parameter)
    Additive.sum(manyps3).compact_repr(context)
    pAA = Parameter()
    assert pAA.compact_repr(context) == "A'"


@pytest.mark.skip
def test_visualize():
    """
    Creates webserver that opens automatically if run in jupyter notebook
    """
    from faebryk.exporters.visualize.interactive_params import visualize_parameters

    class App(Node):
        p1 = L.f_field(Parameter)(units=P.V)

    app = App()

    p2 = Parameter(units=P.V)
    p3 = Parameter(units=P.A)

    # app.p1.constrain_ge(p2 * 5)
    # app.p1.operation_is_ge(p2 * 5).constrain()
    (app.p1 >= p2 * 5).constrain()

    (p2 * p3 + app.p1 * 1 * P.A <= 10 * P.W).constrain()

    pytest.raises(ValueError, bool, app.p1 >= p2 * 5)

    G = app.get_graph()
    visualize_parameters(G, height=1400)


@pytest.mark.skip
def test_visualize_chain():
    from faebryk.exporters.visualize.interactive_params import visualize_parameters

    params = times(10, Parameter)
    sums = [p1 + p2 for p1, p2 in pairwise(params)]
    products = [p1 * p2 for p1, p2 in pairwise(sums)]
    bigsum = Additive.sum(products)

    predicates = [bigsum <= 100]
    for p in predicates:
        p.constrain()

    G = params[0].get_graph()
    visualize_parameters(G, height=1400)


@pytest.mark.skip
def test_visualize_inspect_app():
    from faebryk.exporters.visualize.interactive_params import visualize_parameters

    rp2040 = F.RP2040()

    G = rp2040.get_graph()
    visualize_parameters(G, height=1400)


# TODO remove
if __name__ == "__main__":
    # if run in jupyter notebook
    import sys

    func = test_compact_repr

    if "ipykernel" in sys.modules:
        func()
    else:
        import typer

        setup_basic_logging()
        typer.run(func)
