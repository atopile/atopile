from dataclasses import dataclass
from typing import Any, Protocol

from faebryk.core.graph import Graph
from faebryk.core.parameter import Expression, ParameterOperatable, Predicate


class Solver(Protocol):
    # TODO booleanlike is very permissive
    type PredicateWithInfo[ArgType] = tuple[ParameterOperatable.BooleanLike, ArgType]

    @dataclass
    class SolveResult[ArgType]:
        true_predicates: list["Solver.PredicateWithInfo[ArgType]"]
        false_predicates: list["Solver.PredicateWithInfo[ArgType]"]
        unknown_predicates: list["Solver.PredicateWithInfo[ArgType]"]

    @dataclass
    class SolveResultSingle:
        # TODO thinkn about failure case
        value: Any  # TODO Any -> NumberLike?
        # parameters_with_empty_solution_sets: list[Parameter]

    # timeout per solve call in milliseconds
    timeout: int
    # threads: int
    # in megabytes
    # memory: int

    def get_any_single(
        self,
        operatable: ParameterOperatable,
        suppose_constraint: Predicate | None = None,
        minimize: Expression | None = None,
        constrain_result: bool = True,
    ) -> SolveResultSingle:
        """
        Solve for a single value for the given expression.

        Args:
            operatable: The expression or parameter to solve.
            suppose_constraint: An optional constraint that can be added to make solving
                                easier. It is only in effect for the duration of the
                                solve call.
            minimize: An optional expression to minimize while solving.
            constrain_result: If True, ensure the result is part of the solution set of
                              the expression.

        Returns:
            A SolveResultSingle object containing the chosen value.
        """
        ...

    def assert_any_predicate[ArgType](
        self,
        predicates: list["Solver.PredicateWithInfo[ArgType]"],
        suppose_constraint: Predicate | None = None,
        minimize: Expression | None = None,
        constrain_solved: bool = True,
    ) -> SolveResult[ArgType]:
        """
        Make at least one of the passed predicates true, unless that is impossible.

        Args:
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
    def find_and_lock_solution(self, G: Graph) -> None: ...


class DefaultSolver(Solver):
    timeout: int = 1000

    def get_any_single(
        self,
        operatable: ParameterOperatable,
        suppose_constraint: Predicate | None = None,
        minimize: Expression | None = None,
        constrain_result: bool = True,
    ):
        raise NotImplementedError()

    def assert_any_predicate[ArgType](
        self,
        predicates: list["Solver.PredicateWithInfo[ArgType]"],
        suppose_constraint: Predicate | None = None,
        minimize: Expression | None = None,
        constrain_solved: bool = True,
    ) -> Solver.SolveResult[ArgType]:
        raise NotImplementedError()

    def find_and_lock_solution(self, G: Graph) -> None:
        raise NotImplementedError()
