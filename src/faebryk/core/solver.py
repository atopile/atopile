from dataclasses import dataclass
from typing import Any, Protocol

from faebryk.core.graph import Graph
from faebryk.core.parameter import Expression, Parameter, ParameterOperatable, Predicate


class Solver(Protocol):
    # TODO booleanlike is very permissive
    type PredicateWithInfo[ArgType] = tuple[ParameterOperatable.BooleanLike, ArgType]

    @dataclass
    class SolveResult[ArgType]:
        true_predicates: list["Solver.PredicateWithInfo[ArgType]"]
        false_predicates: list["Solver.PredicateWithInfo[ArgType]"]
        unknown_predicates: list["Solver.PredicateWithInfo[ArgType]"]

    # timeout per solve call in milliseconds
    timeout: int
    # threads: int
    # in megabytes
    # memory: int

    def get_any_single(
        self,
        G: Graph,
        expression: Expression,
        suppose_constraint: Predicate | None = None,
        minimize: Expression | None = None,
        constrain_result: bool = True,
    ) -> tuple[Any, list[Parameter]]:  # TODO Any -> NumberLike?
        """
        Solve for a single value for the given expression.

        Args:
            G: The graph to solve on.
            expression: The expression to solve.
            suppose_constraint: An optional constraint that can be added to make solving
                                easier. It is only in effect for the duration of the
                                solve call.
            minimize: An optional expression to minimize while solving.
            constrain_result: If True, ensure the result is part of the solution set of
                              the expression.

        Returns:
            A tuple containing the chosen value and a list of parameters with empty
                               solution sets.
        """
        ...

    def assert_any_predicate[ArgType](
        self,
        G: Graph,
        predicates: list["Solver.PredicateWithInfo[ArgType]"],
        suppose_constraint: Predicate | None = None,
        minimize: Expression | None = None,
        constrain_solved: bool = True,
    ) -> SolveResult[ArgType]:
        """
        Make at least one of the passed predicates true, unless that is impossible.

        Args:
            G: The graph to solve on.
            predicates: A list of predicates to solve.
            suppose_constraint: An optional constraint that can be added to make solving
                                easier. It is only in effect for the duration of the
                                solve call.
            minimize: An optional expression to minimize while solving.
            constrain_solved: If True, add the solutions as constraints.

        Returns:
            A SolveResult object containing the true, false, and unknown predicates.

        Note:
            There is no specific order in which the predicates are solved.
        """
        ...

    # run deferred work
    def finalize(self, G: Graph) -> None: ...


class DefaultSolver(Solver):
    timeout: int = 1000

    def get_any_single(
        self,
        G: Graph,
        expression: Expression,
        suppose_constraint: Predicate | None = None,
        minimize: Expression | None = None,
        constrain_result: bool = True,
    ):
        raise NotImplementedError()

    def assert_any_predicate[ArgType](
        self,
        G: Graph,
        predicates: list["Solver.PredicateWithInfo[ArgType]"],
        suppose_constraint: Predicate | None = None,
        minimize: Expression | None = None,
        constrain_solved: bool = True,
    ) -> Solver.SolveResult[ArgType]:
        raise NotImplementedError()

    def finalize(self, G: Graph) -> None:
        raise NotImplementedError()
