# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import io
import logging
import sys
from collections import defaultdict
from dataclasses import dataclass
from types import UnionType
from typing import Callable, Iterable, Sequence, cast

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
    All,
    CanonicalOperation,
    SolverAlgorithm,
    SolverLiteral,
    SolverOperatable,
    alias_is_literal,
    find_congruent_expression,
    get_graphs,
    is_alias_is_literal,
    make_if_doesnt_exist,
    make_lit,
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


# TODO use Mutator everywhere instead of repr_maps
class Mutator:
    @dataclass
    class _Transformations:
        mutated: REPR_MAP
        removed: set[ParameterOperatable]
        copied: set[ParameterOperatable]
        created: dict[ParameterOperatable, list[ParameterOperatable]]
        # TODO make api for contraining
        terminated: set[ConstrainableExpression]

    def __init__(
        self,
        *Gs: Graph,
        print_context: ParameterOperatable.ReprContext,
        algo: SolverAlgorithm,
        last_run_operables: set[ParameterOperatable] | None = None,
        repr_map: REPR_MAP | None = None,
    ) -> None:
        self._G: set[Graph] = set(Gs)
        self.print_context = print_context

        if not last_run_operables:
            last_run_operables = set()

        self._last_run_operables = last_run_operables
        self._starting_operables = set(self.nodes_of_type(include_terminated=True))
        self._new_operables = self._starting_operables - self._last_run_operables
        self.transformations = Mutator._Transformations(
            mutated=repr_map or {},
            removed=set(),
            copied=set(),
            created=defaultdict(list),
            terminated=set(),
        )

        # TODO remove debug
        # logger.debug(f"new ops ({algo.name}): {len(self._new_operables)}")
        # for op in self._new_operables:
        #     logger.debug(f"\t{hex(id(op))}| {op.compact_repr(self.print_context)}")

        self.algo = algo

    @property
    def G(self) -> set[Graph]:
        # Handles C++ graph shenanigans on move
        g = self._G
        if all(g.node_count > 0 for g in g):
            return g
        # Handle graph merge
        gs = get_graphs(self._starting_operables)
        self._G = set(gs)
        return self._G

    def has_been_mutated(self, po: ParameterOperatable) -> bool:
        return po in self.transformations.mutated

    def get_mutated(self, po: ParameterOperatable) -> ParameterOperatable:
        return self.transformations.mutated[po]

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

        self.transformations.mutated[po] = new_po
        return new_po

    def _override_repr(self, po: ParameterOperatable, new_po: ParameterOperatable):
        """
        Do not use this if you don't understand the consequences.
        Honestly I don't.
        """
        # TODO not sure this is the best way to handle ghost exprs
        if po in self.transformations.mutated:
            self.transformations.created[self.transformations.mutated[po]] = [po]

        self.transformations.mutated[po] = new_po

    def mutate_parameter(
        self,
        param: Parameter,
        units: Unit | Quantity | None = None,
        domain: Domain | None = None,
        soft_set: Quantity_Interval_Disjoint | Quantity_Interval | None = None,
        within: Quantity_Interval_Disjoint | Quantity_Interval | None = None,
        guess: Quantity | int | float | None = None,
        tolerance_guess: float | None = None,
        likely_constrained: bool | None = None,
        override_within: bool = False,
    ) -> Parameter:
        if param in self.transformations.mutated:
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
            within=within if override_within else param.within,
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
        operands: Iterable[All] | None = None,
        expression_factory: type[Expression] | None = None,
        soft_mutate: type[Is] | type[IsSubset] | None = None,
        ignore_existing: bool = False,
    ) -> CanonicalOperation:
        if expression_factory is None:
            expression_factory = type(expr)

        if operands is None:
            operands = expr.operands

        if expr in self.transformations.mutated:
            out = self.get_mutated(expr)
            assert isinstance(out, CanonicalOperation)
            # TODO more checks
            assert type(out) is expression_factory
            # still need to run soft_mutate even if expr already in repr
            if soft_mutate:
                expr = out
            else:
                return out

        if soft_mutate:
            assert issubclass(expression_factory, CanonicalOperation)
            out = self.create_expression(expression_factory, *operands, from_ops=[expr])
            self.soft_mutate(soft_mutate, expr, out)
            return out

        copy_only = expression_factory is type(expr) and operands == expr.operands
        if not copy_only and not ignore_existing:
            assert issubclass(expression_factory, CanonicalOperation)
            exists = find_congruent_expression(
                expression_factory, *operands, mutator=self
            )
            if exists is not None:
                return self._mutate(expr, self.get_copy(exists))

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
            if self.is_predicate_terminated(expr):
                new_expr._solver_terminated = True

        return self._mutate(expr, new_expr)  # type: ignore #TODO

    # TODO make more use of soft_mutate for alias & ss with non-lit
    def soft_mutate(
        self,
        soft: type[Is] | type[IsSubset],
        old: ParameterOperatable,
        new: ParameterOperatable,
    ):
        # filter A is A, A ss A
        if new is old:
            return
        self.create_expression(soft, old, new, constrain=True, from_ops=[old])

    def mutate_unpack_expression(
        self, expr: Expression, operands: list[ParameterOperatable] | None = None
    ) -> ParameterOperatable:
        """
        '''
        op(A, ...) -> A
        op!(A, ...) -> A!
        '''
        """
        unpacked = expr.operands[0] if operands is None else operands[0]
        if not isinstance(unpacked, ParameterOperatable):
            raise ValueError("Unpacked operand can't be a literal")
        out = self._mutate(expr, self.get_copy(unpacked))
        if isinstance(out, ConstrainableExpression) and out.constrained:
            out.constrain()
        return out

    def mutator_neutralize_expressions(self, expr: Expression) -> ParameterOperatable:
        """
        '''
        op(op_inv(A), ...) -> A
        op!(op_inv(A), ...) -> A!
        '''
        """
        inner_expr = expr.operands[0]
        if not isinstance(inner_expr, Expression):
            raise ValueError("Inner operand must be an expression")
        inner_operand = inner_expr.operands[0]
        if not isinstance(inner_operand, ParameterOperatable):
            raise ValueError("Unpacked operand can't be a literal")
        out = self._mutate(expr, self.get_copy(inner_operand))
        if isinstance(out, ConstrainableExpression) and out.constrained:
            out.constrain()
        return out

    def mutate_expression_with_op_map(
        self,
        expr: Expression,
        operand_mutator: Callable[[int, ParameterOperatable], ParameterOperatable.All],
        expression_factory: type[CanonicalOperation] | None = None,
        ignore_existing: bool = False,
    ) -> CanonicalOperation:
        """
        operand_mutator: Only allowed to return old Graph objects
        """
        return self.mutate_expression(
            expr,
            operands=[operand_mutator(i, op) for i, op in enumerate(expr.operands)],
            expression_factory=expression_factory,
            ignore_existing=ignore_existing,
        )

    def get_copy(self, obj: ParameterOperatable.All) -> ParameterOperatable.All:
        if not isinstance(obj, ParameterOperatable):
            return obj

        if self.has_been_mutated(obj):
            return self.get_mutated(obj)

        # purely for debug
        self.transformations.copied.add(obj)

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
        from_ops: Sequence[ParameterOperatable] | None = None,
        constrain: bool = False,
    ) -> T:
        assert issubclass(expr_factory, CanonicalOperation)

        existed = False
        if check_exists:
            expr, existed = make_if_doesnt_exist(expr_factory, *operands, mutator=self)
        else:
            expr = expr_factory(*operands)  # type: ignore
        if not existed:
            self.transformations.created[expr] = list(from_ops or [])
        if constrain and isinstance(expr, ConstrainableExpression):
            self.constrain(expr)
        return expr

    def remove(self, *po: ParameterOperatable):
        assert not any(
            p in self.transformations.mutated for p in po
        ), "Object already in repr_map"
        root_pos = [p for p in po if p.get_parent() is not None]
        assert not root_pos, f"should never remove root parameters: {root_pos}"
        self.transformations.removed.update(po)

    def remove_graph(self, g: Graph):
        # TODO implementing graph removal has to be more explicit
        # e.g mark as no more use, and then future mutators ignore it for the algos
        # for now at least remove expressions
        assert g in self.G
        self.remove(*GraphFunctions(g).nodes_of_type(Expression))

    def is_removed(self, po: ParameterOperatable) -> bool:
        return po in self.transformations.removed

    def _copy_unmutated(
        self,
        exclude_filter: Callable[[ParameterOperatable], bool] | None = None,
    ):
        # TODO: for graph that need no copy, just do {po: po}

        if exclude_filter is None:
            exclude_filter = self.is_removed

        _touched_graphs = self._touched_graphs

        # TODO might not need to sort
        other_param_op = ParameterOperatable.sort_by_depth(
            (
                p
                for G in self.G
                if G in _touched_graphs
                for p in GraphFunctions(G).nodes_of_type(ParameterOperatable)
                if not self.has_been_mutated(p) and not exclude_filter(p)
            ),
            ascending=True,
        )
        for o in other_param_op:
            self.get_copy(o)

        # optimization: if just new_ops, no need to copy
        # pass through untouched graphs
        for g in self.G - _touched_graphs:
            for p in GraphFunctions(g).nodes_of_type(ParameterOperatable):
                self.transformations.mutated[p] = p

    def register_created_parameter(
        self, param: Parameter, from_ops: Sequence[ParameterOperatable] | None = None
    ) -> Parameter:
        self.transformations.created[param] = list(from_ops or [])
        return param

    def constrain(self, *po: ConstrainableExpression, terminate: bool = False):
        for p in po:
            p.constrain()
            alias_is_literal(p, True, self, terminate=terminate)

    @property
    def dirty(self) -> bool:
        non_no_op_mutations = any(
            k is not v for k, v in self.transformations.mutated.items()
        )

        return bool(
            self.transformations.removed
            or non_no_op_mutations
            or self.transformations.created
            or self.transformations.terminated
        )

    @property
    def _touched_graphs(self) -> set[Graph]:
        return {
            n.get_graph()
            for n in self.transformations.removed | self.transformations.mutated.keys()
        }

    def check_no_illegal_mutations(self):
        # TODO should only run during dev

        # Check modifications to original graph
        post_mut_nodes = set(self.nodes_of_type(include_terminated=True))
        removed = self._starting_operables.difference(
            post_mut_nodes, self.transformations.removed
        )
        added = post_mut_nodes.difference(
            self._starting_operables, self.transformations.created
        )
        removed_compact = [op.compact_repr(self.print_context) for op in removed]
        added_compact = [op.compact_repr(self.print_context) for op in added]
        assert not removed, (
            f"Mutator {self.G, self.algo.name} untracked removed "
            f"{indented_container(removed_compact)}"
        )
        assert not added, (
            f"Mutator {self.G, self.algo.name} untracked added "
            f"{indented_container(added_compact)}"
        )

        # don't need to check original graph, done above seperately
        all_new_graphs = get_graphs(self.transformations.mutated.values())
        all_new_params = {
            op
            for g in all_new_graphs
            for op in GraphFunctions(g).nodes_of_type(ParameterOperatable)
        }
        non_registered = all_new_params.difference(
            self.transformations.created, self.transformations.mutated.values()
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

    def close(self) -> AlgoResult:
        result = AlgoResult(
            repr_map={},
            graphs=[],
            dirty=self.dirty,
        )

        if result.dirty:
            touched = self._touched_graphs
            self.check_no_illegal_mutations()
            self._copy_unmutated()

            result.repr_map = self.transformations.mutated
            result.graphs = get_graphs(result.repr_map.values())

            # Check if original graphs ended up in result
            # allowed if no copy was needed for graph
            assert not (touched & set(result.graphs))

        return result

    def predicate_terminate(self, pred: ConstrainableExpression):
        assert pred.constrained
        if pred._solver_terminated:
            return
        pred._solver_terminated = True
        self.transformations.terminated.add(pred)

    def is_predicate_terminated(self, pred: ConstrainableExpression) -> bool:
        return pred._solver_terminated

    def predicate_reset_termination(self, pred: ConstrainableExpression):
        assert pred.constrained
        if not pred._solver_terminated:
            return
        pred._solver_terminated = False

    def get_output_operables(self) -> set[ParameterOperatable]:
        # It's enough to check for mutation graphs and not created ones
        # because the created ones always connect to graphs of the mutated ones
        # else they will be lost anyway
        if not self.dirty:
            return self._starting_operables

        return {
            op
            for g in get_graphs(self.transformations.mutated.values())
            for op in GraphFunctions(g).nodes_of_type(ParameterOperatable)
        }

    def nodes_of_type[T: "ParameterOperatable"](
        self,
        t: type[T] = ParameterOperatable,
        sort_by_depth: bool = False,
        created_only: bool = False,
        new_only: bool = False,
        include_terminated: bool = False,
    ) -> list[T] | set[T]:
        assert not new_only or not created_only

        if new_only:
            out = {n for n in self._new_operables if isinstance(n, t)}
        elif created_only:
            out = {n for n in self.transformations.created if isinstance(n, t)}
        else:
            out = {n for G in self.G for n in GraphFunctions(G).nodes_of_type(t)}

        if not include_terminated:
            out = {
                n
                for n in out
                if not (
                    isinstance(n, ConstrainableExpression)
                    and self.is_predicate_terminated(n)
                )
            }

        if sort_by_depth:
            out = ParameterOperatable.sort_by_depth(out, ascending=True)

        return out

    def nodes_of_types(
        self,
        t: tuple[type[ParameterOperatable], ...] | UnionType,
        sort_by_depth: bool = False,
        include_terminated: bool = False,
    ) -> list[ParameterOperatable] | set[ParameterOperatable]:
        out = {n for G in self._G for n in GraphFunctions(G).nodes_of_types(t)}
        out = cast(set[ParameterOperatable], out)
        if not include_terminated:
            out = {
                n
                for n in out
                if not (
                    isinstance(n, ConstrainableExpression)
                    and self.is_predicate_terminated(n)
                )
            }
        if sort_by_depth:
            out = ParameterOperatable.sort_by_depth(out, ascending=True)
        return out

    def get_literal_aliases(self, new_only: bool = True):
        """
        Find new ops which are Is expressions between a ParameterOperatable and a
        literal
        """

        return (
            expr
            for expr in self.nodes_of_type(
                Is, new_only=new_only, include_terminated=True
            )
            if is_alias_is_literal(expr)
        )

    def get_literal_subsets(self, new_only: bool = True):
        new_literal_ss = (
            expr
            for expr in self.nodes_of_type(
                IsSubset, new_only=new_only, include_terminated=True
            )
            if bool(
                expr.constrained
                and expr.get_literal_operands()
                and expr.operatable_operands
                # match A ⊆!!✓ ([5, 20]) but not ([5, 20]) ⊆!!✓ A
                and isinstance(expr.operands[0], ParameterOperatable)
            )
        )

        return {
            p: not_none(try_extract_literal(p, allow_subset=True))
            for alias in new_literal_ss
            for p in alias.operatable_operands
        }

    def get_literal_aliased(self, new_only: bool = True):
        ps = {
            p: not_none(try_extract_literal(p))
            for alias in self.get_literal_aliases(new_only=new_only)
            for p in alias.operatable_operands
        }
        return ps

    def run(self):
        self.algo(self)

    @once
    def get_new_print_context(self) -> ParameterOperatable.ReprContext:
        context_old = self.print_context

        context_new = ParameterOperatable.ReprContext()
        context_new.variable_mapping.next_id = context_old.variable_mapping.next_id

        for s, d in self.transformations.mutated.items():
            if isinstance(s, Parameter) and isinstance(d, Parameter):
                s.compact_repr(context_old)
                s_mapping = context_old.variable_mapping.mapping[s]
                d_mapping = context_new.variable_mapping.mapping.get(d, None)
                if d_mapping is None or d_mapping > s_mapping:
                    context_new.variable_mapping.mapping[d] = s_mapping

        return context_new

    def debug_print(self):
        if not self.transformations.mutated:
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
        table.add_column("Before/Created By")
        table.add_column("After")

        graphs = get_graphs(self.transformations.mutated.values())

        created_ops = self.transformations.created

        rows: list[tuple[str, str]] = []

        for op, from_ops in created_ops.items():
            key = "new"
            key_from_ops = ", ".join(o.compact_repr(context_old) for o in from_ops)
            value = op.compact_repr(context_new)
            if is_alias_is_literal(op):
                expr = next(iter(op.operatable_operands))
                lit = next(iter(op.get_literal_operands().values()))
                if isinstance(expr, ConstrainableExpression):
                    key = (
                        "proven"
                        if try_extract_literal(expr) == make_lit(True)
                        else "disproven"
                    )
                else:
                    key = f"new_alias: {lit}"
            if key_from_ops:
                key = f"{key} from ({key_from_ops})"
            rows.append((key, value))

        terminated = self.transformations.terminated.difference(created_ops)
        for op in terminated:
            rows.append(("terminated", op.compact_repr(context_new)))

        copied = self.transformations.copied
        printed = set()

        for s, d in self.transformations.mutated.items():
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
            printed.add(s)
            rows.append((old, new))

        merged = groupby(self.transformations.mutated.items(), key=lambda t: t[1])
        non_single_merge = {k: v for k, v in merged.items() if len(v) > 1}
        for d, sds in non_single_merge.items():
            for s, _ in sds:
                if s is d:
                    continue
                if s in printed:
                    continue
                old = s.compact_repr(context_old)
                new = d.compact_repr(context_new)
                # already printed above
                if old != new:
                    continue
                if VERBOSE_TABLE:
                    old += "\n\n" + repr(s)
                rows.append((old, "merged"))

        for s in self.transformations.removed:
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
        if len(graphs) != len(self._G):
            logger.debug(
                f"Mutators created/destroyed graphs: "
                f"{len(self._G)} -> {len(graphs)}"
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
                        and n._solver_terminated
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
            for i, m in enumerate(repr_maps):
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
        return Mutator.ReprMap(Mutator.concat_repr_maps(*repr_maps))

    def __repr__(self) -> str:
        old_context = self.print_context
        new_context = self.get_new_print_context()
        mutated_transformations = [
            (k.compact_repr(old_context), v.compact_repr(new_context))
            for k, v in self.transformations.mutated.items()
        ]
        mutated = indented_container(
            [f"{k} -> {v}" for k, v in mutated_transformations if k != v]
            + [f"copy {k}" for k, v in mutated_transformations if k == v]
        )
        created = indented_container(
            [k.compact_repr(new_context) for k in self.transformations.created]
        )
        removed = indented_container(
            [k.compact_repr(old_context) for k in self.transformations.removed]
        )
        # copied = indented_container(
        #    [k.compact_repr(old_context) for k in self.transformations.copied]
        # )
        copied = len(self.transformations.copied)
        terminated = len(self.transformations.terminated)
        return (
            f"Mutator(mutated={mutated}, created={created},"
            f" removed={removed}, copied={copied}, terminated={terminated})"
        )
