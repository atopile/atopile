from dataclasses import dataclass
from typing import Any, Protocol

from faebryk.core.graph import Graph
from faebryk.core.parameter import Expression, ParameterOperatable, Predicate


class Solver(Protocol):
    # TODO booleanlike is very permissive
    type PredicateWithInfo[ArgType] = tuple[ParameterOperatable.BooleanLike, ArgType]

    class TimeoutError(Exception): ...

    @dataclass
    class SolveResult:
        timed_out: bool

    @dataclass
    class SolveResultAny[ArgType](SolveResult):
        true_predicates: list["Solver.PredicateWithInfo[ArgType]"]
        false_predicates: list["Solver.PredicateWithInfo[ArgType]"]
        unknown_predicates: list["Solver.PredicateWithInfo[ArgType]"]

    @dataclass
    class SolveResultSingle(SolveResult):
        # TODO thinkn about failure case
        value: Any  # TODO Any -> NumberLike?
        # parameters_with_empty_solution_sets: list[Parameter]

        def get(self) -> Any:
            if self.timed_out:
                raise Solver.TimeoutError()
            return self.value

    @dataclass
    class SolveResultAll(SolveResult):
        has_solution: bool

    # timeout per solve call in milliseconds
    timeout: int
    # threads: int
    # in megabytes
    # memory: int

    def get_any_single(
        self,
        operatable: ParameterOperatable,
        lock: bool,
        suppose_constraint: Predicate | None = None,
        minimize: Expression | None = None,
    ) -> SolveResultSingle:
        """
        Solve for a single value for the given expression.

        Args:
            operatable: The expression or parameter to solve.
            suppose_constraint: An optional constraint that can be added to make solving
                                easier. It is only in effect for the duration of the
                                solve call.
            minimize: An optional expression to minimize while solving.
            lock: If True, ensure the result is part of the solution set of
                              the expression.

        Returns:
            A SolveResultSingle object containing the chosen value.
        """
        ...

    def assert_any_predicate[ArgType](
        self,
        predicates: list["Solver.PredicateWithInfo[ArgType]"],
        lock: bool,
        suppose_constraint: Predicate | None = None,
        minimize: Expression | None = None,
    ) -> SolveResultAny[ArgType]:
        """
        Make at least one of the passed predicates true, unless that is impossible.

        Args:
            predicates: A list of predicates to solve.
            suppose_constraint: An optional constraint that can be added to make solving
                                easier. It is only in effect for the duration of the
                                solve call.
            minimize: An optional expression to minimize while solving.
            lock: If True, add the solutions as constraints.

        Returns:
            A SolveResult object containing the true, false, and unknown predicates.

        Note:
            There is no specific order in which the predicates are solved.
        """
        ...

    # run deferred work
    def find_and_lock_solution(self, G: Graph) -> SolveResultAll: ...


class DefaultSolver(Solver):
    timeout: int = 1000

    def get_any_single(
        self,
        operatable: ParameterOperatable,
        lock: bool,
        suppose_constraint: Predicate | None = None,
        minimize: Expression | None = None,
    ) -> Solver.SolveResultSingle:
        raise NotImplementedError()

    def assert_any_predicate[ArgType](
        self,
        predicates: list["Solver.PredicateWithInfo[ArgType]"],
        lock: bool,
        suppose_constraint: Predicate | None = None,
        minimize: Expression | None = None,
    ) -> Solver.SolveResultAny[ArgType]:
        raise NotImplementedError()

    def find_and_lock_solution(self, G: Graph) -> Solver.SolveResultAll:
        raise NotImplementedError()
