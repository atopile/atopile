# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
from faebryk.core.graph import Graph
from faebryk.core.node import Node
from faebryk.core.parameter import ParameterOperatable
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.core.solver.solver import Solver
from faebryk.libs.sets.sets import BoolSet


def solves_to(stmt: ParameterOperatable, result: bool, solver: Solver):
    def assert_eq(x: ParameterOperatable):
        assert solver.inspect_known_values(x) == BoolSet(result)

    stmt.inspect_add_on_solution(assert_eq)


def solve_and_test(G: Graph | Node, *stmts: ParameterOperatable):
    if isinstance(G, Node):
        G = G.get_graph()

    solver = DefaultSolver()

    for stmt in stmts:
        solves_to(stmt, True, solver)

    solver.find_and_lock_solution(G)
