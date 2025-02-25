# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import io
import logging
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import chain
from types import UnionType
from typing import Any, Callable, Iterable, Sequence, cast

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
    CanonicalExpression,
    ContradictionByLiteral,
    SolverAlgorithm,
    SolverAll,
    SolverAllExtended,
    SolverLiteral,
    alias_is_literal,
    find_congruent_expression,
    get_aliases,
    get_graphs,
    get_lit_mapping_from_lit_expr,
    get_supersets,
    is_alias_is_literal,
    is_subset_literal,
    try_extract_literal,
)
from faebryk.libs.exceptions import downgrade
from faebryk.libs.logging import TERMINAL_WIDTH
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval,
    Quantity_Interval_Disjoint,
    Quantity_Set,
)
from faebryk.libs.sets.sets import P_Set
from faebryk.libs.units import HasUnit, Quantity, Unit, quantity
from faebryk.libs.util import (
    cast_assert,
    groupby,
    indented_container,
    not_none,
    once,
)

logger = logging.getLogger(__name__)

type REPR_MAP = dict[ParameterOperatable, ParameterOperatable]

if S_LOG:
    logger.setLevel(logging.DEBUG)


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
        soft_replaced: dict[ParameterOperatable, ParameterOperatable]

    def __init__(
        self,
        *Gs: Graph,
        print_context: ParameterOperatable.ReprContext,
        algo: SolverAlgorithm,
        terminal: bool,
        iteration_repr_map: REPR_MAP | None = None,
        repr_map: REPR_MAP | None = None,
    ) -> None:
        self._G: set[Graph] = set(Gs)
        self.print_context = print_context
        self.terminal = terminal

        if not iteration_repr_map:
            iteration_repr_map = {}

        self._starting_operables = set(self.nodes_of_type(include_terminated=True))

        self._last_run_repr_map = iteration_repr_map
        self._last_run_operables = set(iteration_repr_map.values())
        self._new_operables = self._starting_operables - self._last_run_operables
        self._merged_since_last_run = {
            new_v: [old_k for old_k, _ in kvs]
            for new_v, kvs in groupby(
                iteration_repr_map.items(), key=lambda t: t[1], only_multi=True
            ).items()
        }

        self.transformations = Mutator._Transformations(
            mutated=repr_map or {},
            removed=set(),
            copied=set(),
            created=defaultdict(list),
            terminated=set(),
            soft_replaced=dict(),
        )

        self.algo = algo

    @property
    @once
    def mutated_since_last_run(self) -> set[CanonicalExpression]:
        # TODO make faster, compact repr is a pretty bad one
        # consider congruence instead, but be careful since not in same graph space
        out = {
            v
            for k, v in self._last_run_repr_map.items()
            if isinstance(v, CanonicalExpression)
            and isinstance(k, Expression)
            and k is not v
            and k.compact_repr() != v.compact_repr()
            # ignore merged (since those always act mutated)
            # but accept if all merged got mutated
            and (
                v not in self._merged_since_last_run
                or all(
                    km.compact_repr() != v.compact_repr()
                    for km in self._merged_since_last_run[v]
                )
            )
        }
        return out

    @property
    def G(self) -> set[Graph]:
        # Handles C++ graph shenanigans on move
        gs = self._G
        if all(g.node_count > 0 for g in gs):
            return gs
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

    def _create_expression[T: Expression](
        self,
        expr_factory: type[T],
        *operands: SolverAllExtended,
        non_operands: Any = None,
        constrain: bool = False,
    ) -> T:
        new_operands = [
            self.get_copy(
                op,
                accept_soft=not (expr_factory in [Is, IsSubset] and constrain),
            )
            for op in operands
        ]
        new_expr = expr_factory(*new_operands)
        new_expr.non_operands = non_operands

        if constrain and isinstance(new_expr, ConstrainableExpression):
            new_expr.constrained = True
            # TODO this is better, but ends up in inf loop
            # self.constrain(new_expr)

        for op in new_operands:
            if isinstance(op, ParameterOperatable):
                assert (
                    op.get_graph() == new_expr.get_graph()
                ), f"Graph mismatch: {op.get_graph()} != {new_expr.get_graph()}"

        return new_expr

    def mutate_expression(
        self,
        expr: Expression,
        operands: Iterable[SolverAllExtended] | None = None,
        expression_factory: type[Expression] | None = None,
        soft_mutate: type[Is] | type[IsSubset] | None = None,
        ignore_existing: bool = False,
    ) -> CanonicalExpression:
        if expression_factory is None:
            expression_factory = type(expr)

        if operands is None:
            operands = expr.operands

        if expr in self.transformations.mutated:
            out = self.get_mutated(expr)
            assert isinstance(out, CanonicalExpression)
            # TODO more checks
            assert type(out) is expression_factory
            # still need to run soft_mutate even if expr already in repr
            if soft_mutate:
                expr = out
            else:
                return out

        if soft_mutate:
            assert issubclass(expression_factory, CanonicalExpression)
            return self.soft_mutate_expr(
                expression_factory, expr, operands, soft_mutate
            )

        copy_only = expression_factory is type(expr) and operands == expr.operands
        if not copy_only and not ignore_existing:
            assert issubclass(expression_factory, CanonicalExpression)
            exists = find_congruent_expression(
                expression_factory, *operands, mutator=self, allow_uncorrelated=False
            )
            if exists is not None:
                return self._mutate(expr, self.get_copy(exists))

        constrain = isinstance(expr, ConstrainableExpression) and expr.constrained
        new_expr = self._create_expression(
            expression_factory,
            *operands,
            non_operands=expr.non_operands,
            constrain=constrain,
        )

        if isinstance(expr, ConstrainableExpression):
            new_expr = cast_assert(ConstrainableExpression, new_expr)
            if self.is_predicate_terminated(expr):
                new_expr._solver_terminated = True

        return self._mutate(expr, new_expr)  # type: ignore #TODO

    def soft_replace[T: ParameterOperatable](
        self,
        current: T,
        new: ParameterOperatable,
    ) -> T:
        if self.has_been_mutated(current):
            copy = self.get_mutated(current)
            exps = copy.get_operations()  # noqa: F841
            # FIXME: reenable, but alias classes need to take this into account
            # assert all(isinstance(o, (Is, IsSubset)) and o.constrained for o in exps)

        self.transformations.soft_replaced[current] = new
        return self.get_copy(current, accept_soft=False)  # type: ignore

    def soft_mutate_expr(
        self,
        expression_factory: type[CanonicalExpression],
        expr: Expression,
        operands: Iterable[SolverAllExtended],
        soft: type[Is] | type[IsSubset],
    ) -> CanonicalExpression:
        operands = list(operands)
        # Don't create A is A, lit is lit
        if expr.is_congruent_to_factory(
            expression_factory, operands, allow_uncorrelated=True
        ):
            return expr  # type: ignore

        # Avoid alias X to Op1(lit) if X is!! Op2(lit)
        congruent = {
            alias
            for alias in (get_aliases(expr) if soft is Is else get_supersets(expr))
            if isinstance(alias, expression_factory)
            and alias.is_congruent_to_factory(
                expression_factory, operands, allow_uncorrelated=True
            )
        }
        if congruent:
            return next(iter(congruent))

        out = self.create_expression(
            expression_factory,
            *operands,
            from_ops=[expr],
            allow_uncorrelated=soft is IsSubset,
        )
        self.soft_mutate(soft, expr, out)
        return out

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
        self.create_expression(
            soft,
            old,
            new,
            constrain=True,
            from_ops=[old],
            # FIXME
            allow_uncorrelated=True,
        )

    def mutate_unpack_expression(
        self, expr: Expression, operands: list[ParameterOperatable] | None = None
    ) -> ParameterOperatable:
        """
        ```
        op(A, ...) -> A
        op!(A, ...) -> A!
        ```
        """
        unpacked = expr.operands[0] if operands is None else operands[0]
        if not isinstance(unpacked, ParameterOperatable):
            raise ValueError("Unpacked operand can't be a literal")
        out = self._mutate(expr, self.get_copy(unpacked))
        if isinstance(expr, ConstrainableExpression) and expr.constrained:
            assert isinstance(out, ConstrainableExpression)
            self.constrain(out)
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
            self.constrain(out)
        return out

    def mutate_expression_with_op_map(
        self,
        expr: Expression,
        operand_mutator: Callable[[int, ParameterOperatable], ParameterOperatable.All],
        expression_factory: type[CanonicalExpression] | None = None,
        ignore_existing: bool = False,
    ) -> CanonicalExpression:
        """
        operand_mutator: Only allowed to return old Graph objects
        """
        return self.mutate_expression(
            expr,
            operands=[operand_mutator(i, op) for i, op in enumerate(expr.operands)],
            expression_factory=expression_factory,
            ignore_existing=ignore_existing,
        )

    def get_copy(
        self, obj: ParameterOperatable.All, accept_soft: bool = True
    ) -> ParameterOperatable.All:
        if not isinstance(obj, ParameterOperatable):
            return obj

        if accept_soft and obj in self.transformations.soft_replaced:
            return self.transformations.soft_replaced[obj]

        if self.has_been_mutated(obj):
            return self.get_mutated(obj)

        # TODO: not sure if ok
        # if obj is new, no need to copy
        # TODO add guard to _mutate to not let new stuff be mutated
        if (
            obj in self.transformations.created
            or obj in self.transformations.mutated.values()
        ):
            return obj

        # purely for debug
        self.transformations.copied.add(obj)

        if isinstance(obj, Expression):
            return self.mutate_expression(obj)
        elif isinstance(obj, Parameter):
            return self.mutate_parameter(obj)

        assert False

    def create_expression[T: CanonicalExpression](
        self,
        expr_factory: type[T],
        *operands: SolverAll,
        check_exists: bool = True,
        from_ops: Sequence[ParameterOperatable] | None = None,
        constrain: bool = False,
        allow_uncorrelated: bool = False,
    ) -> T:
        assert issubclass(expr_factory, CanonicalExpression)

        expr = None
        if check_exists:
            # TODO look in old & new graph
            expr = find_congruent_expression(
                expr_factory,
                *operands,
                mutator=self,
                allow_uncorrelated=allow_uncorrelated,
            )

        if expr is None:
            expr = self._create_expression(
                expr_factory,
                *operands,
                constrain=constrain,
            )
            self.transformations.created[expr] = list(from_ops or [])

        # TODO double constrain ugly
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
            k is not v
            for k, v in self.transformations.mutated.items()
            if k not in self.transformations.copied
        )

        return bool(
            self.transformations.removed
            or non_no_op_mutations
            or self.transformations.created
            or self.transformations.terminated
        )

    @property
    def _touched_graphs(self) -> set[Graph]:
        """
        Return graphs that require a copy in some form
        - if a mutation happened we need to copy the whole graph to replace
         the old node with the new one
        - if a node was removed, we need to copy the graph to remove it
        """
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
            touched_pre_copy = self._touched_graphs
            self.check_no_illegal_mutations()
            self._copy_unmutated()

            result.repr_map = self.transformations.mutated
            result.graphs = self.get_graphs()

            # Check if original graphs ended up in result
            # allowed if no copy was needed for graph
            assert not (touched_pre_copy & set(result.graphs))

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

    def get_graphs(self) -> list[Graph]:
        return get_graphs(
            chain(
                self.transformations.mutated.values(),
                self.transformations.created,
            )
        )

    def get_output_operables(self) -> set[ParameterOperatable]:
        # It's enough to check for mutation graphs and not created ones
        # because the created ones always connect to graphs of the mutated ones
        # else they will be lost anyway
        if not self.dirty:
            return self._starting_operables

        return {
            op
            for g in self.get_graphs()
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
            out = GraphFunctions(*self.G).nodes_of_type(t)

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
        out = GraphFunctions(*self.G).nodes_of_types(t)
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

        aliases: set[CanonicalExpression]
        aliases = set(
            self.nodes_of_type(Is, new_only=new_only, include_terminated=True)
        )

        if new_only:
            # Taking into account if op with no literal merged into a op with literal
            for new, olds in self._merged_since_last_run.items():
                new_lit = try_extract_literal(new)
                if new_lit is None:
                    continue
                old_lits = {try_extract_literal(o) for o in olds}
                if old_lits == {new_lit}:
                    continue
                aliases.update(new.get_operations(Is, constrained_only=True))
            aliases.update(self.mutated_since_last_run)

        return (expr for expr in aliases if is_alias_is_literal(expr))

    def _get_literal_subsets(self, new_only: bool = True):
        subsets: set[CanonicalExpression]
        subsets = set(
            self.nodes_of_type(IsSubset, new_only=new_only, include_terminated=True)
        )

        if new_only:
            # Taking into account if op with no literal merged into a op with literal
            for new, olds in self._merged_since_last_run.items():
                new_lit = try_extract_literal(new, allow_subset=True)
                if new_lit is None:
                    continue
                old_lits = {try_extract_literal(o, allow_subset=True) for o in olds}
                if old_lits == {new_lit}:
                    continue
                subsets.update(new.get_operations(IsSubset, constrained_only=True))
            subsets.update(self.mutated_since_last_run)

        return (expr for expr in subsets if is_subset_literal(expr))

    def get_literal_mappings(self, new_only: bool = True, allow_subset: bool = False):
        # TODO better exceptions

        ops = self.get_literal_aliases(new_only=new_only)
        mapping = [get_lit_mapping_from_lit_expr(op) for op in ops]
        if not len({k for k, _ in mapping}) == len(mapping):
            raise ContradictionByLiteral("Literal contradictions", [], [])
        mapping_dict = dict(mapping)

        if allow_subset:
            ops_ss = self._get_literal_subsets(new_only=new_only)
            mapping_ss = [get_lit_mapping_from_lit_expr(op) for op in ops_ss]
            grouped_ss = groupby(mapping_ss, key=lambda t: t[0])
            for k, v in grouped_ss.items():
                merged_ss = P_Set.intersect_all(*(ss_lit for _, ss_lit in v))
                if merged_ss.is_empty():
                    raise ContradictionByLiteral("Empty intersection", [], [])
                if k in mapping_dict:
                    if not mapping_dict[k].is_subset_of(merged_ss):  # type: ignore
                        raise ContradictionByLiteral(
                            "ss lit doesn't match is_lit", [], []
                        )
                    continue
                mapping_dict[k] = merged_ss

        return mapping_dict

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

        graphs = get_graphs(self.transformations.mutated.values())

        created_ops = self.transformations.created

        rows: list[tuple[str, str]] = []

        for op, from_ops in created_ops.items():
            key = "new"
            key_from_ops = " \n  ".join(o.compact_repr(context_old) for o in from_ops)
            key_from_ops = f"  {key_from_ops}"
            value = op.compact_repr(context_new)
            if is_alias_is_literal(op) or is_subset_literal(op):
                expr = next(iter(op.operatable_operands))
                lit = next(iter(op.get_literal_operands().values()))
                if not SHOW_SS_IS and expr in created_ops:
                    continue
                alias_type = "alias" if isinstance(op, Is) else "subset"
                key = f"new_{alias_type}\n{lit}"
                value = expr.compact_repr(context_new)
            if key_from_ops:
                key = f"{key} from\n{key_from_ops}"
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
            if (
                isinstance(s, ConstrainableExpression)
                and new.replace("✓", "") == old.replace("✓", "")
                and try_extract_literal(d) != try_extract_literal(s)
                and new.count("✓") == old.count("✓") + 1
            ):
                # done by proven/disproven
                # TODO disproven
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
            rows_unique = Counter(rows)
            rows_sorted = sorted(rows_unique.items(), key=lambda t: t[0])
            table = Table(
                title="Mutations",
                show_lines=True,
            )
            track_count = any(c > 1 for c in rows_unique.values())
            if track_count:
                table.add_column("x")
            table.add_column("Before/Created By")
            table.add_column("After")
            for row, count in rows_sorted:
                count_str = "" if count == 1 else f"{count}x"
                if track_count:
                    table.add_row(count_str, *row)
                else:
                    table.add_row(*row)

            console = Console(
                record=True,
                file=io.StringIO(),
                width=int(TERMINAL_WIDTH) - 40,
            )
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
                    if not (is_alias_is_literal(n) or is_subset_literal(n))
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
        def __init__(
            self, repr_map: REPR_MAP, removed: set[ParameterOperatable] | None = None
        ):
            self.repr_map = repr_map
            self.removed = removed or set()

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

        def is_removed(self, param: ParameterOperatable) -> bool:
            return param in self.removed

        def __getitem__(self, param: ParameterOperatable) -> SolverLiteral:
            return not_none(self.try_get_literal(param))

        def __contains__(self, param: ParameterOperatable) -> bool:
            return param in self.repr_map

        def __repr__(self) -> str:
            return f"ReprMap({self.repr_map})"

        def __rich_repr__(self):
            yield self.repr_map

        @staticmethod
        def create_from_graphs(*graphs: Graph) -> "Mutator.ReprMap":
            repr_map = {
                po: po
                for g in graphs
                for po in GraphFunctions(g).nodes_of_type(ParameterOperatable)
            }
            return Mutator.ReprMap(repr_map)

    @staticmethod
    def create_concat_repr_map(*repr_maps: REPR_MAP) -> ReprMap:
        concatenated = Mutator.concat_repr_maps(*repr_maps)
        removed = repr_maps[0].keys() - concatenated.keys()
        return Mutator.ReprMap(concatenated, removed)

    def __repr__(self) -> str:
        old_context = self.print_context
        new_context = self.get_new_print_context()
        mutated_transformations = [
            (k.compact_repr(old_context), v.compact_repr(new_context))
            for k, v in self.transformations.mutated.items()
            if k not in self.transformations.copied
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
            f"Mutator('{self.algo.name}', mutated={mutated}, created={created},"
            f" removed={removed}, copied={copied}, terminated={terminated})"
        )
