# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import io
import logging
from collections import defaultdict
from dataclasses import dataclass
from functools import wraps
from itertools import combinations
from statistics import median
from types import NoneType
from typing import TYPE_CHECKING, Callable, Iterable, Sequence, TypeGuard, cast

from rich.console import Console
from rich.table import Table

from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.node import Node
from faebryk.core.parameter import (
    Associative,
    CanonicalExpression,
    CanonicalLiteral,
    CanonicalNumber,
    ConstrainableExpression,
    Domain,
    Expression,
    FullyAssociative,
    Is,
    IsSubset,
    Parameter,
    ParameterOperatable,
)
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval_Disjoint,
)
from faebryk.libs.sets.sets import BoolSet, P_Set, as_lit
from faebryk.libs.util import (
    ConfigFlag,
    ConfigFlagFloat,
    ConfigFlagInt,
    KeyErrorAmbiguous,
    partition,
    unique_ref,
)

if TYPE_CHECKING:
    from faebryk.core.solver.mutator import REPR_MAP, Mutator

logger = logging.getLogger(__name__)

# Config -------------------------------------------------------------------------------
S_LOG = ConfigFlag("SLOG", default=False, descr="Log solver operations")
VERBOSE_TABLE = ConfigFlag("SVERBOSE_TABLE", default=False, descr="Verbose table")
SHOW_SS_IS = ConfigFlag(
    "SSHOW_SS_IS",
    default=False,
    descr="Show subset/is predicates in graph print",
)
PRINT_START = ConfigFlag("SPRINT_START", default=False, descr="Print start of solver")
MAX_ITERATIONS_HEURISTIC = int(
    ConfigFlagInt("SMAX_ITERATIONS", default=40, descr="Max iterations")
)
TIMEOUT = ConfigFlagFloat("STIMEOUT", default=120, descr="Solver timeout").get()
ALLOW_PARTIAL_STATE = ConfigFlag("SPARTIAL", default=True, descr="Allow partial state")
# --------------------------------------------------------------------------------------

if S_LOG:
    logger.setLevel(logging.DEBUG)


def set_log_level(level: int):
    from faebryk.core.solver.defaultsolver import logger as defaultsolver_logger
    from faebryk.core.solver.mutator import logger as mutator_logger

    loggers = [logger, mutator_logger, defaultsolver_logger]
    for lo in loggers:
        lo.setLevel(level)


class Contradiction(Exception):
    def __init__(self, msg: str, involved: list[ParameterOperatable]):
        super().__init__(msg)
        self.msg = msg
        self.involved_exprs = involved

    def __str__(self):
        return f"{self.msg}: Involved: {self.involved_exprs}"


class ContradictionByLiteral(Contradiction):
    def __init__(
        self,
        msg: str,
        involved: list[ParameterOperatable],
        literals: list["SolverLiteral"],
    ):
        super().__init__(msg, involved)
        self.literals = literals

    def __str__(self):
        return f"{super().__str__()}\n" f"Literals: {self.literals}"


SolverLiteral = CanonicalLiteral
SolverAll = ParameterOperatable | SolverLiteral
SolverAllExtended = ParameterOperatable.All | SolverLiteral


# alias
make_lit = as_lit


# TODO should be part of mutator
def try_extract_literal(
    po: ParameterOperatable,
    allow_subset: bool = False,
    check_pre_transform: "Mutator | None" = None,
) -> SolverLiteral | None:
    pos = {po}

    # TODO should be mutator api
    if (
        check_pre_transform
        and po in check_pre_transform.transformations.mutated.values()
    ):
        mutator = check_pre_transform
        pos |= {
            k
            for k, v in mutator.transformations.mutated.items()
            if v is po and k not in mutator.transformations.removed
        }

    lits = set()
    try:
        for po in pos:
            lit = ParameterOperatable.try_extract_literal(po, allow_subset=allow_subset)
            if lit is not None:
                lits.add(lit)
    except KeyErrorAmbiguous as e:
        raise ContradictionByLiteral(
            "Duplicate unequal is literals",
            involved=[po],
            literals=e.duplicates,
        ) from e
    if len(lits) > 1:
        raise ContradictionByLiteral(
            "Multiple literals found",
            involved=list(pos),
            literals=list(lits),
        )
    lit = next(iter(lits), None)
    assert isinstance(lit, (CanonicalNumber, BoolSet, P_Set, NoneType))
    return lit


def try_extract_literal_info(
    po: ParameterOperatable,
) -> tuple[SolverLiteral | None, bool]:
    """
    returns (literal, is_alias)
    """
    lit = try_extract_literal(po, allow_subset=False)
    if lit is not None:
        return lit, True
    lit = try_extract_literal(po, allow_subset=True)
    return lit, False


def map_extract_literals(
    expr: Expression, allow_subset: bool = False
) -> tuple[list[SolverAll], bool]:
    out = []
    any_lit = False
    for op in expr.operands:
        if is_literal(op):
            out.append(op)
            continue
        lit = try_extract_literal(op, allow_subset=allow_subset)
        if lit is None:
            out.append(op)
            continue
        out.append(lit)
        any_lit = True
    return out, any_lit


def alias_is_literal(
    po: ParameterOperatable,
    literal: ParameterOperatable.Literal | SolverLiteral,
    mutator: "Mutator",
    from_ops: Sequence[ParameterOperatable] | None = None,
    terminate: bool = False,
):
    literal = make_lit(literal)
    existing = try_extract_literal(po, check_pre_transform=mutator)
    if existing is not None:
        if existing == literal:
            if terminate:
                for op in po.get_operations(Is, constrained_only=True):
                    if existing in op.operands:
                        mutator.predicate_terminate(op)
                return
            return
        raise ContradictionByLiteral(
            "Tried alias to different literal",
            involved=[po],
            literals=[existing, literal],
        )
    # prevent (A is X) is X
    if isinstance(po, Is):
        if literal in po.get_literal_operands().values():
            return
    out = mutator.create_expression(
        Is,
        po,
        literal,
        from_ops=from_ops,
        constrain=True,
        # already checked for uncorrelated lit, op needs to be correlated
        allow_uncorrelated=False,
    )
    if terminate:
        mutator.predicate_terminate(out)
    return out


def subset_literal(
    po: ParameterOperatable,
    literal: ParameterOperatable.Literal | SolverLiteral,
    mutator: "Mutator",
    from_ops: Sequence[ParameterOperatable] | None = None,
):
    literal = make_lit(literal)

    if literal.is_empty():
        raise ContradictionByLiteral(
            "Tried subset to empty set",
            involved=[po],
            literals=[literal],
        )

    existing_alias = try_extract_literal(po, check_pre_transform=mutator)
    if existing_alias is not None:
        if not existing_alias.is_subset_of(literal):  # type: ignore #TODO
            raise ContradictionByLiteral(
                "Tried subset to different literal",
                involved=[po],
                literals=[existing_alias, literal],
            )
        return

    existing = try_extract_literal(po, allow_subset=True, check_pre_transform=mutator)
    if existing is not None:
        # no point in adding more general subset
        if existing.is_subset_of(literal):  # type: ignore #TODO
            return
        # other cases handled by intersect subsets algo

    return mutator.create_expression(
        IsSubset,
        po,
        literal,
        from_ops=from_ops,
        constrain=True,
        # already checked for uncorrelated lit, op needs to be correlated
        allow_uncorrelated=False,
    )


def are_aliased(po: ParameterOperatable, *other: ParameterOperatable) -> bool:
    return bool(
        po.get_operations(Is, constrained_only=True)
        & {o for o in other for o in o.get_operations(Is, constrained_only=True)}
    )


def alias_to(
    po: ParameterOperatable,
    to: ParameterOperatable | SolverLiteral,
    mutator: "Mutator",
    check_existing: bool = True,
    from_ops: Sequence[ParameterOperatable] | None = None,
):
    if is_literal(to):
        assert check_existing
        return alias_is_literal(po, to, mutator, from_ops=from_ops)

    # check if alias exists
    if isinstance(po, Expression) and isinstance(to, Expression) and check_existing:
        if po.get_operations(Is, constrained_only=True) & to.get_operations(
            Is, constrained_only=True
        ):
            return

    return mutator.create_expression(
        Is,
        po,
        to,
        from_ops=from_ops,
        constrain=True,
        check_exists=check_existing,
        allow_uncorrelated=True,
    )


def subset_to(
    po: ParameterOperatable,
    to: ParameterOperatable | SolverLiteral,
    mutator: "Mutator",
    check_existing: bool = True,
    from_ops: Sequence[ParameterOperatable] | None = None,
):
    if is_literal(to):
        assert check_existing
        return subset_literal(po, to, mutator, from_ops=from_ops)

    # check if alias exists
    if isinstance(po, Expression) and isinstance(to, Expression) and check_existing:
        if po.get_operations(Is, constrained_only=True) & to.get_operations(
            Is, constrained_only=True
        ):
            return

    return mutator.create_expression(
        IsSubset,
        po,
        to,
        from_ops=from_ops,
        constrain=True,
        check_exists=check_existing,
        allow_uncorrelated=True,
    )


def is_literal(po: ParameterOperatable | SolverAll) -> TypeGuard[SolverLiteral]:
    # allowed because of canonicalization
    return ParameterOperatable.is_literal(po)


def is_numeric_literal(po: ParameterOperatable) -> TypeGuard[CanonicalNumber]:
    return is_literal(po) and isinstance(po, CanonicalNumber)


def is_literal_expression(
    po: ParameterOperatable | SolverAll,
) -> TypeGuard[Expression]:
    return isinstance(po, Expression) and not po.get_involved_parameters()


def is_pure_literal_expression(
    po: ParameterOperatable | SolverAll,
) -> TypeGuard[CanonicalExpression]:
    return isinstance(po, Expression) and all(is_literal(op) for op in po.operands)


def is_alias_is_literal(po: ParameterOperatable) -> TypeGuard[Is]:
    return bool(
        isinstance(po, Is)
        and po.constrained
        and po.get_literal_operands()
        and po.operatable_operands
    )


def is_subset_literal(po: ParameterOperatable) -> TypeGuard[IsSubset]:
    return bool(
        isinstance(po, IsSubset)
        and po.constrained
        and is_literal(po.operands[1])
        and isinstance(po.operands[0], ParameterOperatable)
    )


def alias_is_literal_and_check_predicate_eval(
    expr: ParameterOperatable, value: BoolSet | bool, mutator: "Mutator"
):
    """
    Call this when 100% sure what the result of a predicate is.
    """
    alias_is_literal(expr, value, mutator, terminate=True)
    if not isinstance(expr, ConstrainableExpression):
        return
    if not expr.constrained:
        return
    # all predicates alias to True, so alias False will already throw
    if value != BoolSet(True):
        raise Contradiction(
            "Constrained predicate deduced to False",
            involved=[expr],
        )
    mutator.predicate_terminate(expr)

    # TODO is this still needed?
    # terminate all alias_is P -> True
    for op in expr.get_operations(Is):
        if not op.constrained:
            continue
        lit = try_extract_literal(op)
        if lit is None:
            continue
        if lit != BoolSet(True):
            continue
        mutator.predicate_terminate(op)


def no_other_constrains(
    po: ParameterOperatable,
    *other: ConstrainableExpression,
    unfulfilled_only: bool = False,
) -> bool:
    no_other_constraints = (
        len(
            [
                x
                for x in get_constrained_expressions_involved_in(po).difference(other)
                if not unfulfilled_only or not x._solver_terminated
            ]
        )
        == 0
    )
    return no_other_constraints and not po.has_implicit_constraints_recursive()


@dataclass
class FlattenAssociativeResult[T]:
    extracted_operands: list[ParameterOperatable.All]
    """
    Extracted operands
    """
    destroyed_operations: set[T]
    """
    ParameterOperables that got flattened and thus are not used anymore
    """


def flatten_associative[T: Associative](
    to_flatten: T,  # type: ignore
    check_destructable: Callable[[Expression, Expression], bool],
):
    """
    Recursively extract operands from nested expressions of the same type.

    ```
    (A + B) + C + (D + E)
       Y    Z   X    W
    flatten(Z) -> flatten(Y) + [C] + flatten(X)
      flatten(Y) -> [A, B]
      flatten(X) -> flatten(W) + [D, E]
      flatten(W) -> [C]
    -> [A, B, C, D, E] = extracted operands
    -> {Z, X, W, Y} = destroyed operations
    ```

    Note: `W` flattens only for right associative operations

    Args:
    - check_destructable(expr, parent_expr): function to check if an expression is
        allowed to be flattened (=destructed)
    """

    out = FlattenAssociativeResult[T](
        extracted_operands=[],
        destroyed_operations=set(),
    )

    def can_be_flattened(o: ParameterOperatable.All) -> TypeGuard[T]:
        if not isinstance(to_flatten, Associative):
            return False
        if not isinstance(to_flatten, FullyAssociative):
            if to_flatten.operands[0] is not o:
                return False
        return type(o) is type(to_flatten) and check_destructable(o, to_flatten)

    non_compressible_operands, nested_compressible_operations = partition(
        can_be_flattened,
        to_flatten.operands,
    )
    out.extracted_operands.extend(non_compressible_operands)

    nested_extracted_operands = []
    for nested_to_flatten in nested_compressible_operations:
        out.destroyed_operations.add(nested_to_flatten)

        res = flatten_associative(nested_to_flatten, check_destructable)
        nested_extracted_operands += res.extracted_operands
        out.destroyed_operations.update(res.destroyed_operations)

    out.extracted_operands.extend(nested_extracted_operands)

    return out


def is_replacable(
    repr_map: "REPR_MAP",
    to_replace: Expression,
    parent_expr: Expression,
) -> bool:
    """
    Check if an expression can be replaced.
    Only possible if not in use somewhere else or already mapped to new expr
    """
    if to_replace in repr_map:  # overly restrictive: equivalent replacement would be ok
        return False
    if to_replace.get_operations() != {parent_expr}:
        return False
    return True


def is_constrained(po: ParameterOperatable) -> TypeGuard[ConstrainableExpression]:
    return isinstance(po, ConstrainableExpression) and po.constrained


def get_lit_mapping_from_lit_expr(
    expr: Is | IsSubset,
) -> tuple[ParameterOperatable, SolverLiteral]:
    assert is_alias_is_literal(expr) or is_subset_literal(expr)
    return next(iter(expr.operatable_operands)), next(
        iter(expr.get_literal_operands().values())
    )


def get_params_for_expr(expr: Expression) -> set[Parameter]:
    param_ops = {op for op in expr.operatable_operands if isinstance(op, Parameter)}
    expr_ops = {op for op in expr.operatable_operands if isinstance(op, Expression)}

    return param_ops | {op for e in expr_ops for op in get_params_for_expr(e)}


# TODO make generator
def get_expressions_involved_in[T: Expression](
    p: ParameterOperatable,
    type_filter: type[T] = Expression,
    include_root: bool = False,
    up_only: bool = True,
) -> set[T]:
    dependants = p.get_operations(recursive=True)
    if isinstance(p, Expression):
        if include_root:
            dependants.add(p)

        if not up_only:
            dependants.update(p.get_expression_operands(recursive=True))

    res = {p for p in dependants if isinstance(p, type_filter)}
    return res


def get_constrained_expressions_involved_in[T: ConstrainableExpression](
    p: ParameterOperatable,
    type_filter: type[T] = ConstrainableExpression,
) -> set[T]:
    res = {p for p in get_expressions_involved_in(p, type_filter) if p.constrained}
    return res


# TODO write tests for this
def get_correlations(
    expr: Expression,
    exclude: set[Expression] | None = None,
):
    # TODO: might want to check if expr has aliases because those are correlated too

    if exclude is None:
        exclude = set()

    exclude.add(expr)
    exclude.update(get_constrained_expressions_involved_in(expr, Is))
    operables = [o for o in expr.operands if isinstance(o, ParameterOperatable)]

    excluded = {
        e for e in exclude if isinstance(e, ConstrainableExpression) and e.constrained
    }

    op_set = set(operables)

    exprs = {o: get_constrained_expressions_involved_in(o, Is) for o in op_set}
    # check disjoint sets
    for e1, e2 in combinations(operables, 2):
        if e1 is e2:
            yield e1, e2, exprs[e1].difference(excluded)
        overlap = (exprs[e1] & exprs[e2]).difference(excluded)
        if overlap:
            yield e1, e2, overlap


def find_unique_params(po: ParameterOperatable) -> set[ParameterOperatable]:
    match po:
        case Parameter():
            return {po}
        case Expression():
            return {p for op in po.operands for p in find_unique_params(op)}
        case _:
            return set()


def count_param_occurrences(po: ParameterOperatable) -> dict[Parameter, int]:
    counts: dict[Parameter, int] = defaultdict(int)

    match po:
        case Parameter():
            counts[po] += 1
        case Expression():
            for op in po.operands:
                for param, count in count_param_occurrences(op).items():
                    counts[param] += count

    return counts


def is_correlatable_literal(op):
    if not is_literal(op):
        return False
    return op.is_single_element() or op.is_empty()


def is_replacable_by_literal(op: ParameterOperatable.All):
    if not isinstance(op, ParameterOperatable):
        return None

    # special case for Is(True, True) due to alias_is_literal check
    if isinstance(op, Is) and {BoolSet(True)} == set(op.operands):
        return BoolSet(True)

    lit = try_extract_literal(op, allow_subset=False)
    if lit is None:
        return None
    if not is_correlatable_literal(lit):
        return None
    return lit


def find_congruent_expression[T: CanonicalExpression](
    expr_factory: type[T],
    *operands: SolverAll,
    mutator: "Mutator",
    allow_uncorrelated: bool = False,
) -> T | None:
    non_lits = [op for op in operands if isinstance(op, ParameterOperatable)]
    literal_expr = all(is_literal(op) or is_literal_expression(op) for op in operands)
    if literal_expr:
        lit_ops = {
            op
            for op in mutator.nodes_of_type(
                expr_factory, created_only=False, include_terminated=True
            )
            if is_literal_expression(op)
            # check congruence
            and Expression.are_pos_congruent(
                op.operands,
                cast(Sequence[ParameterOperatable.All], operands),
                allow_uncorrelated=allow_uncorrelated,
            )
        }
        if lit_ops:
            return next(iter(lit_ops))
        return None

    # TODO: might have to check in repr_map
    candidates = [
        expr for expr in non_lits[0].get_operations() if isinstance(expr, expr_factory)
    ]
    for c in candidates:
        # TODO congruence check instead
        if c.operands == operands:
            return c
    return None


def get_supersets(
    op: ParameterOperatable,
) -> dict[ParameterOperatable | SolverLiteral, IsSubset]:
    return {
        e.operands[1]: e
        for e in op.get_operations(IsSubset, constrained_only=True)
        if e.operands[0] is op
    }


def get_aliases(
    op: ParameterOperatable,
) -> dict[ParameterOperatable | SolverLiteral, Is]:
    return {
        e.get_other_operand(op): e for e in op.get_operations(Is, constrained_only=True)
    }


def get_all_aliases(mutator: "Mutator") -> set[Is]:
    return {
        op
        for op in mutator.nodes_of_type(Is, include_terminated=True)
        if op.constrained
    }


def get_all_subsets(mutator: "Mutator") -> set[IsSubset]:
    return {
        op
        for op in mutator.nodes_of_type(IsSubset, include_terminated=True)
        if op.constrained
    }


# TODO move to Mutator
def get_graphs(values: Iterable) -> list[Graph]:
    return unique_ref(
        p.get_graph() if isinstance(p, Node) else p
        for p in values
        if isinstance(p, (Node, Graph))
    )


def merge_parameters(params: Iterable[Parameter]) -> Parameter:
    params = list(params)

    domain = Domain.get_shared_domain(*(p.domain for p in params))
    # intersect ranges

    # heuristic:
    # intersect soft sets
    soft_sets = {p.soft_set for p in params if p.soft_set is not None}
    soft_set = None
    if soft_sets:
        soft_set = Quantity_Interval_Disjoint.op_intersect_intervals(*soft_sets)

    # heuristic:
    # get median
    guesses = {p.guess for p in params if p.guess is not None}
    guess = None
    if guesses:
        guess = median(guesses)  # type: ignore

    # heuristic:
    # max tolerance guess
    tolerance_guesses = {
        p.tolerance_guess for p in params if p.tolerance_guess is not None
    }
    tolerance_guess = None
    if tolerance_guesses:
        tolerance_guess = max(tolerance_guesses)

    likely_constrained = any(p.likely_constrained for p in params)

    return Parameter(
        domain=domain,
        # In stage-0 removed: within, units
        soft_set=soft_set,
        guess=guess,
        tolerance_guess=tolerance_guess,
        likely_constrained=likely_constrained,
    )


def debug_name_mappings(
    context: ParameterOperatable.ReprContext,
    *gs: Graph,
    print_out: Callable[[str], None] = logger.debug,
):
    table = Table(title="Name mappings", show_lines=True)
    table.add_column("Variable name")
    table.add_column("Node name")

    for g in gs:
        for p in sorted(
            GraphFunctions(g).nodes_of_type(Parameter), key=Parameter.get_full_name
        ):
            table.add_row(p.compact_repr(context), p.get_full_name())

    if table.rows:
        console = Console(record=True, width=80, file=io.StringIO())
        console.print(table)
        print_out(console.export_text(styles=True))


type SolverAlgorithmFunc = "Callable[[Mutator], None]"


@dataclass(frozen=True)
class SolverAlgorithm:
    name: str
    func: SolverAlgorithmFunc
    single: bool
    terminal: bool

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


def algorithm(
    name: str,
    single: bool = False,
    terminal: bool = True,
) -> Callable[[SolverAlgorithmFunc], SolverAlgorithm]:
    """
    Decorator to wrap an algorithm function

    Args:
    - single: if True, the algorithm is only applied once in the beginning.
        All other algorithms assume this one ran before
    - terminal: Results are invalid if graph is mutated after solver is run
    """

    if not hasattr(algorithm, "_registered_algorithms"):
        algorithm._registered_algorithms = []

    def decorator(func: SolverAlgorithmFunc) -> SolverAlgorithm:
        @wraps(func)
        def wrapped(*args, **kwargs):
            return func(*args, **kwargs)

        out = SolverAlgorithm(
            name=name,
            func=wrapped,
            single=single,
            terminal=terminal,
        )
        algorithm._registered_algorithms.append(out)

        return out

    return decorator


def get_algorithms() -> list[SolverAlgorithm]:
    return algorithm._registered_algorithms
