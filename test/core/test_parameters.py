# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import pytest

from faebryk.core.node import Node
from faebryk.core.parameter import Parameter
from faebryk.libs.library import L
from faebryk.libs.sets import Range
from faebryk.libs.units import P

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
    from faebryk.exporters.visualize.interactive_graph import interactive_graph

    class App(Node):
        p1 = L.f_field(Parameter)(units=P.V)

    app = App()

    p2 = Parameter(units=P.V)
    p3 = Parameter(units=P.A)

    # app.p1.constrain_ge(p2 * 5)
    # app.p1.operation_is_ge(p2 * 5).constrain()
    (app.p1 >= p2 * 5).constrain()

    (p2 * p3 + app.p1 * 1 * P.A <= 10 * P.W).constrain()

    # pytest.raises(ValueError, bool, app.p1 >= p2 * 5)

    G = app.get_graph()
    interactive_graph(G, height=1400)


# TODO remove
if __name__ == "__main__":
    # if run in jupyter notebook
    import sys

    if "ipykernel" in sys.modules:
        test_visualize()
    else:
        import typer

        typer.run(test_visualize)
