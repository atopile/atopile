# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import typer

from faebryk.core.parameter import (
    Parameter,
    ParameterOperatable,
)
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.libs.logging import setup_basic_logging
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval,
    Quantity_Interval_Disjoint,
)
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


def demo_1_literals():
    x = Quantity_Interval(10 * P.V, 20 * P.V)
    print(x)

    y = Quantity_Interval(2 * P.A, 3 * P.A)

    z = x * y
    print(z)
    return

    z_w = Quantity_Interval_Disjoint(z, units=P.W)
    print(z_w)

    z_sum = z + z_w
    print(z_sum)


def demo_2_literals_uncorrelated():
    x = Quantity_Interval_Disjoint((10, 20))

    y = Quantity_Interval_Disjoint((15, 30))
    print(x <= y)
    return

    y2 = Quantity_Interval_Disjoint((25, 30))
    print(x <= y2)

    y3 = Quantity_Interval_Disjoint((5, 9))
    print(x <= y3)

    print(x & y)


def demo_3_expression_tree():
    A, B, C = (Parameter() for _ in range(3))

    x = A + B + C * 5 > 10
    x.constrain()

    context = ParameterOperatable.ReprContext()

    print(x.compact_repr(context))

    solver = DefaultSolver()
    repr_map = solver.phase_1_simplify_analytically(x.get_graph(), context)
    print(repr_map[0].repr_map[x].compact_repr(context, no_lit=True))


def main(i: int):
    match i:
        case 1:
            demo_1_literals()
        case 2:
            demo_2_literals_uncorrelated()
        case 3:
            demo_3_expression_tree()


if __name__ == "__main__":
    setup_basic_logging(force_fmt=True)
    typer.run(main)
