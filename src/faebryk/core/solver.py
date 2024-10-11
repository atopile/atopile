from typing import Any, Protocol

from faebryk.core.graph import Graph
from faebryk.core.parameter import Expression, Parameter, Predicate


class Solver(Protocol):
    # timeout per solve call in milliseconds
    timeout: int
    # threads: int
    # in megabytes
    # memory: int

    # solve for a single value for the given expression
    # while trying to minimize the value of the optional minimize expression
    # suppose_constraint can be added, which by constraining the solution further can make solving easier
    # it is only in effect for the duration of the solve call
    # constrain_result will make sure the result is actually part of the solution set of the expression
    # returns a tuple of the value chosen and a list of parameters that have an empty solution set
    def get_any_single(
        self,
        G: Graph,
        expression: Expression,
        suppose_constraint: Predicate | None = None,
        minimize: Expression | None = None,
        constrain_result: bool = True,
    ) -> tuple[Any, list[Parameter]]: ...  # TODO Any -> NumberLike?

    # make at least one of the passed predicates true
    # while trying to minimize the value of the optional minimize expression
    # there is no specific order in which the predicates are solved
    # suppose_constraint can be added, which by constraining the solution further can make solving easier
    # it is only in effect for the duration of the solve call
    # constrain_solved will add the solutions as constraints
    # returns a tuple of two lists:
    # - the first list contains the predicates that were actually solved, i.e. they are true/false
    # - the second list contains the expressions that remain unknown
    # - the third list contains the parameters that have an empty solution set
    def assert_any_predicate(
        self,
        G: Graph,
        predicates: list[Predicate],
        suppose_constraint: Predicate | None = None,
        minimize: Expression | None = None,
        constrain_solved: bool = True,
    ) -> tuple[list[Expression], list[Expression], list[Parameter]]: ...

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

    def assert_any_predicate(
        self,
        G: Graph,
        predicates: list[Predicate],
        suppose_constraint: Predicate | None = None,
        minimize: Expression | None = None,
        constrain_solved: bool = True,
    ) -> tuple[list[Expression], list[Expression], list[Parameter]]:
        raise NotImplementedError()

    def finalize(self, G: Graph) -> None:
        raise NotImplementedError()
