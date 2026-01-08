# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
import operator
from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from typing import (
    TYPE_CHECKING,
    Callable,
    Counter,
    Iterable,
    Mapping,
    Sequence,
    cast,
)

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core import graph
from faebryk.core.solver.solver import LOG_PICK_SOLVE
from faebryk.libs.logging import rich_to_string
from faebryk.libs.util import (
    ConfigFlag,
    ConfigFlagFloat,
    ConfigFlagInt,
    KeyErrorAmbiguous,
    groupby,
    not_none,
    partition,
    unique,
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
        involved: list[F.Parameters.is_parameter_operatable],
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

        def _get_origins(
            p: F.Parameters.is_parameter_operatable,
        ) -> list[F.Parameters.is_parameter_operatable]:
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
        involved: list[F.Parameters.is_parameter_operatable],
        literals: list[F.Literals.is_literal],
        mutator: "Mutator",
    ):
        super().__init__(msg, involved, mutator)
        self.literals = literals

    def __str__(self):
        literals_str = "\n".join(f" - {lit.pretty_str()}" for lit in self.literals)
        return f"{super().__str__()}\n\nLiterals:\n{literals_str}"


class MutatorUtils:
    def __init__(self, mutator: "Mutator"):
        self.mutator = mutator

    def dimensionless(self) -> "F.Units.is_unit":
        return (
            F.Units.Dimensionless.bind_typegraph(self.mutator.tg_out)
            .create_instance(self.mutator.G_transient)
            .is_unit.get()
        )

    def make_number_literal_from_range(
        self, lower: float, upper: float
    ) -> F.Literals.Numbers:
        return (
            F.Literals.Numbers.bind_typegraph(self.mutator.tg_in)
            .create_instance(self.mutator.G_transient)
            .setup_from_min_max(
                lower,
                upper,
                unit=self.dimensionless(),
            )
        )

    # TODO should be part of mutator
    def try_extract_literal(
        self,
        po: F.Parameters.is_parameter_operatable,
        allow_subset: bool = False,
        check_pre_transform: bool = False,
    ) -> F.Literals.is_literal | None:
        pos = {po}

        # TODO should be mutator api
        if check_pre_transform and po in self.mutator.transformations.mutated.values():
            pos |= {
                k
                for k, v in self.mutator.transformations.mutated.items()
                if v is po and k not in self.mutator.transformations.removed
            }

        lits = set[F.Literals.is_literal]()
        try:
            for po in pos:
                lit = po.try_extract_literal(allow_subset=allow_subset)
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
        return lit

    def try_extract_literal_info(
        self,
        po: F.Parameters.is_parameter_operatable,
    ) -> tuple[F.Literals.is_literal | None, bool]:
        """
        returns (literal, is_alias)
        """
        lit = self.try_extract_literal(po, allow_subset=False)
        if lit is not None:
            return lit, True
        lit = self.try_extract_literal(po, allow_subset=True)
        return lit, False

    def try_extract_lit_op(
        self, po: F.Parameters.is_parameter_operatable
    ) -> tuple[F.Literals.is_literal, F.Expressions.Is | F.Expressions.IsSubset] | None:
        aliases = self.get_aliases(po)
        alias_lits = [
            (k_lit, v) for k, v in aliases.items() if (k_lit := self.is_literal(k))
        ]
        if alias_lits:
            unique_lits = unique(
                alias_lits,
                lambda x: x[0],
                custom_eq=lambda x, y: x.equals(
                    y, g=self.mutator.G_transient, tg=self.mutator.tg_in
                ),
            )
            if len(unique_lits) > 1:
                raise ContradictionByLiteral(
                    "Multiple alias literals found",
                    involved=[po]
                    + [x[1].is_parameter_operatable.get() for x in unique_lits],
                    literals=[x[0] for x in unique_lits],
                    mutator=self.mutator,
                )
            return alias_lits[0]
        subsets = self.get_supersets(po)
        subset_lits = [
            (k_lit, vs) for k, vs in subsets.items() if (k_lit := self.is_literal(k))
        ]
        # TODO this is weird
        if subset_lits:
            for k, vs in subset_lits:
                if all(
                    k.is_subset_of(
                        other_k, g=self.mutator.G_transient, tg=self.mutator.tg_in
                    )
                    for other_k, _ in subset_lits
                ):
                    return k, vs[0]
        return None

    def map_extract_literals(
        self,
        expr: F.Expressions.is_expression,
        allow_subset: bool = False,
    ) -> tuple[
        list[F.Parameters.can_be_operand], list[F.Parameters.is_parameter_operatable]
    ]:
        out = list[F.Parameters.can_be_operand]()
        any_lit = list[F.Parameters.is_parameter_operatable]()
        for op in expr.get_operands():
            if self.is_literal(op):
                out.append(op)
                continue
            op_po = op.as_parameter_operatable.force_get()
            lit = self.try_extract_literal(op_po, allow_subset=allow_subset)
            if lit is None:
                out.append(op)
                continue
            out.append(lit.as_operand.get())
            any_lit.append(op_po)
        return out, any_lit

    def alias_is_literal(
        self,
        po: F.Parameters.is_parameter_operatable,
        literal: F.Literals.is_literal,
        from_ops: Sequence[F.Parameters.is_parameter_operatable] | None = None,
        terminate: bool = False,
    ) -> F.Expressions.is_expression | F.Literals.is_literal:
        existing = self.try_extract_literal(po, check_pre_transform=True)
        if existing is not None:
            if existing.equals(
                literal, g=self.mutator.G_transient, tg=self.mutator.tg_in
            ):
                if terminate:
                    for op in po.get_operations(F.Expressions.Is, predicates_only=True):
                        if op.is_expression.get().in_operands(
                            existing.as_operand.get()
                        ):
                            self.mutator.predicate_terminate(
                                op.get_trait(F.Expressions.is_predicate)
                            )
                    return self.mutator.make_lit(True).is_literal.get()
                return self.mutator.make_lit(True).is_literal.get()
            raise ContradictionByLiteral(
                "Tried alias to different literal",
                involved=[po],
                literals=[existing, literal],
                mutator=self.mutator,
            )
        # prevent (A is X) is X
        if po_is := fabll.Traits(po).get_obj_raw().try_cast(F.Expressions.Is):
            if literal.in_container(
                po_is.is_expression.get().get_operand_literals().values(),
                g=self.mutator.G_transient,
                tg=self.mutator.tg_in,
            ):
                return self.mutator.make_lit(True).is_literal.get()
        if (ss_lit := self.try_extract_literal(po, allow_subset=True)) is not None:
            if not literal.is_subset_of(
                ss_lit, g=self.mutator.G_transient, tg=self.mutator.tg_in
            ):
                raise ContradictionByLiteral(
                    "Tried alias to literal incompatible with subset",
                    involved=[po],
                    literals=[ss_lit, literal],
                    mutator=self.mutator,
                )
        out = self.mutator.create_expression(
            F.Expressions.Is,
            po.as_operand.get(),
            literal.as_operand.get(),
            from_ops=from_ops,
            assert_=True,
            # already checked for uncorrelated lit, op needs to be correlated
            allow_uncorrelated=False,
            check_redundant=False,
            _relay=False,
        )
        if terminate:
            self.mutator.predicate_terminate(
                out.get_sibling_trait(F.Expressions.is_predicate)
            )
        return out

    def subset_literal(
        self,
        po: F.Parameters.is_parameter_operatable,
        literal: F.Literals.is_literal,
        from_ops: Sequence[F.Parameters.is_parameter_operatable] | None = None,
    ) -> F.Expressions.is_expression:
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
            if ex_op.try_cast(F.Expressions.Is):
                if not ex_lit.is_subset_of(
                    literal, g=self.mutator.G_transient, tg=self.mutator.tg_in
                ):
                    raise ContradictionByLiteral(
                        "Tried subset to different literal",
                        involved=[po],
                        literals=[ex_lit, literal],
                        mutator=self.mutator,
                    )
                return ex_op.is_expression.get()

            # no point in adding more general subset
            if ex_lit.is_subset_of(
                literal, g=self.mutator.G_transient, tg=self.mutator.tg_in
            ):
                return ex_op.is_expression.get()
            # other cases handled by intersect subsets algo

        return cast(
            # cast allowed because _relay is False
            F.Expressions.is_expression,
            self.mutator.create_expression(
                F.Expressions.IsSubset,
                po.as_operand.get(),
                literal.as_operand.get(),
                from_ops=from_ops,
                assert_=True,
                # already checked for uncorrelated lit, op needs to be correlated
                allow_uncorrelated=False,
                check_redundant=False,
                _relay=False,
            ),
        )

    def alias_to(
        self,
        po: F.Parameters.can_be_operand,
        to: F.Parameters.can_be_operand,
        check_redundant: bool = True,
        from_ops: Sequence[F.Parameters.is_parameter_operatable] | None = None,
        terminate: bool = False,
    ) -> F.Expressions.is_expression | F.Literals.is_literal:
        from faebryk.core.solver.symbolic.pure_literal import (
            _exec_pure_literal_expressions,
        )

        from_ops = from_ops or []
        if (
            (to_po := to.as_parameter_operatable.try_get())
            and (to_expr := to_po.as_expression.try_get())
            and (to_canon := to_expr.as_canonical.try_get())
        ):
            res = _exec_pure_literal_expressions(
                g=self.mutator.G_transient,
                tg=self.mutator.tg_in,
                expr=to_canon.as_expression.get(),
            )
            if res is not None:
                to = res.as_operand.get()

        to_is_lit = self.is_literal(to)
        po_is_lit = self.is_literal(po)
        if po_is_lit:
            if not to_is_lit:
                to, po = po, to
                to_is_lit, po_is_lit = po_is_lit, to_is_lit
            else:
                if not po_is_lit.equals(
                    to_is_lit, g=self.mutator.G_transient, tg=self.mutator.tg_in
                ):
                    raise ContradictionByLiteral(
                        "Incompatible literal aliases",
                        involved=list(from_ops),
                        literals=[po_is_lit, to_is_lit],
                        mutator=self.mutator,
                    )
                return self.mutator.make_lit(True).is_literal.get()
        po_po = po.as_parameter_operatable.force_get()
        from_ops = [po_po] + list(from_ops)
        if to_is_lit:
            assert check_redundant
            to_lit = to.as_literal.force_get()
            return self.alias_is_literal(
                po_po, to_lit, from_ops=from_ops, terminate=terminate
            )

        # not sure why this would be needed anyway
        if terminate:
            raise NotImplementedError("Terminate not implemented for non-literals")

        # check if alias exists
        if (
            po_po.as_expression.try_get()
            and (to_po := to.as_parameter_operatable.try_get())
            and (to_exp := to_po.as_expression.try_get())
            and check_redundant
        ):
            if overlap := (
                po_po.get_operations(F.Expressions.Is, predicates_only=True)
                & to_exp.as_parameter_operatable.get().get_operations(
                    F.Expressions.Is, predicates_only=True
                )
            ):
                return next(iter(overlap)).is_expression.get()

        return self.mutator.create_expression(
            F.Expressions.Is,
            po,
            to,
            from_ops=from_ops,
            assert_=True,
            check_redundant=check_redundant,
            allow_uncorrelated=True,
            _relay=False,
        )

    def subset_to(
        self,
        po: F.Parameters.can_be_operand,
        to: F.Parameters.can_be_operand,
        check_redundant: bool = True,
        from_ops: Sequence[F.Parameters.is_parameter_operatable] | None = None,
    ) -> F.Expressions.is_expression | F.Literals.is_literal:
        from faebryk.core.solver.symbolic.pure_literal import (
            _exec_pure_literal_expressions,
        )

        from_ops = from_ops or []
        from_ops = [
            x_po
            for x in [po, to] + list(from_ops)
            if (x_po := x.try_get_sibling_trait(F.Parameters.is_parameter_operatable))
        ]

        if (
            (to_po := to.as_parameter_operatable.try_get())
            and (to_exp := to_po.as_expression.try_get())
            and (to_canon := to_exp.as_canonical.try_get())
        ):
            res = _exec_pure_literal_expressions(
                g=self.mutator.G_transient,
                tg=self.mutator.tg_in,
                expr=to_canon.as_expression.get(),
            )
            if res is not None:
                to = res.as_operand.get()

        to_lit = self.is_literal(to)
        po_lit = self.is_literal(po)

        if to_lit and po_lit:
            if not po_lit.is_subset_of(
                to_lit, g=self.mutator.G_transient, tg=self.mutator.tg_in
            ):
                raise ContradictionByLiteral(
                    "Incompatible literal subsets",
                    involved=from_ops,
                    literals=[to_lit, po_lit],
                    mutator=self.mutator,
                )
            return self.mutator.make_lit(True).is_literal.get()

        if to_lit:
            assert check_redundant
            return self.subset_literal(
                po.as_parameter_operatable.force_get(),
                to_lit,
                from_ops=from_ops,
            )
        if po_lit and check_redundant:
            # TODO implement
            pass

        # check if alias exists
        if (
            (po_po := po.as_parameter_operatable.try_get())
            and po_po.as_expression.try_get()
            and (to_po := to.as_parameter_operatable.try_get())
            and to_po.as_expression.try_get()
            and check_redundant
        ):
            if overlap := (
                po.as_parameter_operatable.force_get().get_operations(
                    F.Expressions.Is, predicates_only=True
                )
                & to.as_parameter_operatable.force_get().get_operations(
                    F.Expressions.Is, predicates_only=True
                )
            ):
                return next(iter(overlap)).is_expression.get()

        return self.mutator.create_expression(
            F.Expressions.IsSubset,
            po,
            to,
            from_ops=from_ops,
            assert_=True,
            check_redundant=check_redundant,
            allow_uncorrelated=True,
            _relay=False,
        )

    def alias_is_literal_and_check_predicate_eval(
        self,
        expr: F.Expressions.is_expression,
        value: F.Literals.is_literal,
    ):
        """
        Call this when 100% sure what the result of a predicate is.
        """
        self.alias_to(
            expr.as_operand.get(),
            value.as_operand.get(),
            terminate=True,
        )
        if not (expr_co := expr.try_get_sibling_trait(F.Expressions.is_predicate)):
            return
        expr_po = expr.as_parameter_operatable.get()
        # all predicates alias to True, so alias False will already throw
        bool_lit = fabll.Traits(value).get_obj(F.Literals.Booleans)
        if bool_lit.is_false():
            raise Contradiction(
                "Predicate deduced to False",
                involved=[expr_po],
                mutator=self.mutator,
            )
        self.mutator.predicate_terminate(expr_co)

        # TODO is this still needed?
        # terminate all alias_is P -> True
        for op in expr_po.get_operations(F.Expressions.Is, predicates_only=True):
            op_po = op.is_parameter_operatable.get()
            lit = self.try_extract_literal(op_po)
            if lit is None:
                continue
            if not lit.equals_singleton(True):
                continue
            self.mutator.predicate_terminate(op.get_trait(F.Expressions.is_predicate))

    def is_replacable_by_literal(
        self, op: F.Parameters.can_be_operand
    ) -> F.Literals.is_literal | None:
        if not (op_po := op.as_parameter_operatable.try_get()):
            return None

        # special case for Is(True, True) due to alias_is_literal check
        if (
            (op_is := fabll.Traits(op_po).get_obj_raw().try_cast(F.Expressions.Is))
            and (op_lits := (op_e := op_is.is_expression.get()).get_operand_literals())
            and not op_e.get_operand_operatables()
            and all(op_lit.equals_singleton(True) for op_lit in op_lits.values())
        ):
            return self.mutator.make_lit(True).is_literal.get()

        lit = self.try_extract_literal(op_po, allow_subset=False)
        if lit is None:
            return None
        if not self.is_correlatable_literal(lit):
            return None
        return lit

    def find_congruent_expression[T: fabll.NodeT](
        self,
        expr_factory: type[T],
        *operands: F.Parameters.can_be_operand,
        allow_uncorrelated: bool = False,
        dont_match: list[F.Expressions.is_expression] | None = None,
    ) -> T | None:
        """
        Careful: Disregards whether asserted in root expression!
        """
        non_lits = [
            op_po for op in operands if (op_po := op.as_parameter_operatable.try_get())
        ]
        literal_expr = all(
            self.is_literal(op) or self.is_literal_expression(op) for op in operands
        )
        dont_match_set = set(dont_match or [])
        if literal_expr:
            lit_ops = {
                op
                for op in self.mutator.get_typed_expressions(
                    expr_factory, created_only=False, include_terminated=True
                )
                if op.get_trait(F.Expressions.is_expression) not in dont_match_set
                and self.is_literal_expression(
                    op.get_trait(F.Parameters.can_be_operand)
                )
                # check congruence
                and F.Expressions.is_expression.are_pos_congruent(
                    op.get_trait(F.Expressions.is_expression).get_operands(),
                    operands,
                    g=self.mutator.G_transient,
                    tg=self.mutator.tg_in,
                    allow_uncorrelated=allow_uncorrelated,
                )
            }
            if lit_ops:
                return next(iter(lit_ops))
            return None

        # TODO: might have to check in repr_map
        candidates = [
            expr_t
            for expr in non_lits[0].get_operations()
            if (expr_t := expr.try_cast(expr_factory))
            and expr_t.get_trait(F.Expressions.is_expression) not in dont_match_set
        ]

        for c in candidates:
            if c.get_trait(F.Expressions.is_expression).is_congruent_to_factory(
                expr_factory,
                operands,
                g=self.mutator.G_transient,
                tg=self.mutator.tg_in,
                allow_uncorrelated=allow_uncorrelated,
            ):
                return c
        return None

    # Subsumption checking -------------------------------------------------------------

    @staticmethod
    def _get_potentially_subsuming_types(
        expr_factory: type[fabll.NodeT],
    ) -> tuple[type[fabll.NodeT], ...]:
        """
        Get all expression types that could potentially subsume the given type.
        Includes the type itself plus any stronger types.

        Cross-type subsumption (candidate → new):
        - Is → IsSubset, GreaterThan, GreaterOrEqual
        - IsSubset → GreaterThan, GreaterOrEqual
        - GreaterThan ↔ GreaterOrEqual
        """
        return {
            F.Expressions.IsSubset: (
                F.Expressions.IsSubset,
                F.Expressions.Is,
            ),
            F.Expressions.GreaterThan: (
                F.Expressions.GreaterThan,
                F.Expressions.GreaterOrEqual,
                F.Expressions.Is,
                F.Expressions.IsSubset,
            ),
            F.Expressions.GreaterOrEqual: (
                F.Expressions.GreaterOrEqual,
                F.Expressions.GreaterThan,
                F.Expressions.Is,
                F.Expressions.IsSubset,
            ),
            F.Expressions.Or: (F.Expressions.Or,),
        }.get(expr_factory, (expr_factory,))

    @staticmethod
    def _compatible_expr_types(
        new_factory: type[fabll.NodeT],
        candidate_obj: fabll.Node,
    ) -> bool:
        """Can the candidate expression potentially subsume the new expression?"""
        return any(
            candidate_obj.isinstance(t)
            for t in MutatorUtils._get_potentially_subsuming_types(new_factory)
        )

    @staticmethod
    def _operands_structurally_match(
        new_operands: Sequence[F.Parameters.can_be_operand],
        candidate_operands: Sequence[F.Parameters.can_be_operand],
    ) -> bool:
        """
        Check that non-literal operands refer to the same parameter/expression.
        Literals can differ (semantic check will compare values).
        """
        for new_op, cand_op in zip(new_operands, candidate_operands):
            new_po = new_op.as_parameter_operatable.try_get()
            cand_po = cand_op.as_parameter_operatable.try_get()

            # Both literals - skip (semantic check will compare values)
            if new_po is None and cand_po is None:
                continue

            # One literal, one not - no match
            if new_po is None or cand_po is None:
                return False

            # Both operatables - must be same node (allow different graphs since
            # the mutator operates across input and output graphs)
            if not new_po.is_same(cand_po, allow_different_graph=True):
                return False

        return True

    @staticmethod
    def _operands_are_subset(
        candidate_operands: Sequence[F.Parameters.can_be_operand],
        new_operands: Sequence[F.Parameters.can_be_operand],
    ) -> bool:
        """
        Check if candidate operands are a subset of new operands (by identity).
        Used for Or subsumption: Or(A, B) subsumes Or(A, B, C).
        """
        if len(candidate_operands) > len(new_operands):
            return False

        def _get_uuid(op: F.Parameters.can_be_operand) -> int | None:
            if (po := op.as_parameter_operatable.try_get()) is not None:
                return po.instance.node().get_uuid()
            if (lit := op.as_literal.try_get()) is not None:
                return lit.instance.node().get_uuid()
            return None

        new_uuids = {_get_uuid(op) for op in new_operands}
        return all(_get_uuid(op) in new_uuids for op in candidate_operands)

    @staticmethod
    def _structural_match(
        new_factory: type[fabll.NodeT],
        new_operands: Sequence[F.Parameters.can_be_operand],
        candidate: F.Expressions.is_predicate,
    ) -> bool:
        """
        Quick structural check - does this candidate have compatible shape?
        e.g., same operand(s) in same position(s), compatible expression type
        """
        # TODO: find a more efficient way to do structural-match searches
        # (log(N) in number of exprs?)
        candidate_expr = candidate.as_expression.get()
        candidate_operands = candidate_expr.get_operands()

        # Same/compatible expression type?
        candidate_obj = fabll.Traits(candidate).get_obj_raw()
        if not MutatorUtils._compatible_expr_types(new_factory, candidate_obj):
            return False

        # Or: quick filter - candidate must have <= operands (subset check in semantic)
        if new_factory is F.Expressions.Or:
            return len(candidate_operands) <= len(new_operands)

        # Same arity?
        if len(candidate_operands) != len(new_operands):
            return False

        # Operands match (considering the non-literal operand)?
        return MutatorUtils._operands_structurally_match(
            new_operands, candidate_operands
        )

    @staticmethod
    def _is_subsumed_by(
        new_factory: type[fabll.NodeT],
        new_operands: Sequence[F.Parameters.can_be_operand],
        candidate: F.Expressions.is_predicate,
        g: graph.GraphView,
        tg: fbrk.TypeGraph,
    ) -> bool:
        """
        Semantic subsumption check — assumes structural match already passed.

        Predicate types with no subsumption cases:
        - Is: same values would be congruent (not subsuming), different don't subsume
        - IsBitSet: same bit+value would be congruent, different bits don't subsume

        Valid but expensive/complex cases intentionally skipped:
        - Or:
            - Non-Or P subsumes Or(A, B, ...) if P subsumes any operand (recursive)
            - Or(A, B) subsumes non-Or P if all operands subsume P (recursive)
        - Not:
            - Not(A) subsumes Not(B) if B subsumes A (contraposition, recursive)
            - P subsumes Not(Q) when P implies ~Q (requires negation semantics)
            - Not(P) subsumes Q when ~P implies Q (requires negation semantics)
        - Nested logical expressions:
            - Not(Not(X)) ≡ X (handled by is_involutory normalization elsewhere)
            - De Morgan's laws for Not(Or(...))
        """

        def _compare_operand_literals(
            operand_index: int,
            comparator: Callable[[F.Literals.is_literal, F.Literals.is_literal], bool],
        ) -> bool:
            """
            Generic comparison of literal operands at a given index.
            Returns True if comparator(candidate_lit, new_lit) is True.
            """
            new_lit = new_operands[operand_index].as_literal.try_get()
            cand_lit = (
                candidate.as_expression.get()
                .get_operands()[operand_index]
                .as_literal.try_get()
            )

            if new_lit is None or cand_lit is None:
                return False

            try:
                return comparator(cand_lit, new_lit)
            except F.Literals.IncompatibleTypesError:
                return False

        def _get_singleton_value(lit: F.Literals.is_literal) -> float | None:
            """Extract singleton numeric value from a literal."""
            nums = fabll.Traits(lit).get_obj_raw().try_cast(F.Literals.Numbers)
            if nums is None:
                return None
            return nums.try_get_single()

        def _get_min_value(lit: F.Literals.is_literal) -> float | None:
            """Extract minimum value from a numeric literal (range or singleton)."""
            nums = fabll.Traits(lit).get_obj_raw().try_cast(F.Literals.Numbers)
            if nums is None or nums.is_empty():
                return None
            return nums.get_min_value()

        def _make_numeric_comparator(
            cand_extractor: Callable[[F.Literals.is_literal], float | None],
            op: Callable[[float, float], bool],
        ) -> Callable[[F.Literals.is_literal, F.Literals.is_literal], bool]:
            def comparator(
                cand_lit: F.Literals.is_literal, new_lit: F.Literals.is_literal
            ) -> bool:
                cand_val = cand_extractor(cand_lit)
                new_val = _get_singleton_value(new_lit)
                if cand_val is None or new_val is None:
                    return False
                return op(cand_val, new_val)

            return comparator

        _numeric_ge = _make_numeric_comparator(_get_singleton_value, operator.ge)
        _numeric_gt = _make_numeric_comparator(_get_singleton_value, operator.gt)
        _min_ge_singleton = _make_numeric_comparator(_get_min_value, operator.ge)
        _min_gt_singleton = _make_numeric_comparator(_get_min_value, operator.gt)

        def _is_subset_of(c: F.Literals.is_literal, n: F.Literals.is_literal) -> bool:
            return c.is_subset_of(n, g=g, tg=tg)

        c = fabll.Traits(candidate).get_obj_raw()
        E = F.Expressions

        match new_factory:
            # IsSubset ← Is, IsSubset
            case E.IsSubset if c.isinstance(E.Is) or c.isinstance(E.IsSubset):
                return _compare_operand_literals(1, _is_subset_of)
            # GreaterThan ← Is (value > bound)
            case E.GreaterThan if c.isinstance(E.Is):
                return _compare_operand_literals(1, _numeric_gt)
            # GreaterThan ← IsSubset (min > bound)
            case E.GreaterThan if c.isinstance(E.IsSubset):
                return _compare_operand_literals(1, _min_gt_singleton)
            # GreaterThan ← GT, GE (bound comparison)
            case E.GreaterThan if c.isinstance(E.GreaterThan):
                return _compare_operand_literals(1, _numeric_ge)
            case E.GreaterThan if c.isinstance(E.GreaterOrEqual):
                return _compare_operand_literals(1, _numeric_gt)
            # GreaterOrEqual ← Is (value >= bound)
            case E.GreaterOrEqual if c.isinstance(E.Is):
                return _compare_operand_literals(1, _numeric_ge)
            # GreaterOrEqual ← IsSubset (min >= bound)
            case E.GreaterOrEqual if c.isinstance(E.IsSubset):
                return _compare_operand_literals(1, _min_ge_singleton)
            # GreaterOrEqual ← GT, GE (bound comparison)
            case E.GreaterOrEqual if c.isinstance(E.GreaterThan):
                return _compare_operand_literals(1, _numeric_ge)
            case E.GreaterOrEqual if c.isinstance(E.GreaterOrEqual):
                return _compare_operand_literals(1, _numeric_ge)
            # Or ← Or (operand subset check)
            case E.Or if c.isinstance(E.Or):
                candidate_operands = candidate.as_expression.get().get_operands()
                return MutatorUtils._operands_are_subset(
                    candidate_operands, new_operands
                )
            case _:
                return False

    def get_all_aliases(self) -> set[F.Expressions.Is]:
        return set(
            self.mutator.get_typed_expressions(
                F.Expressions.Is,
                include_terminated=True,
                required_traits=(F.Expressions.is_predicate,),
            )
        )

    def get_all_subsets(self) -> set[F.Expressions.IsSubset]:
        return set(
            self.mutator.get_typed_expressions(
                F.Expressions.IsSubset,
                include_terminated=True,
                required_traits=(F.Expressions.is_predicate,),
            )
        )

    def collect_factors[T: F.Expressions.Multiply | F.Expressions.Power](
        self,
        counter: Counter[F.Parameters.is_parameter_operatable],
        collect_type: type[T],
    ) -> tuple[
        dict[F.Parameters.is_parameter_operatable, F.Literals.Numbers],
        list[F.Parameters.is_parameter_operatable],
    ]:
        # Convert the counter to a dict for easy manipulation
        factors: dict[
            F.Parameters.is_parameter_operatable,
            F.Literals.Numbers,
        ] = {op: self.mutator.make_lit(count) for op, count in counter.items()}
        # Store operations of type collect_type grouped by their non-literal operand
        same_literal_factors: dict[
            F.Parameters.is_parameter_operatable,
            list[F.Parameters.is_parameter_operatable],
        ] = defaultdict(list)

        # Look for operations matching collect_type and gather them
        for collect_op in set(factors.keys()):
            if not collect_op.get_obj().isinstance(collect_type):
                continue
            expr = collect_op.as_expression.force_get()
            # Skip if operation doesn't have exactly two operands
            # TODO unnecessary strict
            if len(expr.get_operands()) != 2:
                continue
            # handled by lit fold first
            if len(expr.get_operand_literals()) > 1:
                continue
            if not expr.get_operand_literals():
                continue
            # handled by lit fold completely
            if self.is_pure_literal_expression(collect_op.as_operand.get()):
                continue
            if not F.Expressions.is_commutative.is_commutative_type(
                collect_type.bind_typegraph(self.mutator.tg_in)
            ):
                if collect_type is not F.Expressions.Power:
                    raise NotImplementedError(
                        f"Non-commutative {collect_type.__name__} not implemented"
                    )
                # For power, ensure second operand is literal
                if not self.is_literal(expr.get_operands()[1]):
                    continue

            # pick non-literal operand
            paramop = next(iter(expr.get_operand_operatables()))
            # Collect these factors under the non-literal operand
            same_literal_factors[paramop].append(collect_op)
            # If this operand isn't in factors yet, initialize it with 0
            if paramop not in factors:
                factors[paramop] = self.mutator.make_lit(0)
            # Remove this operation from the main factors
            del factors[collect_op]

        # new_factors: combined literal counts, old_factors: leftover items
        new_factors: dict[F.Parameters.is_parameter_operatable, F.Literals.Numbers] = {}
        old_factors = list[F.Parameters.is_parameter_operatable]()

        # Combine literals for each non-literal operand
        for var, count in factors.items():
            muls = same_literal_factors[var]
            # If no effective multiplier or only a single factor, treat as leftover
            if count.try_get_single() == 0 and len(muls) <= 1:
                old_factors.extend(muls)
                continue

            # If only count=1 and no additional factors, just keep the variable
            if count.try_get_single() == 1 and not muls:
                old_factors.append(var)
                continue

            # Extract literal parts from collected operations
            mul_lits = [
                next(
                    fabll.Traits(o_lit).get_obj(F.Literals.Numbers)
                    for o_lit in mul.as_expression.force_get()
                    .get_operand_literals()
                    .values()
                )
                for mul in muls
            ]

            # Sum all literal multipliers plus the leftover count
            new_factors[var] = count.op_add_intervals(*mul_lits)

        return new_factors, old_factors

    # TODO better name
    @staticmethod
    def fold_op[T: F.Literals.LiteralNodes](
        operands: Sequence[F.Literals.is_literal],
        operator: Callable[[T, T], T],
        lit_t: type[T],
        identity: F.Literals.LiteralValues,
    ) -> list[F.Literals.is_literal]:
        """
        Return 'sum' of all literals in the iterable, or empty list if sum is identity.
        """
        if not operands:
            return []

        literal_it = iter(operands)
        const_sum = fabll.Traits(next(literal_it)).get_obj(lit_t)
        for c in literal_it:
            c_lit = fabll.Traits(c).get_obj(lit_t)
            const_sum = operator(const_sum, c_lit)

        const_sum_lit = const_sum.get_trait(F.Literals.is_literal)

        # TODO make work with all the types
        if const_sum_lit.equals_singleton(identity):
            return []

        return [const_sum_lit]

    @staticmethod
    def are_aliased(
        po: F.Parameters.is_parameter_operatable,
        *other: F.Parameters.is_parameter_operatable,
    ) -> bool:
        return bool(
            po.get_operations(F.Expressions.Is, predicates_only=True)
            & {
                o
                for o in other
                for o in o.get_operations(F.Expressions.Is, predicates_only=True)
            }
        )

    @staticmethod
    def is_literal(
        po: F.Parameters.can_be_operand,
    ) -> F.Literals.is_literal | None:
        # allowed because of canonicalization
        return po.as_literal.try_get()

    @staticmethod
    def is_numeric_literal(
        po: F.Parameters.can_be_operand,
    ) -> F.Literals.Numbers | None:
        return fabll.Traits(po).get_obj_raw().try_cast(F.Literals.Numbers)

    @staticmethod
    def is_literal_expression(
        po: F.Parameters.can_be_operand,
    ) -> F.Expressions.is_expression | None:
        if not (
            (po_po := po.as_parameter_operatable.try_get())
            and (po_expr := po_po.as_expression.try_get())
        ):
            return None
        if has_non_lits := po_expr.get_operands_with_trait(  # noqa: F841
            F.Parameters.is_parameter, recursive=True
        ):
            return None
        return po_expr

    @staticmethod
    def is_pure_literal_expression(
        po: F.Parameters.can_be_operand,
    ) -> F.Expressions.is_expression | None:
        if not (
            (po_po := po.as_parameter_operatable.try_get())
            and (po_expr := po_po.as_expression.try_get())
        ):
            return None
        all_lits = all(MutatorUtils.is_literal(op) for op in po_expr.get_operands())
        if not all_lits:
            return None
        return po_expr

    @staticmethod
    def is_alias_is_literal(
        po: F.Parameters.is_parameter_operatable,
    ) -> F.Expressions.Is | None:
        if not (expr := po.as_expression.try_get()):
            return None
        if not (po_is := fabll.Traits(po).get_obj_raw().try_cast(F.Expressions.Is)):
            return None
        if not po.try_get_sibling_trait(F.Expressions.is_predicate):
            return None
        if not expr.get_operand_literals():
            return None
        if not expr.get_operand_operatables():
            return None
        return po_is

    @staticmethod
    def is_subset_literal(
        po: F.Parameters.is_parameter_operatable,
    ) -> F.Expressions.IsSubset | None:
        """
        A ss! X
        -> return True
        """
        if not (
            po_ss := fabll.Traits(po).get_obj_raw().try_cast(F.Expressions.IsSubset)
        ):
            return None
        po_expr = po.as_expression.force_get()
        if not po_expr.try_get_sibling_trait(F.Expressions.is_predicate):
            return None
        if not (lits := po_expr.get_operand_literals()):
            return None
        if not po_expr.get_operand_operatables():
            return None
        # don't return X ss! A
        if not set(lits.keys()) == {1}:
            return None
        return po_ss

    def no_other_predicates(
        self,
        po: F.Parameters.is_parameter_operatable,
        *other: F.Expressions.is_assertable,
        unfulfilled_only: bool = False,
    ) -> bool:
        no_other_predicates = (
            len(
                [
                    x
                    for x in MutatorUtils.get_predicates_involved_in(po).difference(
                        other
                    )
                    if not unfulfilled_only
                    or not (
                        (pred := x.try_get_trait(F.Expressions.is_predicate))
                        and self.mutator.is_predicate_terminated(pred)
                    )
                ]
            )
            == 0
        )
        return no_other_predicates and not po.has_implicit_predicates_recursive()

    @dataclass
    class FlattenAssociativeResult:
        extracted_operands: list[F.Parameters.can_be_operand]
        """
        Extracted operands
        """
        destroyed_operations: set[F.Expressions.is_expression]
        """
        ParameterOperables that got flattened and thus are not used anymore
        """

    @staticmethod
    def flatten_associative(
        to_flatten: F.Expressions.is_flattenable,
        check_destructable: Callable[
            [F.Expressions.is_expression, F.Expressions.is_expression], bool
        ],
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

        out = MutatorUtils.FlattenAssociativeResult(
            extracted_operands=[],
            destroyed_operations=set(),
        )

        to_flatten_expr = to_flatten.get_sibling_trait(F.Expressions.is_expression)
        is_associative = bool(
            to_flatten.try_get_sibling_trait(F.Expressions.is_associative)
        )
        to_flatten_obj = fabll.Traits(to_flatten).get_obj_raw()

        def can_be_flattened(
            o: F.Parameters.can_be_operand,
        ) -> bool:
            if not is_associative:
                if not to_flatten_expr.get_operands()[0].is_same(o):
                    return False
            if not fabll.Traits(o).get_obj_raw().has_same_type_as(to_flatten_obj):
                return False
            if not check_destructable(
                o.get_sibling_trait(F.Expressions.is_expression), to_flatten_expr
            ):
                return False
            return True

        non_compressible_operands, nested_compressible_operations = map(
            list,
            partition(
                can_be_flattened,
                to_flatten_expr.get_operands(),
            ),
        )
        out.extracted_operands.extend(non_compressible_operands)

        nested_extracted_operands = []
        for nested_to_flatten in nested_compressible_operations:
            nested_to_flatten_po = nested_to_flatten.as_parameter_operatable.force_get()
            nested_to_flatten_expr = nested_to_flatten_po.as_expression.force_get()

            out.destroyed_operations.add(nested_to_flatten_expr)

            res = MutatorUtils.flatten_associative(
                nested_to_flatten.get_sibling_trait(F.Expressions.is_flattenable),
                check_destructable,
            )
            nested_extracted_operands += res.extracted_operands
            out.destroyed_operations.update(res.destroyed_operations)

        out.extracted_operands.extend(nested_extracted_operands)

        return out

    @staticmethod
    def get_lit_mapping_from_lit_expr(
        expr: F.Expressions.Is | F.Expressions.IsSubset,
    ) -> tuple[F.Parameters.is_parameter_operatable, F.Literals.is_literal]:
        """
        A is! X, X is! A, A ss! X
        -> return (A, X)
        """
        e = expr.is_expression.get()
        e_po = e.as_parameter_operatable.get()
        assert MutatorUtils.is_alias_is_literal(e_po) or MutatorUtils.is_subset_literal(
            e_po
        )
        non_lits = e.get_operand_operatables()
        lits = e.get_operand_literals()
        assert len(non_lits) == 1
        assert len(lits) == 1
        if isinstance(expr, F.Expressions.IsSubset):
            # don't do X ss! A
            assert set(lits.keys()) == {1}
        return next(iter(non_lits)), next(iter(lits.values()))

    @staticmethod
    def get_params_for_expr(
        expr: F.Expressions.is_expression,
    ) -> set[F.Parameters.is_parameter]:
        param_ops = expr.get_operands_with_trait(F.Parameters.is_parameter)
        expr_ops = expr.get_operands_with_trait(F.Expressions.is_expression)

        return param_ops | {
            op for e in expr_ops for op in MutatorUtils.get_params_for_expr(e)
        }

    # TODO make generator
    @staticmethod
    def get_expressions_involved_in[T: fabll.NodeT](
        p: F.Parameters.is_parameter_operatable,
        type_filter: type[T] = fabll.Node,
        include_root: bool = False,
        up_only: bool = True,
        require_trait: type[fabll.NodeT] | None = None,
    ) -> set[T]:
        dependants = p.get_operations(recursive=True)
        if e := p.as_expression.try_get():
            if include_root:
                dependants.add(fabll.Traits(e).get_obj_raw())

            if not up_only:
                dependants.update(
                    [
                        fabll.Traits(op).get_obj_raw()
                        for op in e.get_operands_with_trait(
                            F.Expressions.is_expression, recursive=True
                        )
                    ]
                )

        res = {
            t
            for p in dependants
            if (t := p.try_cast(type_filter))
            and (not require_trait or p.has_trait(require_trait))
        }
        return res

    @staticmethod
    def get_predicates_involved_in[T: fabll.NodeT](
        p: F.Parameters.is_parameter_operatable,
        type_filter: type[T] = fabll.Node,
    ) -> set[T]:
        return MutatorUtils.get_expressions_involved_in(
            p, type_filter, require_trait=F.Expressions.is_predicate
        )

    @staticmethod
    def get_relevant_predicates(
        *op: F.Parameters.can_be_operand,
    ) -> set[F.Expressions.is_predicate]:
        # get all root predicates
        leaves = set(op)
        roots = set[F.Expressions.is_predicate]()
        while True:
            new_roots = {
                e.get_sibling_trait(F.Expressions.is_predicate)
                for e in F.Parameters.can_be_operand.get_root_operands(
                    *leaves, predicates_only=True
                )
            } - roots

            # get leaves for transitive predicates
            # A >! B, B >! C => only A >! B is in roots
            leaves = {
                leaf.as_operand.get()
                for root in new_roots
                for leaf in root.as_expression.get().get_operand_leaves_operatable()
            } - leaves

            roots.update(new_roots)

            if not leaves:
                return roots

    @staticmethod
    def get_correlations(
        expr: F.Expressions.is_expression,
        exclude: set[F.Expressions.is_expression] | None = None,
    ):
        # TODO: might want to check if expr has aliases because those are correlated too

        if exclude is None:
            exclude = set()

        exclude.add(expr)
        excluded = {
            e for e in exclude if e.try_get_sibling_trait(F.Expressions.is_predicate)
        }
        excluded.update(
            is_.is_expression.get()
            for is_ in MutatorUtils.get_predicates_involved_in(
                expr.as_parameter_operatable.get(), F.Expressions.Is
            )
        )

        operables = [
            o_po
            for o in expr.get_operands()
            if (o_po := o.as_parameter_operatable.try_get())
        ]
        op_set = set(operables)

        def _get(e: F.Parameters.is_parameter_operatable):
            vs = {e}
            if e_expr := e.as_expression.try_get():
                vs = e_expr.get_operand_leaves_operatable()
            return {
                o
                for v in vs
                for o in MutatorUtils.get_predicates_involved_in(v, F.Expressions.Is)
            }

        exprs = {o: _get(o) for o in op_set}
        # check disjoint sets
        for e1, e2 in combinations(operables, 2):
            if e1.is_same(e2):
                yield e1, e2, exprs[e1].difference(excluded)
            overlap = (exprs[e1] & exprs[e2]).difference(excluded)
            if overlap:
                yield e1, e2, overlap

    @staticmethod
    def find_unique_params(
        po: F.Parameters.can_be_operand,
    ) -> set[F.Parameters.is_parameter_operatable]:
        if (po_op := po.as_parameter_operatable.try_get()) and (
            po_op.as_parameter.try_get()
        ):
            return {po_op}
        if (po_op := po.as_parameter_operatable.try_get()) and (
            po_expr := po_op.as_expression.try_get()
        ):
            return {
                p
                for op in po_expr.get_operands()
                for p in MutatorUtils.find_unique_params(op)
            }
        return set()

    @staticmethod
    def count_param_occurrences(
        po: F.Parameters.is_parameter_operatable,
    ) -> dict[F.Parameters.is_parameter, int]:
        counts: dict[F.Parameters.is_parameter, int] = defaultdict(int)

        if p := po.as_parameter.try_get():
            counts[p] += 1
        if po_expr := po.as_expression.try_get():
            for op in po_expr.get_operands():
                if not (op_po := op.as_parameter_operatable.try_get()):
                    continue
                for param, count in MutatorUtils.count_param_occurrences(op_po).items():
                    counts[param] += count
        return counts

    @staticmethod
    def is_correlatable_literal(op: F.Literals.is_literal):
        if not MutatorUtils.is_literal(op.as_operand.get()):
            return False
        return op.is_singleton() or op.is_empty()

    @staticmethod
    def get_supersets(
        op: F.Parameters.is_parameter_operatable,
    ) -> Mapping[F.Parameters.can_be_operand, list[F.Expressions.IsSubset]]:
        ss = [
            e
            for e in op.get_operations(F.Expressions.IsSubset, predicates_only=True)
            if e.is_expression.get().get_operands()[0].is_same(op.as_operand.get())
        ]
        return groupby(ss, key=lambda e: e.is_expression.get().get_operands()[1])

    @staticmethod
    def get_aliases(
        op: F.Parameters.is_parameter_operatable,
    ) -> dict[F.Parameters.can_be_operand, F.Expressions.Is]:
        return {
            other_p: e
            for e in op.get_operations(F.Expressions.Is, predicates_only=True)
            if (other_p := e.get_other_operand(op.as_operand.get()))
        }

    def merge_parameters(
        self,
        params: Iterable[F.Parameters.is_parameter],
    ) -> F.Parameters.is_parameter:
        params = list(params)
        if not params:
            raise ValueError("No parameters provided")

        p_type_repr = fabll.Traits(params[0]).get_obj_raw()

        if p_type_repr.isinstance(F.Parameters.NumericParameter):
            new = (
                F.Parameters.NumericParameter.bind_typegraph(self.mutator.tg_out)
                .create_instance(self.mutator.G_out)
                .setup(
                    # units removed in canonicalization
                    is_unit=F.Units.Dimensionless.bind_typegraph(self.mutator.tg_out)
                    .create_instance(self.mutator.G_out)
                    .is_unit.get(),
                    domain=F.Parameters.NumericParameter.DOMAIN_SKIP,
                )
            )
            return new.is_parameter.get()
        elif p_type_repr.isinstance(F.Parameters.BooleanParameter):
            new = (
                F.Parameters.BooleanParameter.bind_typegraph(self.mutator.tg_out)
                .create_instance(self.mutator.G_out)
                .setup()
            )
            return new.is_parameter.get()
        elif p_type_repr.isinstance(F.Parameters.StringParameter):
            new = (
                F.Parameters.StringParameter.bind_typegraph(self.mutator.tg_out)
                .create_instance(self.mutator.G_out)
                .setup()
            )
            return new.is_parameter.get()
        elif p_type_repr.isinstance(F.Parameters.EnumParameter):
            enum = F.Parameters.EnumParameter.check_single_single_enum(
                [fabll.Traits(p).get_obj(F.Parameters.EnumParameter) for p in params]
            )
            new = (
                F.Parameters.EnumParameter.bind_typegraph(self.mutator.tg_out)
                .create_instance(self.mutator.G_out)
                .setup(enum=enum)
            )
            return new.is_parameter.get()
        else:
            raise TypeError(f"Unknown parameter type: {p_type_repr}")

    @staticmethod
    def hack_get_expr_type(expr: F.Expressions.is_expression) -> type[fabll.NodeT]:
        # TODO this is a hack, we should not do it like this
        # better build something into is_expression trait that allows copying
        type_node = not_none(fabll.Traits(expr).get_obj_raw().get_type_node())
        expression_factory = fabll.TypeNodeBoundTG.__TYPE_NODE_MAP__[type_node].t
        return expression_factory
