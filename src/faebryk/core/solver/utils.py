# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
from collections import defaultdict
from typing import (
    TYPE_CHECKING,
    Callable,
    Iterable,
    Mapping,
    Sequence,
)

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.logging_utils import rich_to_string
from faebryk.core import graph
from faebryk.libs.util import (
    ConfigFlag,
    ConfigFlagFloat,
    ConfigFlagInt,
    OrderedSet,
    not_none,
    unique_ref,
)

if TYPE_CHECKING:
    from faebryk.core.solver.mutator import ExpressionBuilder, Mutator


logger = logging.getLogger(__name__)

# Config -------------------------------------------------------------------------------
LOG_PICK_SOLVE = ConfigFlag("LOG_PICK_SOLVE", False)
S_LOG = ConfigFlag("SLOG", default=False, descr="Log solver operations")
VERBOSE_TABLE = ConfigFlag("SVERBOSE_TABLE", default=False, descr="Verbose table")
SHOW_SS_IS = ConfigFlag(
    "SSHOW_SS_IS",
    default=False,
    descr="Show subset/is predicates in graph print",
)
PRINT_START = ConfigFlag("SPRINT_START", default=False, descr="Print start of solver")
MAX_ITERATIONS_HEURISTIC = int(
    ConfigFlagInt("SMAX_ITERATIONS", default=10, descr="Max iterations")
)
TIMEOUT = ConfigFlagFloat("STIMEOUT", default=150, descr="Solver timeout").get()
ALLOW_PARTIAL_STATE = ConfigFlag("SPARTIAL", default=True, descr="Allow partial state")
# --------------------------------------------------------------------------------------

if S_LOG:
    logger.setLevel(logging.DEBUG)


def set_log_level(level: int):
    from faebryk.core.solver.mutator import logger as mutator_logger
    from faebryk.core.solver.solver import logger as solver_logger

    loggers = [logger, mutator_logger, solver_logger]
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
        print_ctx = self.mutator.mutation_map.print_ctx

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
        constraint_sources: list[F.Parameters.is_parameter_operatable] | None = None,
        constraint_expr_pairs: Iterable[
            tuple[F.Literals.is_literal, F.Expressions.IsSubset]
        ]
        | None = None,
    ):
        super().__init__(msg, involved, mutator)
        self.literals = literals
        sources: list[F.Parameters.is_parameter_operatable] = []
        if constraint_sources is not None:
            # Trace back constraint sources through the mutation map to find
            # the original expressions in the instance graph with source chunks
            for src in constraint_sources:
                traced = mutator.mutation_map.map_backward(src)
                if traced:
                    sources.extend(traced)
                else:
                    sources.append(src)
        if constraint_expr_pairs is not None:
            sources.extend(
                self.get_original_constraints(constraint_expr_pairs, mutator)
            )
        self.constraint_sources = unique_ref(sources)

    def __str__(self):
        from atopile.compiler.ast_visitor import ASTVisitor

        def _format_source_chunk(node: fabll.Node) -> str | None:
            source_chunk = ASTVisitor.get_source_chunk(node.instance)
            if source_chunk is None:
                return None
            return source_chunk.loc.get().get_full_location()

        literals_lines = []
        for lit in self.literals:
            source = _format_source_chunk(fabll.Traits(lit).get_obj_raw())
            literal_str = lit.pretty_str()
            if source:
                literals_lines.append(f" - {literal_str} ({source})")
            else:
                literals_lines.append(f" - {literal_str}")

        parts = [super().__str__()]

        if self.constraint_sources:
            context = self.mutator.mutation_map.print_ctx

            def _has_bounded_literal(
                expr: F.Parameters.is_parameter_operatable,
            ) -> bool:
                try:
                    if expr_expr := expr.as_expression.try_get():
                        expr_trait = expr_expr
                    else:
                        return False
                    literals = list(expr_trait.get_operand_literals().values())
                    for operand in expr_trait.get_operands():
                        if lit := operand.as_literal.try_get():
                            literals.append(lit)

                    for lit in literals:
                        lit_obj = fabll.Traits(lit).get_obj_raw()
                        if numbers := lit_obj.try_cast(F.Literals.Numbers):
                            import math

                            min_val = numbers.get_min_value()
                            max_val = numbers.get_max_value()
                            if not math.isinf(min_val) and not math.isinf(max_val):
                                return True
                        else:
                            return True
                    return False
                except Exception:
                    return False

            def _safe_compact_repr(
                expr: F.Parameters.is_parameter_operatable,
            ) -> str:
                try:
                    return expr.compact_repr(context, use_name=True)
                except Exception as exc:
                    return f"<unprintable constraint {type(exc).__name__}>"

            constraint_lines = []
            for constraint in self.constraint_sources:
                source = _format_source_chunk(fabll.Traits(constraint).get_obj_raw())
                constraint_str = _safe_compact_repr(constraint)
                if source or _has_bounded_literal(constraint):
                    if source:
                        constraint_lines.append(f" - {constraint_str} ({source})")
                    else:
                        constraint_lines.append(f" - {constraint_str}")
            parts.append("Constraints:\n" + "\n".join(constraint_lines))

        parts.append("Literals:\n" + "\n".join(literals_lines))
        return "\n\n".join(parts)

    @staticmethod
    def get_original_constraints(
        lit_expr_pairs: Iterable[tuple[F.Literals.is_literal, F.Expressions.IsSubset]],
        mutator: "Mutator",
    ) -> list[F.Parameters.is_parameter_operatable]:
        """
        Resolve the earliest constraint expressions for a set of subset expressions.
        """
        roots: list[F.Parameters.is_parameter_operatable] = []
        for _, ss_expr in lit_expr_pairs:
            ss_expr_po = ss_expr.get_trait(F.Parameters.is_parameter_operatable)
            roots.extend(mutator.mutation_map.map_backward(ss_expr_po))
        return unique_ref(roots)


class MutatorUtils:
    def __init__(self, mutator: "Mutator"):
        self.mutator = mutator

    def make_number_literal_from_range(
        self, lower: float, upper: float
    ) -> F.Literals.Numbers:
        return (
            F.Literals.Numbers.bind_typegraph(self.mutator.tg_in)
            .create_instance(self.mutator.G_transient)
            .setup_from_min_max(
                lower,
                upper,
                unit=None,
            )
        )

    # literal extraction ---------------------------------------------------------------

    def try_extract_superset(
        self,
        po: F.Parameters.is_parameter_operatable,
    ) -> F.Literals.is_literal | None:
        # TODO check if empty set?
        return po.try_extract_superset()

    def try_extract_subset(
        self,
        po: F.Parameters.is_parameter_operatable,
    ) -> F.Literals.is_literal | None:
        return po.try_extract_subset()

    def map_operands_extracted_supersets(
        self,
        expr: F.Expressions.is_expression,
    ) -> tuple[
        list[F.Parameters.can_be_operand], list[F.Parameters.is_parameter_operatable]
    ]:
        """
        return operands, but replaced with superset if they have one
        returns (
            mapped: [literal operand | extracted superset | non-superset operand],
            info: [operands with superset]
        )
        """
        out = list[F.Parameters.can_be_operand]()
        any_lit = list[F.Parameters.is_parameter_operatable]()
        for op in expr.get_operands():
            if self.is_literal(op):
                out.append(op)
                continue
            op_po = op.as_parameter_operatable.force_get()
            lit = self.try_extract_superset(op_po)
            if lit is None:
                out.append(op)
                continue
            out.append(lit.as_operand.get())
            any_lit.append(op_po)
        return out, any_lit

    # ----------------------------------------------------------------------------------
    @staticmethod
    def get_op_supersets(
        op: F.Parameters.is_parameter_operatable,
    ) -> Mapping[F.Parameters.can_be_operand, F.Expressions.IsSubset]:
        return {
            e.get_superset_operand(): e
            for e in op.get_operations(F.Expressions.IsSubset, predicates_only=True)
            if e.get_subset_operand().is_same(op.as_operand.get())
        }

    def is_replacable_by_literal(
        self, op: F.Parameters.can_be_operand
    ) -> F.Literals.is_literal | None:
        if not (op_po := op.as_parameter_operatable.try_get()):
            return None

        lit = self.try_extract_superset(op_po)
        if lit is None:
            return None
        if not self.is_correlatable_literal(lit):
            return None
        return lit

    # TODO better name
    @staticmethod
    def fold_op[T: F.Literals.LiteralNodes](
        operands: Sequence[F.Literals.is_literal],
        operator: Callable[[T, T], T],
        lit_t: type[T],
        identity: F.Literals.LiteralValues,
    ) -> F.Literals.is_literal | None:
        """
        Return 'sum' of all literals in the iterable, or empty list if sum is identity.
        """
        if not operands:
            return None

        literal_it = iter(operands)
        const_sum = fabll.Traits(next(literal_it)).get_obj(lit_t)
        for c in literal_it:
            c_lit = fabll.Traits(c).get_obj(lit_t)
            const_sum = operator(const_sum, c_lit)

        const_sum_lit = const_sum.get_trait(F.Literals.is_literal)

        # TODO make work with all the types
        if const_sum_lit.op_setic_equals_singleton(identity):
            return None

        return const_sum_lit

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
    def is_set_literal_expression(
        po: F.Parameters.is_parameter_operatable,
        allow_subset_exprs: bool = True,
        allow_superset_exprs: bool = True,
    ) -> F.Expressions.IsSubset | None:
        """
        A ss! X (if allow_subset_exprs)
        X ss! A (if allow_superset_exprs)
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
        indexes = set(lits.keys())
        if not allow_subset_exprs and 1 in indexes:
            return None
        if not allow_superset_exprs and 0 in indexes:
            return None
        return po_ss

    @staticmethod
    def is_correlatable_literal(op: F.Literals.is_literal):
        if not MutatorUtils.is_literal(op.as_operand.get()):
            return False
        return op.op_setic_is_singleton() or op.op_setic_is_empty()

    @staticmethod
    def get_params_for_expr(
        expr: F.Expressions.is_expression,
    ) -> OrderedSet[F.Parameters.is_parameter]:
        param_ops = expr.get_operands_with_trait(F.Parameters.is_parameter)
        expr_ops = expr.get_operands_with_trait(F.Expressions.is_expression)

        result = OrderedSet(param_ops)
        for e in expr_ops:
            result.update(MutatorUtils.get_params_for_expr(e))
        return result

    @staticmethod
    def get_relevant_predicates(
        *op: F.Parameters.can_be_operand,
    ) -> OrderedSet[F.Expressions.is_predicate]:
        if not op:
            return OrderedSet()

        tg = next(iter(op)).tg

        anticorrelated_pairs = MutatorUtils.get_anticorrelated_pairs(tg)
        original_params = {
            p
            for o in op
            if (po := o.as_parameter_operatable.try_get())
            and (p := po.as_parameter.try_get())
        }
        visited_params = OrderedSet(original_params)
        leaves = OrderedSet(op)
        roots: OrderedSet[F.Expressions.is_predicate] = OrderedSet()

        while True:
            new_roots = (
                OrderedSet(
                    e.get_sibling_trait(F.Expressions.is_predicate)
                    for e in F.Parameters.can_be_operand.get_root_operands(
                        *leaves, predicates_only=True
                    )
                )
                - roots
            )

            # get leaves for transitive predicates
            # A >! B, B >! C => only A >! B is in roots
            # Skip leaves that are anticorrelated with any original relevant param
            new_leaves: OrderedSet[F.Parameters.can_be_operand] = OrderedSet()
            for root in new_roots:
                for leaf_po in root.as_expression.get().get_operand_leaves_operatable():
                    if (
                        leaf_param := leaf_po.as_parameter.try_get()
                    ) is None or leaf_param in visited_params:
                        continue

                    # Prevent Not(Correlated(A,B,C,...)) from creating a spurious
                    # transitive closure
                    if any(
                        frozenset({orig, leaf_param}) in anticorrelated_pairs
                        for orig in original_params
                    ):
                        continue

                    new_leaves.add(leaf_po.as_operand.get())
                    visited_params.add(leaf_param)

            leaves = new_leaves
            roots.update(new_roots)

            if not leaves:
                return roots

    @staticmethod
    def find_unique_params(
        po: F.Parameters.can_be_operand,
    ) -> OrderedSet[F.Parameters.is_parameter_operatable]:
        if (po_op := po.as_parameter_operatable.try_get()) and (
            po_op.as_parameter.try_get()
        ):
            return OrderedSet([po_op])
        if (po_op := po.as_parameter_operatable.try_get()) and (
            po_expr := po_op.as_expression.try_get()
        ):
            return OrderedSet(
                p
                for op in po_expr.get_operands()
                for p in MutatorUtils.find_unique_params(op)
            )
        return OrderedSet()

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
    def get_anticorrelated_pairs(
        tg: "fbrk.TypeGraph",
    ) -> set[frozenset["F.Parameters.is_parameter"]]:
        """
        Collect all parameter pairs that are explicitly marked as uncorrelated
        via Not(Correlated(...)) expressions.
        """
        from itertools import combinations

        out: set[frozenset[F.Parameters.is_parameter]] = set()

        for expr in F.Expressions.Correlated.bind_typegraph(tg).get_instances():
            expr_op = expr.can_be_operand.get()
            expr_e = expr.is_expression.get()
            if not expr_op.get_operations(
                types=F.Expressions.Not, recursive=False, predicates_only=True
            ):
                continue

            corr_params = [
                p
                for leaf in expr_e.get_operand_leaves_operatable()
                if (p := leaf.as_parameter.try_get())
            ]

            for p1, p2 in combinations(corr_params, 2):
                out.add(frozenset([p1, p2]))

        return out

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
        elif p_type_repr.isinstance(F.Parameters.BooleanParameter):
            new = (
                F.Parameters.BooleanParameter.bind_typegraph(self.mutator.tg_out)
                .create_instance(self.mutator.G_out)
                .setup()
            )
        elif p_type_repr.isinstance(F.Parameters.StringParameter):
            new = (
                F.Parameters.StringParameter.bind_typegraph(self.mutator.tg_out)
                .create_instance(self.mutator.G_out)
                .setup()
            )
        elif p_type_repr.isinstance(F.Parameters.EnumParameter):
            enum = F.Parameters.EnumParameter.check_single_single_enum(
                [fabll.Traits(p).get_obj(F.Parameters.EnumParameter) for p in params]
            )
            new = (
                F.Parameters.EnumParameter.bind_typegraph(self.mutator.tg_out)
                .create_instance(self.mutator.G_out)
                .setup(enum=enum)
            )
        else:
            raise TypeError(f"Unknown parameter type: {p_type_repr}")
        new_p = new.is_parameter.get()
        self.mutator.print_ctx.override_name(
            new_p,
            self.mutator.print_ctx.get_or_create_name(params[0]),
        )
        return new_p

    @staticmethod
    def hack_get_expr_type(
        expr: F.Expressions.is_expression,
    ) -> type[F.Expressions.ExpressionNodes]:
        # TODO this is a hack, we should not do it like this
        # better build something into is_expression trait that allows copying
        type_node = not_none(fabll.Traits(expr).get_obj_raw().get_type_node())
        expression_factory = fabll.TypeNodeBoundTG.__TYPE_NODE_MAP__[type_node].t
        return expression_factory

    def mutator_neutralize_expressions(
        self, expr: F.Expressions.is_expression
    ) -> F.Parameters.is_parameter_operatable:
        """
        '''
        op(op_inv(A), ...) -> A
        op!(op_inv(A), ...) -> A!
        '''
        """
        inner_expr_rep = expr.get_operands()[0]
        if not (
            (inner_expr_po := inner_expr_rep.as_parameter_operatable.try_get())
            and (inner_expr_e := inner_expr_po.as_expression.try_get())
        ):
            raise ValueError("Inner operand must be an expression")
        inner_operand = inner_expr_e.get_operands()[0]
        if not (inner_operand_po := inner_operand.as_parameter_operatable.try_get()):
            raise ValueError("Unpacked operand can't be a literal")
        out = self.mutator._mutate(
            expr.as_parameter_operatable.get(),
            self.mutator.get_copy_po(inner_operand_po),
        )
        if expr.try_get_sibling_trait(F.Expressions.is_predicate) and (
            out_assertable := out.try_get_sibling_trait(F.Expressions.is_assertable)
        ):
            self.mutator.assert_(out_assertable)
        return out

    def mutate_unpack_expression(
        self,
        expr: F.Expressions.is_expression,
        operands: list[F.Parameters.is_parameter_operatable] | None = None,
    ) -> F.Parameters.is_parameter_operatable:
        """
        ```
        op(A, ...) -> A
        op!(E, ...) -> E!
        op!(P, ...) -> P & P is! True
        ```
        """
        unpacked = (
            expr.get_operands()[0].as_parameter_operatable.force_get()
            if operands is None
            else operands[0]
        )
        if unpacked is None:
            raise ValueError("Unpacked operand can't be a literal")
        out = self.mutator._mutate(
            expr.as_parameter_operatable.get(),
            self.mutator.get_copy_po(unpacked),
        )
        if expr.try_get_sibling_trait(F.Expressions.is_predicate):
            if (expression := out.as_expression.try_get()) and (
                assertable := expression.as_assertable.try_get()
            ):
                self.mutator.assert_(assertable)
            else:
                self.mutator.create_check_and_insert_expression(
                    F.Expressions.IsSubset,
                    out.as_operand.get(),
                    self.mutator.make_singleton(True).can_be_operand.get(),
                    from_ops=[out, expr.as_parameter_operatable.get()],
                    assert_=True,
                    terminate=True,
                )
        return out


def pretty_expr(
    expr: "F.Expressions.is_expression | ExpressionBuilder",
    mutator: "Mutator | None" = None,
    context: "F.Parameters.ReprContext | None" = None,
    use_name: bool = False,
    no_lit_suffix: bool = False,
) -> str:
    from faebryk.core.solver.mutator import ExpressionBuilder

    context = context or (mutator.print_ctx if mutator else F.Parameters.ReprContext())

    match expr:
        case ExpressionBuilder():
            if expr.operands:
                tg = expr.operands[0].tg
            else:
                g = graph.GraphView.create()
                tg = fbrk.TypeGraph.create(g=g)

            factory_type = fabll.TypeNodeBoundTG(tg, expr.factory)
            is_expr_type = factory_type.try_get_type_trait(
                F.Expressions.is_expression_type
            )
            if is_expr_type is None:
                raise ValueError(
                    f"Factory {expr.factory} has no is_expression_type trait"
                )
            repr_style = is_expr_type.get_repr_style()

            return F.Expressions.is_expression._compact_repr(
                context,
                repr_style,
                repr_style.symbol
                if repr_style.symbol is not None
                else expr.factory.__name__,
                bool(expr.assert_),
                bool(expr.terminate),
                "",
                False,
                factory_type.get_type_name(),
                expr.operands or [],
                no_lit_suffix=no_lit_suffix,
            )
        case F.Expressions.is_expression():
            return expr.compact_repr(
                context,
                use_name=use_name,
                no_lit_suffix=no_lit_suffix,
            )
        case _:
            raise ValueError(f"Unknown expression type: {type(expr)}")
