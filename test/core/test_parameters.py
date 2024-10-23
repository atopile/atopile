# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from itertools import pairwise

import pytest

from faebryk.core.node import Node
from faebryk.core.parameter import Parameter
from faebryk.libs.library import L
from faebryk.libs.sets import Range
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


def test_visualize_chain():
    from faebryk.exporters.visualize.interactive_params import visualize_parameters

    params = times(10, Parameter)
    sums = [p1 + p2 for p1, p2 in pairwise(params)]
    products = [p1 * p2 for p1, p2 in pairwise(sums)]
    bigsum = sum(products)

    predicates = [bigsum <= 100]
    for p in predicates:
        p.constrain()

    G = params[0].get_graph()
    visualize_parameters(G, height=1400)


# TODO remove
if __name__ == "__main__":
    # if run in jupyter notebook
    import sys

    if "ipykernel" in sys.modules:
        test_visualize()
    else:
        import typer

        typer.run(test_visualize_chain)
