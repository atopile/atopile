# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from statistics import median
from typing import Callable, Iterable, Iterator, TypeGuard, cast

from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.graphinterface import GraphInterfaceSelf
from faebryk.core.parameter import (
    Abs,
    Add,
    And,
    ConstrainableExpression,
    Difference,
    Divide,
    Domain,
    Expression,
    GreaterOrEqual,
    GreaterThan,
    Intersection,
    Is,
    IsSubset,
    Log,
    Multiply,
    Not,
    Or,
    Parameter,
    ParameterOperatable,
    Power,
    Predicate,
    Round,
    Sin,
    Subtract,
    SymmetricDifference,
    Union,
    Xor,
)
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval,
    Quantity_Interval_Disjoint,
    Quantity_Set,
    Quantity_Set_Discrete,
    QuantityLike,
    QuantityLikeR,
)
from faebryk.libs.sets.sets import BoolSet, P_Set
from faebryk.libs.units import HasUnit, Quantity, Unit, quantity
from faebryk.libs.util import (
    EquivalenceClasses,
    KeyErrorAmbiguous,
    not_none,
    partition,
    unique_ref,
)

logger = logging.getLogger(__name__)

Commutative = (
    Add | Multiply | And | Or | Xor | Union | Intersection | SymmetricDifference
)
FullyAssociative = Add | Multiply | And | Or | Xor | Union | Intersection
LeftAssociative = Subtract | Divide | Difference
Associative = FullyAssociative | LeftAssociative


class Contradiction(Exception):
    pass


class ContradictionByLiteral(Contradiction):
    pass


CanonicalNumber = Quantity_Interval_Disjoint | Quantity_Set_Discrete
CanonicalBoolean = BoolSet
CanonicalEnum = P_Set[Enum]
# TODO Canonical set?
CanonicalLiteral = CanonicalNumber | CanonicalBoolean | CanonicalEnum
SolverLiteral = CanonicalLiteral

CanonicalNumericOperation = Add | Multiply | Power | Round | Abs | Sin | Log
CanonicalLogicOperation = Or | Not
CanonicalSeticOperation = Intersection | Union | SymmetricDifference | Difference
CanonicalPredicate = GreaterOrEqual | IsSubset | Is | GreaterThan


CanonicalOperation = (
    CanonicalNumericOperation
    | CanonicalLogicOperation
    | CanonicalSeticOperation
    | CanonicalPredicate
)


def make_lit(val):
    return P_Set.from_value(val)


def try_extract_literal(po) -> SolverLiteral | None:
    lit = ParameterOperatable.try_extract_literal(po)
    if lit is None:
        return None
    assert isinstance(lit, (CanonicalNumber, BoolSet, P_Set))
    return lit


def try_extract_numeric_literal(po) -> CanonicalNumber | None:
    lit = try_extract_literal(po)
    if lit is None:
        return None
    assert isinstance(lit, CanonicalNumber)
    return lit


def try_extract_all_literals[T: P_Set](
    expr: Expression,
    op: type[Expression] | None = None,
    lit_type: type[T] = P_Set,
    accept_partial: bool = False,
) -> list[T] | None:
    try:
        as_lits = [
            ParameterOperatable.try_extract_literal(o, op) for o in expr.operands
        ]
    except KeyErrorAmbiguous as e:
        raise ContradictionByLiteral(
            f"Duplicate unequal is literals: {e.duplicates}"
        ) from e

    if None in as_lits and not accept_partial:
        return None
    as_lits = [lit for lit in as_lits if lit is not None]
    assert all(isinstance(lit, lit_type) for lit in as_lits)
    return cast(list[T], as_lits)


def alias_is_literal(po: ParameterOperatable, literal: ParameterOperatable.Literal):
    existing = po.try_get_literal()
    literal = make_lit(literal)

    if existing is not None:
        if existing == literal:
            return
        raise ContradictionByLiteral(f"{existing} != {literal}")
    po.alias_is(literal)


def alias_is_and_check_constrained(
    expr: ConstrainableExpression, value: BoolSet | bool
):
    if not isinstance(value, BoolSet):
        value = BoolSet(value)
    alias_is_literal(expr, value)
    if not value and expr.constrained:
        raise ContradictionByLiteral(f"False and constrained: {expr}")


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

    @dataclass
    class Result[T2]:
        extracted_operands: list[ParameterOperatable.All]
        """
        Extracted operands
        """
        destroyed_operations: set[T2]
        """
        ParameterOperables that got flattened and thus are not used anymore
        """

    out = Result[T](
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

    if len(nested_extracted_operands) > 0 and logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"FLATTENED {type(to_flatten).__name__} {to_flatten} -> {nested_extracted_operands}"
        )

    out.extracted_operands.extend(nested_extracted_operands)

    return out


def parameter_ops_eq_classes(
    G: Graph,
) -> list[set[ParameterOperatable]]:
    """
    Return for dict[key, set[parameter_operatable]]
    which maps from each obj to its alias/eq class
    Note: if eq class only single obj, it is still included
    """

    non_predicate_objs = (
        GraphFunctions(G)
        .nodes_of_type(ParameterOperatable)
        .difference(GraphFunctions(G).nodes_of_type(Predicate))
    )
    full_eq = EquivalenceClasses[ParameterOperatable](non_predicate_objs)

    is_exprs = [e for e in GraphFunctions(G).nodes_of_type(Is) if e.constrained]

    for is_expr in is_exprs:
        full_eq.add_eq(*is_expr.operatable_operands)

    obvious_eq = defaultdict(list)
    for p in non_predicate_objs:
        obvious_eq[p.obviously_eq_hash()].append(p)

    for candidates in obvious_eq.values():
        if len(candidates) <= 1:
            continue
        logger.debug(f"#obvious eq candidates: {len(candidates)}")
        for i, p in enumerate(candidates):
            for q in candidates[:i]:
                if p.obviously_eq(q):
                    full_eq.add_eq(p, q)
                    break

    return full_eq.get()


def is_replacable(
    repr_map: "Mutator.REPR_MAP",
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


def parameter_dependency_classes(G: Graph) -> list[set[Parameter]]:
    # TODO just get passed
    params = [
        p
        for p in GraphFunctions(G).nodes_of_type(Parameter)
        if get_constrained_expressions_involved_in(p)
    ]

    related = EquivalenceClasses[Parameter](params)

    eq_exprs = [e for e in GraphFunctions(G).nodes_of_type(Predicate) if e.constrained]

    for eq_expr in eq_exprs:
        params = get_params_for_expr(eq_expr)
        related.add_eq(*params)

    return related.get()


def get_params_for_expr(expr: Expression) -> set[Parameter]:
    param_ops = {op for op in expr.operatable_operands if isinstance(op, Parameter)}
    expr_ops = {op for op in expr.operatable_operands if isinstance(op, Expression)}

    return param_ops | {op for e in expr_ops for op in get_params_for_expr(e)}


def get_constrained_expressions_involved_in(
    p: ParameterOperatable,
) -> set[ConstrainableExpression]:
    # p.self -> p.operated_on -> e1.operates_on -> e1.self
    dependants = p.bfs_node(
        lambda path: isinstance(path[-1].node, ParameterOperatable)
        and (
            # self
            isinstance(path[-1], GraphInterfaceSelf)
            # operated on
            or path[-1].node.operated_on is path[-1]
            # operated on -> operates on
            or (
                len(path) >= 2
                and isinstance(path[-2].node, ParameterOperatable)
                and path[-2].node.operated_on is path[-2]
                and isinstance(path[-1].node, Expression)
                and path[-1].node.operates_on is path[-1]
            )
        )
    )
    res = {
        p
        for p in dependants
        if isinstance(p, ConstrainableExpression) and p.constrained
    }
    return res


# TODO move to Mutator
def get_graphs(values: Iterable) -> list[Graph]:
    return unique_ref(
        p.get_graph() for p in values if isinstance(p, ParameterOperatable)
    )


NumericLiteral = QuantityLike | Quantity_Interval_Disjoint | Quantity_Interval
NumericLiteralR = (*QuantityLikeR, Quantity_Interval_Disjoint, Quantity_Interval)
BoolLiteral = BoolSet | bool


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


# TODO use Mutator everywhere instead of repr_maps
class Mutator:
    type REPR_MAP = dict[ParameterOperatable, ParameterOperatable]

    def __init__(
        self,
        G: Graph,
        repr_map: REPR_MAP | None = None,
    ) -> None:
        self.G = G
        self.repr_map = repr_map or {}
        self.removed = set()
        self.copied = set()

    def has_been_mutated(self, po: ParameterOperatable) -> bool:
        return po in self.repr_map

    def get_mutated(self, po: ParameterOperatable) -> ParameterOperatable:
        return self.repr_map[po]

    def _mutate[T: ParameterOperatable](self, po: ParameterOperatable, new_po: T) -> T:
        """
        Low-level mutation function, you are on your own.
        Consider using mutate_parameter or mutate_expression instead.
        """
        if self.has_been_mutated(po):
            if self.get_mutated(po) is not new_po:
                raise ValueError("already mutated")

        if self.is_removed(po):
            raise ValueError("Object marked removed")

        self.repr_map[po] = new_po
        return new_po

    def _override_repr(self, po: ParameterOperatable, new_po: ParameterOperatable):
        """
        Do not use this if you don't understand the consequences.
        Honestly I don't.
        """
        self.repr_map[po] = new_po

    def mutate_parameter(
        self,
        param: Parameter,
        units: Unit | Quantity | None = None,
        domain: Domain | None = None,
        soft_set: Quantity_Interval_Disjoint | Quantity_Interval | None = None,
        guess: Quantity | int | float | None = None,
        tolerance_guess: float | None = None,
        likely_constrained: bool | None = None,
    ) -> Parameter:
        if param in self.repr_map:
            out = self.get_mutated(param)
            assert isinstance(out, Parameter)
            assert out.units == units
            assert out.domain == domain
            assert out.soft_set == soft_set
            assert out.guess == guess
            assert out.tolerance_guess == tolerance_guess
            assert out.likely_constrained == likely_constrained
            return out

        new_param = Parameter(
            units=units if units is not None else param.units,
            within=None,
            domain=domain if domain is not None else param.domain,
            soft_set=soft_set if soft_set is not None else param.soft_set,
            guess=guess if guess is not None else param.guess,
            tolerance_guess=tolerance_guess
            if tolerance_guess is not None
            else param.tolerance_guess,
            likely_constrained=likely_constrained
            if likely_constrained is not None
            else param.likely_constrained,
        )

        return self._mutate(param, new_param)

    def mutate_expression(
        self,
        expr: Expression,
        operands: Iterable[ParameterOperatable.All] | None = None,
        expression_factory: Callable[..., Expression] | None = None,
    ) -> Expression:
        if expr in self.repr_map:
            out = self.get_mutated(expr)
            assert isinstance(out, Expression)
            # TODO more checks
            return out

        if expression_factory is None:
            expression_factory = type(expr)

        if operands is None:
            operands = expr.operands

        new_operands = [self.get_copy(op) for op in operands]
        new_expr = expression_factory(*new_operands)

        for op in new_operands:
            if isinstance(op, ParameterOperatable):
                assert op.get_graph() == new_expr.get_graph()
        if isinstance(expr, ConstrainableExpression):
            cast(ConstrainableExpression, new_expr).constrained = expr.constrained

        return self._mutate(expr, new_expr)

    def mutate_expression_with_op_map(
        self,
        expr: Expression,
        operand_mutator: Callable[[int, ParameterOperatable], ParameterOperatable.All],
        expression_factory: Callable[..., Expression] | None = None,
    ) -> Expression:
        """
        operand_mutator: Only allowed to return old Graph objects
        """
        return self.mutate_expression(
            expr,
            operands=[operand_mutator(i, op) for i, op in enumerate(expr.operands)],
            expression_factory=expression_factory,
        )

    def get_copy(self, obj: ParameterOperatable.All) -> ParameterOperatable.All:
        if not isinstance(obj, ParameterOperatable):
            return obj

        if self.has_been_mutated(obj):
            return self.get_mutated(obj)

        # purely for debug
        self.copied.add(obj)

        if isinstance(obj, Expression):
            return self.mutate_expression(obj)
        elif isinstance(obj, Parameter):
            return self.mutate_parameter(obj)

        assert False

    def remove(self, *po: ParameterOperatable):
        if any(p in self.repr_map for p in po):
            raise ValueError("Object already in repr_map")
        self.removed.update(po)

    def is_removed(self, po: ParameterOperatable) -> bool:
        return po in self.removed

    def copy_unmutated(
        self,
        exclude_filter: Callable[[ParameterOperatable], bool] | None = None,
    ):
        if exclude_filter is None:
            exclude_filter = self.is_removed

        # TODO might not need to sort
        other_param_op = ParameterOperatable.sort_by_depth(
            (
                p
                for p in GraphFunctions(self.G).nodes_of_type(ParameterOperatable)
                if not self.has_been_mutated(p) and not exclude_filter(p)
            ),
            ascending=True,
        )
        for o in other_param_op:
            self.get_copy(o)

    @property
    def dirty(self) -> bool:
        return bool(self.removed or self.repr_map)

    def close(self) -> tuple[REPR_MAP, bool]:
        if not self.dirty:
            return {
                po: po
                for po in GraphFunctions(self.G).nodes_of_type(ParameterOperatable)
            }, False
        self.copy_unmutated()

        assert self.G not in get_graphs(self.repr_map.values())
        return self.repr_map, True

    def debug_print(self):
        import sys

        if getattr(sys, "gettrace", lambda: None)():
            log = print
        else:
            log = logger.info

        for s, d in self.repr_map.items():
            if s in self.copied:
                continue

            if isinstance(d, Parameter) and isinstance(s, Parameter):
                log(
                    f"{s!r}({s.units}, {s.domain}, {s.within}) -> {d!r}({d.units}, {d.domain}, {s.within})"
                )
            else:
                log(f"{s!r} -> {d!r}")

        for s in self.removed:
            log(f"{s!r} -> removed")


class Mutators:
    def __init__(self, *graphs: Graph):
        self.mutators = [Mutator(g) for g in graphs]

    def close(self) -> tuple[Mutator.REPR_MAP, list[Graph], bool]:
        if not any(m.dirty for m in self.mutators):
            return {}, [], False

        repr_map = {}
        for m in self.mutators:
            repr_map.update(m.close()[0])
        return repr_map, get_graphs(repr_map.values()), True

    def run(self, algo: Callable[[Mutator], None]):
        for m in self.mutators:
            algo(m)

    def __iter__(self) -> Iterator[Mutator]:
        return iter(self.mutators)

    @staticmethod
    def concat_repr_maps(*repr_maps: Mutator.REPR_MAP) -> Mutator.REPR_MAP:
        assert repr_maps
        if len(repr_maps) == 1:
            return repr_maps[0]

        concatenated = {}
        for original_obj in repr_maps[0].keys():
            chain_end = original_obj
            chain_interrupted = False
            for m in repr_maps:
                # CONSIDER: I think we can assert this
                if not isinstance(chain_end, ParameterOperatable):
                    break
                if chain_end not in m:
                    logger.warning(
                        f"chain_end {original_obj} -> {chain_end} interrupted"
                    )
                    chain_interrupted = True
                    break
                chain_end = m[chain_end]
            if not chain_interrupted:
                concatenated[original_obj] = chain_end
        return concatenated

    class ReprMap:
        def __init__(self, repr_map: Mutator.REPR_MAP):
            self.repr_map = repr_map

        def try_get_literal(
            self, param: ParameterOperatable, e_type: type[Is | IsSubset] | None = None
        ) -> ParameterOperatable.Literal | None:
            if e_type is Is or e_type is None:
                lit = self.repr_map[param].try_get_literal(e_type)
            elif e_type is IsSubset:
                lit = self.repr_map[param].try_get_literal_subset()
            else:
                assert False

            if lit is None:
                return None
            res = P_Set.from_value(lit)
            if isinstance(res, Quantity_Set):
                return res * quantity(1, HasUnit.get_units(param))
            return res

        def __getitem__(
            self, param: ParameterOperatable
        ) -> ParameterOperatable.Literal:
            return not_none(self.try_get_literal(param))

        def __contains__(self, param: ParameterOperatable) -> bool:
            return param in self.repr_map

    @staticmethod
    def create_concat_repr_map(*repr_maps: Mutator.REPR_MAP) -> ReprMap:
        return Mutators.ReprMap(Mutators.concat_repr_maps(*repr_maps))
