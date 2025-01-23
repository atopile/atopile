# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import io
import logging
import sys
from dataclasses import dataclass
from types import UnionType
from typing import Callable, Iterable, Iterator, cast

from rich.console import Console
from rich.table import Table

from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.parameter import (
    ConstrainableExpression,
    Domain,
    Expression,
    Is,
    IsSubset,
    Parameter,
    ParameterOperatable,
)
from faebryk.core.solver.utils import (
    S_LOG,
    SHOW_SS_IS,
    VERBOSE_TABLE,
    CanonicalOperation,
    SolverAlgorithm,
    SolverLiteral,
    SolverOperatable,
    get_graphs,
    make_if_doesnt_exist,
    try_extract_literal,
)
from faebryk.libs.exceptions import downgrade
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval,
    Quantity_Interval_Disjoint,
    Quantity_Set,
)
from faebryk.libs.units import HasUnit, Quantity, Unit, quantity
from faebryk.libs.util import (
    cast_assert,
    groupby,
    indented_container,
    not_none,
    once,
)

logger = logging.getLogger(__name__)

if S_LOG:
    logger.setLevel(logging.DEBUG)

type REPR_MAP = dict[ParameterOperatable, ParameterOperatable]


@dataclass
class AlgoResult:
    repr_map: REPR_MAP
    graphs: list[Graph]
    dirty: bool
    subset_dirty: bool


# TODO use Mutator everywhere instead of repr_maps
class Mutator:
    def __init__(
        self,
        G: Graph,
        tracked_param_ops: set[ParameterOperatable],
        print_context: ParameterOperatable.ReprContext,
        repr_map: REPR_MAP | None = None,
    ) -> None:
        self._G = G
        self.tracked_param_ops = tracked_param_ops
        self.repr_map = repr_map or {}
        self.removed = set()
        self.copied = set()
        self.print_context = print_context

        # TODO make api for contraining
        # TODO involve marked & new_ops in printing
        self.marked: list[ConstrainableExpression] = []
        self._old_ops = GraphFunctions(G).nodes_of_type(ParameterOperatable)
        self._new_ops: set[ParameterOperatable] = set()

    @property
    def G(self) -> Graph:
        g = self._G
        if g.node_count > 0:
            return g
        # Handle graph merge
        gs = get_graphs(self._old_ops)
        assert len(gs) == 1
        self._G = gs[0]
        return self._G

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
                raise ValueError(f"already mutated to: {self.get_mutated(po)}")

        if self.is_removed(po):
            raise ValueError("Object marked removed")

        self.repr_map[po] = new_po
        return new_po

    def _override_repr(self, po: ParameterOperatable, new_po: ParameterOperatable):
        """
        Do not use this if you don't understand the consequences.
        Honestly I don't.
        """
        # TODO not sure this is the best way to handle ghost exprs
        if po in self.repr_map:
            self._new_ops.add(self.repr_map[po])

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
        new_expr.non_operands = expr.non_operands

        for op in new_operands:
            if isinstance(op, ParameterOperatable):
                assert (
                    op.get_graph() == new_expr.get_graph()
                ), f"Graph mismatch: {op.get_graph()} != {new_expr.get_graph()}"

        if isinstance(expr, ConstrainableExpression):
            new_expr = cast_assert(ConstrainableExpression, new_expr)
            new_expr.constrained = expr.constrained
            if self.is_predicate_true(expr):
                self.mark_predicate_true(new_expr)

        return self._mutate(expr, new_expr)

    def mutate_unpack_expression(self, expr: Expression) -> ParameterOperatable:
        """
        '''
        op(A, ...) -> A
        '''
        """
        unpacked = expr.operands[0]
        if not isinstance(unpacked, ParameterOperatable):
            raise ValueError("Unpacked operand can't be a literal")
        return self._mutate(expr, unpacked)

    def mutator_neutralize_expressions(self, expr: Expression) -> ParameterOperatable:
        """
        '''
        op(op_inv(A), ...) -> A
        '''
        """
        inner_expr = expr.operands[0]
        if not isinstance(inner_expr, Expression):
            raise ValueError("Inner operand must be an expression")
        inner_operand = inner_expr.operands[0]
        if not isinstance(inner_operand, ParameterOperatable):
            raise ValueError("Unpacked operand can't be a literal")
        return self._mutate(expr, inner_operand)

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

    def create_expression[T: CanonicalOperation](
        self,
        expr_factory: type[T],
        *operands: SolverOperatable,
        check_exists: bool = True,
    ) -> T:
        assert issubclass(expr_factory, CanonicalOperation)

        if check_exists:
            expr = make_if_doesnt_exist(expr_factory, *operands)
        else:
            expr = expr_factory(*operands)  # type: ignore
        self._new_ops.add(expr)
        return expr

    def remove(self, *po: ParameterOperatable):
        assert not any(p in self.repr_map for p in po), "Object already in repr_map"
        root_pos = [p for p in po if p.get_parent() is not None]
        assert not root_pos, f"should never remove root parameters: {root_pos}"
        self.removed.update(po)

    def remove_graph(self):
        # TODO implementing graph removal has to be more explicit
        # e.g mark as no more use, and then future mutators ignore it for the algos
        # for now at least remove expressions
        self.remove(*GraphFunctions(self.G).nodes_of_type(Expression))

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

    def register_created_parameter(self, param: Parameter):
        self._new_ops.add(param)
        return param

    @property
    def dirty(self) -> bool:
        return bool(self.needs_copy or self._new_ops or self.marked)

    def get_new_literal_aliases(self, tracked_param_ops_only: bool = False):
        """
        Find new ops which are Is expressions between a ParameterOperatable and a
        literal
        """

        def is_literal_alias(expr: ParameterOperatable) -> bool:
            if not isinstance(expr, Is):
                return False

            po = next(
                (op for op in expr.operands if isinstance(op, ParameterOperatable)),
                None,
            )

            lit = next(
                (op for op in expr.operands if try_extract_literal(op) is not None),
                None,
            )

            return (
                po is not None
                and lit is not None
                and (not tracked_param_ops_only or po in self.tracked_param_ops)
            )

        return (expr for expr in self._new_ops if is_literal_alias(expr))

    @property
    def subset_dirty(self) -> bool:
        """
        True if any ParameterOperatable (A) has been newly aliased to a literal, and A
        is involved in an expression `A op B` with another ParameterOperatable (B)
        """
        # FIXME: this is probably wrong
        # do we need to track the starting set of POs as with param_ops_subset_literals?

        return (
            next(self.get_new_literal_aliases(tracked_param_ops_only=True), None)
            is not None
        )

    @property
    def needs_copy(self) -> bool:
        # optimization: if just new_ops, no need to copy
        return bool(self.removed or self.repr_map)

    def check_no_illegal_mutations(self):
        # TODO should only run during dev

        # Check modifications to original graph
        post_mut_nodes = GraphFunctions(self.G).nodes_of_type(ParameterOperatable)
        removed = self._old_ops.difference(post_mut_nodes, self.removed)
        added = post_mut_nodes.difference(self._old_ops, self._new_ops)
        removed_compact = [op.compact_repr(self.print_context) for op in removed]
        added_compact = [op.compact_repr(self.print_context) for op in added]
        assert (
            not removed
        ), f"Mutator {self.G} removed {indented_container(removed_compact)}"
        assert not added, f"Mutator {self.G} added {indented_container(added_compact)}"

        # don't need to check original graph, done above seperately
        all_new_graphs = get_graphs(self.repr_map.values())
        all_new_params = {
            op
            for g in all_new_graphs
            for op in GraphFunctions(g).nodes_of_type(ParameterOperatable)
        }
        non_registered = all_new_params.difference(
            self._new_ops, self.repr_map.values()
        )
        if non_registered:
            compact = (op.compact_repr(self.print_context) for op in non_registered)
            graphs = get_graphs(non_registered)
            # FIXME: this is currently hit during legitimate build
            with downgrade(AssertionError, logger=logger, to_level=logging.DEBUG):
                assert False, (
                    f"Mutator {self.G} has non-registered new ops: "
                    f"{indented_container(compact)}."
                    f"{indented_container(graphs)}"
                )

    def close(self) -> REPR_MAP:
        self.check_no_illegal_mutations()
        if not self.needs_copy:
            return {
                po: po
                for po in GraphFunctions(self.G).nodes_of_type(ParameterOperatable)
            }
        self.copy_unmutated()

        assert self.G not in get_graphs(self.repr_map.values())
        return self.repr_map

    def mark_predicate_true(self, pred: ConstrainableExpression):
        assert pred.constrained
        if pred._solver_evaluates_to_true:
            return
        pred._solver_evaluates_to_true = True
        self.marked.append(pred)

    def is_predicate_true(self, pred: ConstrainableExpression) -> bool:
        return pred._solver_evaluates_to_true

    def mark_predicate_false(self, pred: ConstrainableExpression):
        assert pred.constrained
        if not pred._solver_evaluates_to_true:
            return
        pred._solver_evaluates_to_true = False
        self.marked.append(pred)

    def get_all_param_ops(self) -> set[ParameterOperatable]:
        return {
            op
            for g in get_graphs(self.repr_map.values())
            for op in GraphFunctions(g).nodes_of_type(ParameterOperatable)
        }

    def nodes_of_type[T: "ParameterOperatable"](
        self, t: type[T], sort_by_depth: bool = False
    ) -> list[T]:
        out = GraphFunctions(self.G).nodes_of_type(t)
        if sort_by_depth:
            out = ParameterOperatable.sort_by_depth(out, ascending=True)
        return list(out)

    def nodes_of_types(
        self,
        t: tuple[type[ParameterOperatable], ...] | UnionType,
        sort_by_depth: bool = False,
    ) -> list:
        out = GraphFunctions(self.G).nodes_of_types(t)
        out = cast(set[ParameterOperatable], out)
        if sort_by_depth:
            out = ParameterOperatable.sort_by_depth(out, ascending=True)
        return list(out)


class Mutators:
    def __init__(
        self,
        *graphs: Graph,
        tracked_param_ops: set[ParameterOperatable] | None = None,
        print_context: ParameterOperatable.ReprContext,
    ):
        self.mutators = [
            Mutator(g, tracked_param_ops=tracked_param_ops, print_context=print_context)
            for g in graphs
        ]
        self.result_repr_map = {}
        self.print_context = print_context

    def close(self) -> AlgoResult:
        result = AlgoResult(
            repr_map={},
            graphs=[],
            dirty=any(m.dirty for m in self.mutators),
            subset_dirty=any(m.subset_dirty for m in self.mutators),
        )

        if result.dirty:
            for m in self.mutators:
                result.repr_map.update(m.close())
            result.graphs = get_graphs(result.repr_map.values())

            assert not (
                set(m.G for m in self.mutators if m.needs_copy) & set(result.graphs)
            )

            self.result_repr_map = result.repr_map

        return result

    def run(self, algo: SolverAlgorithm):
        for m in self.mutators:
            algo(m)

    def __iter__(self) -> Iterator[Mutator]:
        return iter(self.mutators)

    @once
    def get_new_print_context(self) -> ParameterOperatable.ReprContext:
        context_old = self.print_context

        context_new = ParameterOperatable.ReprContext()
        context_new.variable_mapping.next_id = context_old.variable_mapping.next_id

        for s, d in self.result_repr_map.items():
            if isinstance(s, Parameter) and isinstance(d, Parameter):
                s.compact_repr(context_old)
                s_mapping = context_old.variable_mapping.mapping[s]
                d_mapping = context_new.variable_mapping.mapping.get(d, None)
                if d_mapping is None or d_mapping > s_mapping:
                    context_new.variable_mapping.mapping[d] = s_mapping

        return context_new

    def debug_print(self):
        if not self.result_repr_map:
            return

        if getattr(sys, "gettrace", lambda: None)():
            log = print
        else:
            log = logger.debug
            if not logger.isEnabledFor(logging.DEBUG):
                return

        context_old = self.print_context
        context_new = self.get_new_print_context()

        table = Table(title="Mutations", show_lines=True)
        table.add_column("Before")
        table.add_column("After")

        graphs = get_graphs(self.result_repr_map.values())

        new_ops = {op for m in self.mutators for op in m._new_ops}.difference(
            self.result_repr_map.values()
        )

        # TODO remove
        print(
            "SKIBIDI",
            {op for m in self.mutators for op in m._new_ops}
            & set(self.result_repr_map.values()),
        )

        rows: list[tuple[str, str]] = []

        for op in new_ops:
            rows.append(("new", op.compact_repr(context_new)))

        marked = {op for m in self.mutators for op in m.marked}.difference(
            new_ops, self.result_repr_map.values()
        )
        for op in marked:
            rows.append(("marked", op.compact_repr(context_new)))

        copied = {op for m in self.mutators for op in m.copied}

        for s, d in self.result_repr_map.items():
            if not VERBOSE_TABLE:
                if s in copied:
                    continue

                # for no-op mutations (non dirty)
                if s is d:
                    continue

            old = s.compact_repr(context_old)
            new = d.compact_repr(context_new)
            if VERBOSE_TABLE:
                old += "\n\n" + repr(s)
                new += "\n\n" + repr(d)
            if old == new:
                continue
            rows.append((old, new))

        for m in self.mutators:
            for s in m.removed:
                old = s.compact_repr(context_old)
                if VERBOSE_TABLE:
                    old += "\n\n" + repr(s)
                rows.append((old, "removed"))

        if rows:
            rows.sort(key=lambda r: tuple(r))
            for row in rows:
                table.add_row(*row)
            console = Console(record=True, width=80, file=io.StringIO())
            console.print(table)
            log(console.export_text(styles=True))

        # TODO remove
        if len(graphs) != len(self.mutators):
            logger.debug(
                f"Mutators created/destroyed graphs: "
                f"{len(self.mutators)} -> {len(graphs)}"
            )
            # Mutators.print_all(*graphs, context=context_new)

        return context_new

    @staticmethod
    def print_all(
        *graphs: Graph,
        context: ParameterOperatable.ReprContext,
        type_filter: type[ParameterOperatable] = ParameterOperatable,
        print_out: Callable[[str], None] = logger.debug,
    ):
        for i, g in enumerate(graphs):
            pre_nodes = GraphFunctions(g).nodes_of_type(type_filter)
            if SHOW_SS_IS:
                nodes = pre_nodes
            else:
                nodes = [
                    n
                    for n in pre_nodes
                    if not (
                        isinstance(n, (Is, IsSubset))
                        and n.constrained
                        and n._solver_evaluates_to_true
                        and (
                            # A is/ss Lit
                            any(ParameterOperatable.is_literal(o) for o in n.operands)
                            # A is/ss A
                            or n.operands[0] is n.operands[1]
                        )
                    )
                ]
            out = ""
            node_by_depth = groupby(nodes, key=ParameterOperatable.get_depth)
            for depth, dnodes in sorted(node_by_depth.items(), key=lambda t: t[0]):
                out += f"\n  --Depth {depth}--"
                for n in dnodes:
                    out += f"\n      {n.compact_repr(context)}"

            if not nodes:
                continue
            print_out(f"|Graph {i}|={len(nodes)}/{len(pre_nodes)} [{out}\n]")

    @staticmethod
    def concat_repr_maps(*repr_maps: REPR_MAP) -> REPR_MAP:
        # TODO just removed assert
        if not repr_maps:
            return {}
        if len(repr_maps) == 1:
            return repr_maps[0]

        concatenated = {}
        for original_obj in repr_maps[0].keys():
            chain_end = original_obj
            chain_interrupted = False
            i = 0
            for m in repr_maps:
                # CONSIDER: I think we can assert this
                assert isinstance(chain_end, ParameterOperatable)
                if chain_end not in m:
                    assert (
                        original_obj.get_parent() is None
                    ), "should never remove root parameters"
                    logger.debug(
                        f"chain_end {original_obj} -> {chain_end} interrupted at {i}"
                    )
                    chain_interrupted = True
                    break
                chain_end = m[chain_end]
                i += 1
            if not chain_interrupted:
                concatenated[original_obj] = chain_end
        return concatenated

    class ReprMap:
        def __init__(self, repr_map: REPR_MAP):
            self.repr_map = repr_map

        def try_get_literal(
            self, param: ParameterOperatable, allow_subset: bool = False
        ) -> SolverLiteral | None:
            if param not in self.repr_map:
                return None
            lit = try_extract_literal(self.repr_map[param], allow_subset=allow_subset)
            if lit is None:
                return None
            if isinstance(lit, Quantity_Set):
                fac = quantity(1, HasUnit.get_units(param))
                return lit * fac / fac.to_base_units().m
            return lit

        def __getitem__(self, param: ParameterOperatable) -> SolverLiteral:
            return not_none(self.try_get_literal(param))

        def __contains__(self, param: ParameterOperatable) -> bool:
            return param in self.repr_map

        def __repr__(self) -> str:
            return f"ReprMap({self.repr_map})"

        def __rich_repr__(self):
            yield self.repr_map

    @staticmethod
    def create_concat_repr_map(*repr_maps: REPR_MAP) -> ReprMap:
        return Mutators.ReprMap(Mutators.concat_repr_maps(*repr_maps))
