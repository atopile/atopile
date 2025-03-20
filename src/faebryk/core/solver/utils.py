# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from statistics import median
from types import NoneType
from typing import (
    TYPE_CHECKING,
    Callable,
    Counter,
    Iterable,
    Mapping,
    Sequence,
    TypeGuard,
    cast,
)

from faebryk.core.graph import Graph
from faebryk.core.node import Node
from faebryk.core.parameter import (
    Associative,
    CanonicalExpression,
    CanonicalLiteral,
    CanonicalNumber,
    Commutative,
    ConstrainableExpression,
    Domain,
    Expression,
    FullyAssociative,
    Is,
    IsSubset,
    Multiply,
    Parameter,
    ParameterOperatable,
    Power,
)
from faebryk.core.solver.solver import LOG_PICK_SOLVE
from faebryk.libs.logging import rich_to_string
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval_Disjoint,
)
from faebryk.libs.sets.sets import BoolSet, P_Set, as_lit
from faebryk.libs.util import (
    ConfigFlag,
    ConfigFlagFloat,
    ConfigFlagInt,
    KeyErrorAmbiguous,
    groupby,
    partition,
    unique,
    unique_ref,
)

if TYPE_CHECKING:
    from faebryk.core.solver.mutator import Mutator

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
TIMEOUT = ConfigFlagFloat("STIMEOUT", default=150, descr="Solver timeout").get()
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
    def __init__(
        self,
        msg: str,
        involved: list[ParameterOperatable],
        mutator: "Mutator",
    ):
        super().__init__(msg)
        self.msg = msg
        self.involved_exprs = involved
        self.mutator = mutator

    def __str__(self):
        tracebacks = {
            p: self.mutator.mutation_map.get_traceback(p) for p in self.involved_exprs
        }
        print_ctx = self.mutator.mutation_map.input_print_context

        def _get_origins(p: ParameterOperatable) -> list[ParameterOperatable]:
            return tracebacks[p].get_leaves()

        # TODO reenable
        if LOG_PICK_SOLVE:
            for p, tb in tracebacks.items():
                tb_str = rich_to_string(tb.filtered().as_rich_tree())
                logger.warning(tb_str)

        origins = {p: _get_origins(p) for p in self.involved_exprs}
        origins_str = "\n".join(
            [
                f" - {origin.compact_repr(print_ctx, use_name=True)}\n"
                + "\n".join(
                    f"   - {o.compact_repr(print_ctx, use_name=True)}"
                    for o in set(origins[origin])
                )
                for origin in origins
            ]
        )

        return f"Contradiction: {self.msg}\n\nOrigins:\n{origins_str}"


class ContradictionByLiteral(Contradiction):
    def __init__(
        self,
        msg: str,
        involved: list[ParameterOperatable],
        literals: list["SolverLiteral"],
        mutator: "Mutator",
    ):
        super().__init__(msg, involved, mutator)
        self.literals = literals

    def __str__(self):
        literals_str = "\n".join(f" - {lit}" for lit in self.literals)
        return f"{super().__str__()}\n\nLiterals:\n{literals_str}"


SolverLiteral = CanonicalLiteral
SolverAll = ParameterOperatable | SolverLiteral
SolverAllExtended = ParameterOperatable.All | SolverLiteral


# TODO move
def get_graphs(values: Iterable) -> list[Graph]:
    return unique_ref(
        p.get_graph() if isinstance(p, Node) else p
        for p in values
        if isinstance(p, (Node, Graph))
    )


# alias
make_lit = as_lit


class MutatorUtils:
    def __init__(self, mutator: "Mutator"):
        self.mutator = mutator

    # TODO should be part of mutator
    def try_extract_literal(
        self,
        po: ParameterOperatable,
        allow_subset: bool = False,
        check_pre_transform: bool = False,
    ) -> SolverLiteral | None:
        pos = {po}

        # TODO should be mutator api
        if check_pre_transform and po in self.mutator.transformations.mutated.values():
            pos |= {
                k
                for k, v in self.mutator.transformations.mutated.items()
                if v is po and k not in self.mutator.transformations.removed
            }

        lits = set()
        try:
            for po in pos:
                lit = ParameterOperatable.try_extract_literal(
                    po, allow_subset=allow_subset
                )
                if lit is not None:
                    lits.add(lit)
        except KeyErrorAmbiguous as e:
            raise ContradictionByLiteral(
                "Duplicate unequal is literals",
                involved=[po],
                literals=e.duplicates,
                mutator=self.mutator,
            ) from e
        if len(lits) > 1:
            raise ContradictionByLiteral(
                "Multiple literals found",
                involved=list(pos),
                literals=list(lits),
                mutator=self.mutator,
            )
        lit = next(iter(lits), None)
        assert isinstance(lit, (CanonicalNumber, BoolSet, P_Set, NoneType))
        return lit

    def try_extract_literal_info(
        self,
        po: ParameterOperatable,
    ) -> tuple[SolverLiteral | None, bool]:
        """
        returns (literal, is_alias)
        """
        lit = self.try_extract_literal(po, allow_subset=False)
        if lit is not None:
            return lit, True
        lit = self.try_extract_literal(po, allow_subset=True)
        return lit, False

    def try_extract_lit_op(
        self, po: ParameterOperatable
    ) -> tuple[SolverLiteral, Is | IsSubset] | None:
        aliases = self.get_aliases(po)
        alias_lits = [(k, v) for k, v in aliases.items() if self.is_literal(k)]
        if alias_lits:
            unique_lits = unique(alias_lits, lambda x: x[0])
            if len(unique_lits) > 1:
                raise ContradictionByLiteral(
                    "Multiple alias literals found",
                    involved=[po] + [x[1] for x in unique_lits],
                    literals=[x[0] for x in unique_lits],
                    mutator=self.mutator,
                )
            return alias_lits[0]
        subsets = self.get_supersets(po)
        subset_lits = [(k, vs) for k, vs in subsets.items() if self.is_literal(k)]
        # TODO this is weird
        if subset_lits:
            for k, vs in subset_lits:
                if all(k.is_subset_of(other_k) for other_k, _ in subset_lits):  # type: ignore
                    return k, vs[0]
        return None

    def map_extract_literals(
        self,
        expr: Expression,
        allow_subset: bool = False,
    ) -> tuple[list[SolverAll], list[ParameterOperatable]]:
        out = []
        any_lit = []
        for op in expr.operands:
            if self.is_literal(op):
                out.append(op)
                continue
            lit = self.try_extract_literal(op, allow_subset=allow_subset)
            if lit is None:
                out.append(op)
                continue
            out.append(lit)
            any_lit.append(op)
        return out, any_lit

    def alias_is_literal(
        self,
        po: ParameterOperatable,
        literal: ParameterOperatable.Literal | SolverLiteral,
        from_ops: Sequence[ParameterOperatable] | None = None,
        terminate: bool = False,
    ) -> Is | BoolSet:
        literal = make_lit(literal)
        existing = self.try_extract_literal(po, check_pre_transform=True)
        if existing is not None:
            if existing == literal:
                if terminate:
                    for op in po.get_operations(Is, constrained_only=True):
                        if existing in op.operands:
                            self.mutator.predicate_terminate(op)
                    return make_lit(True)
                return make_lit(True)
            raise ContradictionByLiteral(
                "Tried alias to different literal",
                involved=[po],
                literals=[existing, literal],
                mutator=self.mutator,
            )
        # prevent (A is X) is X
        if isinstance(po, Is):
            if literal in po.get_operand_literals().values():
                return make_lit(True)
        if (ss_lit := self.try_extract_literal(po, allow_subset=True)) is not None:
            if not ss_lit.is_superset_of(literal):  # type: ignore
                raise ContradictionByLiteral(
                    "Tried alias to literal incompatible with subset",
                    involved=[po],
                    literals=[ss_lit, literal],
                    mutator=self.mutator,
                )
        out = self.mutator.create_expression(
            Is,
            po,
            literal,
            from_ops=from_ops,
            constrain=True,
            # already checked for uncorrelated lit, op needs to be correlated
            allow_uncorrelated=False,
            check_exists=False,
            _relay=False,
        )
        if terminate:
            self.mutator.predicate_terminate(out)
        return out

    def subset_literal(
        self,
        po: ParameterOperatable,
        literal: ParameterOperatable.Literal | SolverLiteral,
        from_ops: Sequence[ParameterOperatable] | None = None,
    ) -> IsSubset | Is | BoolSet:
        literal = make_lit(literal)

        if literal.is_empty():
            raise ContradictionByLiteral(
                "Tried subset to empty set",
                involved=[po],
                literals=[literal],
                mutator=self.mutator,
            )

        # TODO do we need to add check_pre_transform to this function?
        existing = self.try_extract_lit_op(po)
        if existing is not None:
            ex_lit, ex_op = existing
            if isinstance(ex_op, Is):
                if not ex_lit.is_subset_of(literal):  # type: ignore #TODO
                    raise ContradictionByLiteral(
                        "Tried subset to different literal",
                        involved=[po],
                        literals=[ex_lit, literal],
                        mutator=self.mutator,
                    )
                return ex_op

            # no point in adding more general subset
            if ex_lit.is_subset_of(literal):  # type: ignore #TODO
                return ex_op
            # other cases handled by intersect subsets algo

        return self.mutator.create_expression(
            IsSubset,
            po,
            literal,
            from_ops=from_ops,
            constrain=True,
            # already checked for uncorrelated lit, op needs to be correlated
            allow_uncorrelated=False,
            check_exists=False,
            _relay=False,
        )  # type: ignore

    def alias_to(
        self,
        po: ParameterOperatable | SolverLiteral,
        to: ParameterOperatable | SolverLiteral,
        check_existing: bool = True,
        from_ops: Sequence[ParameterOperatable] | None = None,
        terminate: bool = False,
    ) -> Is | BoolSet:
        from faebryk.core.solver.symbolic.pure_literal import (
            _exec_pure_literal_expressions,
        )

        from_ops = from_ops or []
        if isinstance(to, CanonicalExpression):
            res = _exec_pure_literal_expressions(to)
            if res is not None:
                to = res

        to_is_lit = self.is_literal(to)
        po_is_lit = self.is_literal(po)
        if po_is_lit:
            if not to_is_lit:
                to, po = po, to
                to_is_lit, po_is_lit = po_is_lit, to_is_lit
            else:
                if po != to:  # type: ignore
                    raise ContradictionByLiteral(
                        "Incompatible literal aliases",
                        involved=list(from_ops),
                        literals=[po, to],  # type: ignore
                        mutator=self.mutator,
                    )
                return make_lit(True)
        assert isinstance(po, ParameterOperatable)
        from_ops = [po] + list(from_ops)
        if to_is_lit:
            assert check_existing
            to = cast(SolverLiteral, to)
            return self.alias_is_literal(po, to, from_ops=from_ops, terminate=terminate)

        # not sure why this would be needed anyway
        if terminate:
            raise NotImplementedError("Terminate not implemented for non-literals")

        # check if alias exists
        if isinstance(po, Expression) and isinstance(to, Expression) and check_existing:
            if overlap := (
                po.get_operations(Is, constrained_only=True)
                & to.get_operations(Is, constrained_only=True)
            ):
                return next(iter(overlap))

        return self.mutator.create_expression(
            Is,
            po,
            to,
            from_ops=from_ops,
            constrain=True,
            check_exists=check_existing,
            allow_uncorrelated=True,
            _relay=False,
        )  # type: ignore

    def subset_to(
        self,
        po: ParameterOperatable | SolverLiteral,
        to: ParameterOperatable | SolverLiteral,
        check_existing: bool = True,
        from_ops: Sequence[ParameterOperatable] | None = None,
    ) -> IsSubset | Is | BoolSet:
        from faebryk.core.solver.symbolic.pure_literal import (
            _exec_pure_literal_expressions,
        )

        from_ops = from_ops or []
        from_ops = [
            x for x in [po, to] + list(from_ops) if isinstance(x, ParameterOperatable)
        ]

        if isinstance(to, CanonicalExpression):
            res = _exec_pure_literal_expressions(to)
            if res is not None:
                to = res

        to_is_lit = self.is_literal(to)
        po_is_lit = self.is_literal(po)

        if to_is_lit and po_is_lit:
            if not po.is_subset_of(to):  # type: ignore
                raise ContradictionByLiteral(
                    "Incompatible literal subsets",
                    involved=from_ops,
                    literals=[to, po],
                    mutator=self.mutator,
                )
            return make_lit(True)

        if to_is_lit:
            assert check_existing
            assert isinstance(po, ParameterOperatable)
            return self.subset_literal(po, to, from_ops=from_ops)

        if po_is_lit and check_existing:
            # TODO implement
            pass

        # check if alias exists
        if isinstance(po, Expression) and isinstance(to, Expression) and check_existing:
            if overlap := (
                po.get_operations(Is, constrained_only=True)
                & to.get_operations(Is, constrained_only=True)
            ):
                return next(iter(overlap))

        return self.mutator.create_expression(
            IsSubset,
            po,
            to,
            from_ops=from_ops,
            constrain=True,
            check_exists=check_existing,
            allow_uncorrelated=True,
            _relay=False,
        )  # type: ignore

    def alias_is_literal_and_check_predicate_eval(
        self,
        expr: ParameterOperatable,
        value: BoolSet | bool,
    ):
        """
        Call this when 100% sure what the result of a predicate is.
        """
        self.alias_to(expr, as_lit(value), terminate=True)
        if not isinstance(expr, ConstrainableExpression):
            return
        if not expr.constrained:
            return
        # all predicates alias to True, so alias False will already throw
        if value != BoolSet(True):
            raise Contradiction(
                "Constrained predicate deduced to False",
                involved=[expr],
                mutator=self.mutator,
            )
        self.mutator.predicate_terminate(expr)

        # TODO is this still needed?
        # terminate all alias_is P -> True
        for op in expr.get_operations(Is):
            if not op.constrained:
                continue
            lit = self.try_extract_literal(op)
            if lit is None:
                continue
            if lit != BoolSet(True):
                continue
            self.mutator.predicate_terminate(op)

    def is_replacable_by_literal(self, op: ParameterOperatable.All):
        if not isinstance(op, ParameterOperatable):
            return None

        # special case for Is(True, True) due to alias_is_literal check
        if isinstance(op, Is) and {BoolSet(True)} == set(op.operands):
            return BoolSet(True)

        lit = self.try_extract_literal(op, allow_subset=False)
        if lit is None:
            return None
        if not self.is_correlatable_literal(lit):
            return None
        return lit

    def find_congruent_expression[T: CanonicalExpression](
        self,
        expr_factory: type[T],
        *operands: SolverAll,
        allow_uncorrelated: bool = False,
    ) -> T | None:
        non_lits = [op for op in operands if isinstance(op, ParameterOperatable)]
        literal_expr = all(
            self.is_literal(op) or self.is_literal_expression(op) for op in operands
        )
        if literal_expr:
            lit_ops = {
                op
                for op in self.mutator.nodes_of_type(
                    expr_factory, created_only=False, include_terminated=True
                )
                if self.is_literal_expression(op)
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
            expr
            for expr in non_lits[0].get_operations()
            if isinstance(expr, expr_factory)
        ]
        for c in candidates:
            # TODO congruence check instead
            if c.operands == operands:
                return c
        return None

    def get_all_aliases(self) -> set[Is]:
        return {
            op
            for op in self.mutator.nodes_of_type(Is, include_terminated=True)
            if op.constrained
        }

    def get_all_subsets(self) -> set[IsSubset]:
        return {
            op
            for op in self.mutator.nodes_of_type(IsSubset, include_terminated=True)
            if op.constrained
        }

    def collect_factors[T: Multiply | Power](
        self, counter: Counter[ParameterOperatable], collect_type: type[T]
    ):
        # Convert the counter to a dict for easy manipulation
        factors: dict[ParameterOperatable, ParameterOperatable.NumberLiteral] = dict(
            counter.items()
        )
        # Store operations of type collect_type grouped by their non-literal operand
        same_literal_factors: dict[ParameterOperatable, list[T]] = defaultdict(list)

        # Look for operations matching collect_type and gather them
        for collect_op in set(factors.keys()):
            if not isinstance(collect_op, collect_type):
                continue
            # Skip if operation doesn't have exactly two operands
            # TODO unnecessary strict
            if len(collect_op.operands) != 2:
                continue
            # handled by lit fold first
            if len(collect_op.get_operand_literals()) > 1:
                continue
            if not collect_op.get_operand_literals():
                continue
            # handled by lit fold completely
            if self.is_pure_literal_expression(collect_op):
                continue
            if not issubclass(collect_type, Commutative):
                if not issubclass(collect_type, Power):
                    raise NotImplementedError(
                        f"Non-commutative {collect_type.__name__} not implemented"
                    )
                # For power, ensure second operand is literal
                if not self.is_literal(collect_op.operands[1]):
                    continue

            # pick non-literal operand
            paramop = next(iter(collect_op.operatable_operands))
            # Collect these factors under the non-literal operand
            same_literal_factors[paramop].append(collect_op)  # type: ignore #TODO
            # If this operand isn't in factors yet, initialize it with 0
            if paramop not in factors:
                factors[paramop] = make_lit(0)
            # Remove this operation from the main factors
            del factors[collect_op]

        # new_factors: combined literal counts, old_factors: leftover items
        new_factors = {}
        old_factors = []

        # Combine literals for each non-literal operand
        for var, count in factors.items():
            muls = same_literal_factors[var]
            # If no effective multiplier or only a single factor, treat as leftover
            if count == 0 and len(muls) <= 1:
                old_factors.extend(muls)
                continue

            # If only count=1 and no additional factors, just keep the variable
            if count == 1 and not muls:
                old_factors.append(var)
                continue

            # Extract literal parts from collected operations
            mul_lits = [
                next(o for o in mul.operands if ParameterOperatable.is_literal(o))
                for mul in muls
            ]

            # Sum all literal multipliers plus the leftover count
            new_factors[var] = sum(mul_lits) + make_lit(count)  # type: ignore

        return new_factors, old_factors

    # TODO better name
    @staticmethod
    def fold_op(
        operands: Sequence[SolverLiteral],
        operator: Callable[[SolverLiteral, SolverLiteral], SolverLiteral],
        identity: SolverLiteral,
    ):
        """
        Return 'sum' of all literals in the iterable, or empty list if sum is identity.
        """
        if not operands:
            return []

        literal_it = iter(operands)
        const_sum = next(literal_it)
        for c in literal_it:
            const_sum = operator(const_sum, c)

        # TODO make work with all the types
        if const_sum == identity:
            return []

        return [const_sum]

    @staticmethod
    def are_aliased(po: ParameterOperatable, *other: ParameterOperatable) -> bool:
        return bool(
            po.get_operations(Is, constrained_only=True)
            & {o for o in other for o in o.get_operations(Is, constrained_only=True)}
        )

    @staticmethod
    def is_literal(po: ParameterOperatable | SolverAll) -> TypeGuard[SolverLiteral]:
        # allowed because of canonicalization
        return ParameterOperatable.is_literal(po)

    @staticmethod
    def is_numeric_literal(po: ParameterOperatable) -> TypeGuard[CanonicalNumber]:
        return MutatorUtils.is_literal(po) and isinstance(po, CanonicalNumber)

    @staticmethod
    def is_literal_expression(
        po: ParameterOperatable | SolverAll,
    ) -> TypeGuard[Expression]:
        return isinstance(po, Expression) and not po.get_operand_parameters(
            recursive=True
        )

    @staticmethod
    def is_pure_literal_expression(
        po: ParameterOperatable | SolverAll,
    ) -> TypeGuard[CanonicalExpression]:
        return isinstance(po, Expression) and all(
            MutatorUtils.is_literal(op) for op in po.operands
        )

    @staticmethod
    def is_alias_is_literal(po: ParameterOperatable) -> TypeGuard[Is]:
        return bool(
            isinstance(po, Is)
            and po.constrained
            and po.get_operand_literals()
            and po.operatable_operands
        )

    @staticmethod
    def is_subset_literal(po: ParameterOperatable) -> TypeGuard[IsSubset]:
        return bool(
            isinstance(po, IsSubset)
            and po.constrained
            and MutatorUtils.is_literal(po.operands[1])
            and isinstance(po.operands[0], ParameterOperatable)
        )

    @staticmethod
    def no_other_constraints(
        po: ParameterOperatable,
        *other: ConstrainableExpression,
        unfulfilled_only: bool = False,
    ) -> bool:
        no_other_constraints = (
            len(
                [
                    x
                    for x in MutatorUtils.get_constrained_expressions_involved_in(
                        po
                    ).difference(other)
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

    @staticmethod
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

        out = MutatorUtils.FlattenAssociativeResult[T](
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

            res = MutatorUtils.flatten_associative(
                nested_to_flatten, check_destructable
            )
            nested_extracted_operands += res.extracted_operands
            out.destroyed_operations.update(res.destroyed_operations)

        out.extracted_operands.extend(nested_extracted_operands)

        return out

    @staticmethod
    def is_constrained(po: ParameterOperatable) -> TypeGuard[ConstrainableExpression]:
        return isinstance(po, ConstrainableExpression) and po.constrained

    @staticmethod
    def get_lit_mapping_from_lit_expr(
        expr: Is | IsSubset,
    ) -> tuple[ParameterOperatable, SolverLiteral]:
        assert MutatorUtils.is_alias_is_literal(expr) or MutatorUtils.is_subset_literal(
            expr
        )
        return next(iter(expr.operatable_operands)), next(
            iter(expr.get_operand_literals().values())
        )

    @staticmethod
    def get_params_for_expr(expr: Expression) -> set[Parameter]:
        param_ops = {op for op in expr.operatable_operands if isinstance(op, Parameter)}
        expr_ops = {op for op in expr.operatable_operands if isinstance(op, Expression)}

        return param_ops | {
            op for e in expr_ops for op in MutatorUtils.get_params_for_expr(e)
        }

    # TODO make generator
    @staticmethod
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
                dependants.update(p.get_operand_expressions(recursive=True))

        res = {p for p in dependants if isinstance(p, type_filter)}
        return res

    @staticmethod
    def get_constrained_expressions_involved_in[T: ConstrainableExpression](
        p: ParameterOperatable,
        type_filter: type[T] = ConstrainableExpression,
    ) -> set[T]:
        res = {
            p
            for p in MutatorUtils.get_expressions_involved_in(p, type_filter)
            if p.constrained
        }
        return res

    @staticmethod
    def get_correlations(expr: Expression, exclude: set[Expression] | None = None):
        # TODO: might want to check if expr has aliases because those are correlated too

        if exclude is None:
            exclude = set()

        exclude.add(expr)
        excluded = {
            e
            for e in exclude
            if isinstance(e, ConstrainableExpression) and e.constrained
        }
        excluded.update(MutatorUtils.get_constrained_expressions_involved_in(expr, Is))

        operables = [o for o in expr.operands if isinstance(o, ParameterOperatable)]
        op_set = set(operables)

        def _get(e: ParameterOperatable):
            vs = {e}
            if isinstance(e, Expression):
                vs = e.get_operand_leaves_operatable()
            return {
                o
                for v in vs
                for o in MutatorUtils.get_constrained_expressions_involved_in(v, Is)
            }

        exprs = {o: _get(o) for o in op_set}
        # check disjoint sets
        for e1, e2 in combinations(operables, 2):
            if e1 is e2:
                yield e1, e2, exprs[e1].difference(excluded)
            overlap = (exprs[e1] & exprs[e2]).difference(excluded)
            if overlap:
                yield e1, e2, overlap

    @staticmethod
    def find_unique_params(po: ParameterOperatable) -> set[ParameterOperatable]:
        match po:
            case Parameter():
                return {po}
            case Expression():
                return {
                    p for op in po.operands for p in MutatorUtils.find_unique_params(op)
                }
            case _:
                return set()

    @staticmethod
    def count_param_occurrences(po: ParameterOperatable) -> dict[Parameter, int]:
        counts: dict[Parameter, int] = defaultdict(int)

        match po:
            case Parameter():
                counts[po] += 1
            case Expression():
                for op in po.operands:
                    for param, count in MutatorUtils.count_param_occurrences(
                        op
                    ).items():
                        counts[param] += count

        return counts

    @staticmethod
    def is_correlatable_literal(op):
        if not MutatorUtils.is_literal(op):
            return False
        return op.is_single_element() or op.is_empty()

    @staticmethod
    def get_supersets(
        op: ParameterOperatable,
    ) -> Mapping[ParameterOperatable | SolverLiteral, list[IsSubset]]:
        ss = [
            e
            for e in op.get_operations(IsSubset, constrained_only=True)
            if e.operands[0] is op
        ]
        return groupby(ss, key=lambda e: e.operands[1])

    @staticmethod
    def get_aliases(
        op: ParameterOperatable,
    ) -> dict[ParameterOperatable | SolverLiteral, Is]:
        return {
            e.get_other_operand(op): e
            for e in op.get_operations(Is, constrained_only=True)
        }

    @staticmethod
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
