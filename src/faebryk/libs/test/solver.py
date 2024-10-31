# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
from faebryk.core.graphinterface import Graph
from faebryk.core.node import Node
from faebryk.core.parameter import ParameterOperatable
from faebryk.core.solver import DefaultSolver
from faebryk.libs.sets import PlainSet


def solves_to(stmt: ParameterOperatable, result: bool):
    stmt.inspect_add_on_solution(lambda x: x.inspect_known_values() == PlainSet(result))


def solve_and_test(G: Graph | Node, *stmts: ParameterOperatable):
    if isinstance(G, Node):
        G = G.get_graph()

    for stmt in stmts:
        solves_to(stmt, True)

    solver = DefaultSolver()
    solver.find_and_lock_solution(G)
