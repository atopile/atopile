# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import inspect
import logging
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Iterable,
    NamedTuple,
    Sequence,
    cast,
    overload,
)

from more_itertools import first
from rich.table import Table
from rich.tree import Tree

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.algorithm import SolverAlgorithm
from faebryk.core.solver.utils import (
    S_LOG,
    SHOW_SS_IS,
    VERBOSE_TABLE,
    MutatorUtils,
    pretty_expr,
)
from faebryk.libs.logging import rich_to_string
from faebryk.libs.util import (
    OrderedSet,
    duplicates,
    groupby,
    indented_container,
    invert_dict,
    not_none,
    once,
)

if TYPE_CHECKING:
    from faebryk.core.solver.symbolic.invariants import InsertExpressionResult

logger = logging.getLogger(__name__)
if S_LOG:
    logger.setLevel(logging.DEBUG)


Is = F.Expressions.Is
IsSubset = F.Expressions.IsSubset


class is_terminated(fabll.Node):
    """
    Mark expression as terminated.
    Tells algorithms to not further transform the expression.
    Useful for when we already folded it maximally and want to stop processing it.
    """

    is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()


class is_irrelevant(fabll.Node):
    """
    Marks op as irrelevant for solving.
    - mutator hides it from queries
    - gets removed at end of iterations

    Used for removing subsumed, but mutated expressions.
    Can also be used for other stuff in the future.
    TODO: implement in mutator
    """

    is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()


@dataclass
class Transformations:
    print_ctx: F.Parameters.ReprContext

    mutated: dict[
        F.Parameters.is_parameter_operatable, F.Parameters.is_parameter_operatable
    ] = field(default_factory=dict)
    removed: OrderedSet[F.Parameters.is_parameter_operatable] = field(
        default_factory=OrderedSet[F.Parameters.is_parameter_operatable]
    )
    copied: OrderedSet[F.Parameters.is_parameter_operatable] = field(
        default_factory=OrderedSet[F.Parameters.is_parameter_operatable]
    )
    created: dict[
        F.Parameters.is_parameter_operatable,
        list[F.Parameters.is_parameter_operatable],
    ] = field(default_factory=lambda: defaultdict(list))
    # TODO make api for contraining
    terminated: OrderedSet[F.Expressions.is_expression] = field(
        default_factory=OrderedSet[F.Expressions.is_expression]
    )
    asserted: OrderedSet[F.Expressions.is_assertable] = field(
        default_factory=OrderedSet[F.Expressions.is_assertable]
    )
    soft_replaced: dict[
        F.Parameters.is_parameter_operatable, F.Parameters.is_parameter_operatable
    ] = field(default_factory=dict)

    @property
    def dirty(self) -> bool:
        non_no_op_mutations = any(
            not k.is_same(v) for k, v in self.mutated.items() if k not in self.copied
        )

        return bool(
            self.removed
            or non_no_op_mutations
            or self.created
            or self.terminated
            or self.asserted
        )

    @property
    def is_identity(self) -> bool:
        return (
            not self.removed
            and all(k is v for k, v in self.mutated.items())
            and not self.created
            and not self.terminated
        )

    @staticmethod
    def identity(
        tg: fbrk.TypeGraph,
        g: graph.GraphView,
        input_print_context: F.Parameters.ReprContext,
    ) -> "Transformations":
        return Transformations(
            mutated={
                po: po
                for po in fabll.Traits.get_implementors(
                    trait=F.Parameters.is_parameter_operatable.bind_typegraph(tg),
                    g=g,
                )
            },
            print_ctx=input_print_context,
        )

    def __str__(self) -> str:
        if not self.dirty:
            return "Transformations()"
        assert self.print_ctx

        ctx = self.print_ctx

        mutated_transformations = [
            (k.compact_repr(ctx), v.compact_repr(ctx))
            for k, v in self.mutated.items()
            if k not in self.copied
        ]
        mutated = indented_container(
            [f"{k} -> {v}" for k, v in mutated_transformations if k != v]
            + [f"copy {k}" for k, v in mutated_transformations if k == v]
        )
        created = indented_container([k.compact_repr(ctx) for k in self.created])
        removed = indented_container([k.compact_repr(ctx) for k in self.removed])
        # copied = indented_container(
        #    [k.compact_repr(old_context) for k in self.transformations.copied]
        # )
        copied = len(self.copied)
        terminated = len(self.terminated)
        return (
            f"mutated={mutated}"
            f", created={created}"
            f", removed={removed}"
            f", copied={copied}"
            f", terminated={terminated}"
        )

    def get_new_predicates(
        self, op: F.Parameters.is_parameter_operatable
    ) -> list[F.Expressions.is_predicate]:
        # TODO could still happen, but then we have clash
        # keep this in mind for future
        if self.is_identity:
            return []
        if op not in self.copied:
            return []
        target = self.mutated[op]
        out = list[F.Expressions.is_predicate]()
        for e in self.created:
            if not (e_co := e.try_get_sibling_trait(F.Expressions.is_predicate)):
                continue
            if (expr := e.as_expression.try_get()) is not None and (
                target in expr.get_operand_operatables()
            ):
                out.append(e_co)
        return out


@dataclass
class Traceback:
    class Type(Enum):
        NOOP = auto()
        PASSTHROUGH = auto()
        COPIED = auto()
        CREATED = auto()
        SOFT_REPLACED = auto()
        MERGED = auto()
        MUTATED = auto()
        CONSTRAINED = auto()

    @dataclass(repr=False)
    class Stage:
        srcs: Sequence[F.Parameters.is_parameter_operatable]
        dst: F.Parameters.is_parameter_operatable
        algo: str
        reason: "Traceback.Type"
        ctx: F.Parameters.ReprContext
        related: list["Traceback.Stage"]

        def __repr__(self) -> str:
            return f"{self.reason.name} {self.algo}"

    stage: Stage
    back: "list[Traceback]" = field(default_factory=list)

    def visit(self, visitor: Callable[["Traceback", int], bool]) -> None:
        """
        Visit all nodes in the traceback tree in a depth-first manner without recursion.

        Args:
            visitor: A function that takes a Traceback node and depth as arguments.
                    Returns True to continue traversal into children, False to skip.
        """
        # Stack contains tuples of (node, depth)
        stack: list[tuple[Traceback, int]] = [(self, 0)]

        while stack:
            current, depth = stack.pop()

            # Visit the current node
            continue_traversal = visitor(current, depth)

            # If visitor returns True and there are children, add them to the stack
            if continue_traversal and current.back:
                # Add children in reverse order to maintain DFS left-to-right traversal
                for child in reversed(current.back):
                    stack.append((child, depth + 1))

    def filtered(self) -> "Traceback":
        """
        NOOP & PASSTHROUGH stages always have exactly one source
            (which is the destination)
        This function returns a new traceback with all NOOP & PASSTHROUGH stages removed
        Root is always kept.
        ```
        CREATED
         NOOP
          COPIED
        ```
        becomes
        ```
        CREATED
         COPIED
        ```
        """

        # Create a mapping of original nodes to their filtered counterparts
        node_map: dict[int, Traceback] = {}

        # Create a new root traceback with the same stage as the original
        result = Traceback(stage=self.stage)
        node_map[id(self)] = result

        # Stack for DFS traversal: (original_node, filtered_parent)
        stack: list[tuple[Traceback, Traceback]] = []

        # Initialize stack with children of root
        for child in self.back:
            stack.append((child, result))

        while stack:
            original, filtered_parent = stack.pop()

            if original.stage.reason in {
                Traceback.Type.NOOP,
                Traceback.Type.PASSTHROUGH,
                Traceback.Type.COPIED,
            }:
                # For NOOP stages, skip this node but process its children
                for grandchild in original.back:
                    stack.append((grandchild, filtered_parent))
            else:
                # For non-NOOP stages, create a filtered node
                filtered_node = Traceback(stage=original.stage)
                filtered_parent.back.append(filtered_node)
                node_map[id(original)] = filtered_node

                # Process children of this node
                for child in original.back:
                    stack.append((child, filtered_node))

        return result

    def get_leaves(self) -> list[F.Parameters.is_parameter_operatable]:
        leaves = []

        def _collect_leaves(node, depth):
            if not node.back:
                leaves.extend(node.stage.srcs)
            return True

        self.visit(_collect_leaves)
        return leaves

    def __repr__(self) -> str:
        # TODO
        return f"Traceback({id(self):04x}) {self.stage}"

    def as_rich_tree(
        self, visited: set[F.Parameters.is_parameter_operatable] | None = None
    ) -> Tree:
        from rich.text import Text

        if visited is None:
            visited = set()

        dst_text = self.stage.dst.compact_repr(self.stage.ctx)
        tree = Tree(Text(dst_text, style="bold blue"))

        if self.stage.dst in visited:
            tree.add(Text("...duplicate...", style="bold red"))
            return tree

        if self.stage.reason not in {
            Traceback.Type.NOOP,
            Traceback.Type.PASSTHROUGH,
        }:
            visited.add(self.stage.dst)

        reason = self.stage.reason.name
        algo = " ".join(self.stage.algo.split(" ")[:3])

        # Create a node for the reason and algorithm
        if self.stage.reason in {
            Traceback.Type.NOOP,
            Traceback.Type.PASSTHROUGH,
            Traceback.Type.COPIED,
        }:
            reason_branch = tree
        else:
            node_text = Text(f"{reason}", style="bold cyan")
            node_text.append(f"[{algo}]", style="italic green")
            reason_branch = tree.add(node_text)

        if self.back:
            for back_node in self.back:
                reason_branch.add(back_node.as_rich_tree(visited))
        elif self.stage.srcs:
            for src in self.stage.srcs:
                src_text = src.compact_repr(self.stage.ctx, use_name=True)
                reason_branch.add(Text(src_text, style="green"))
        else:
            reason_branch.add(Text("...no sources...", style="bold red"))

        return tree


class MutationStage:
    def __init__(
        self,
        tg_in: fbrk.TypeGraph,
        tg_out: fbrk.TypeGraph,
        algorithm: SolverAlgorithm | str,
        iteration: int,
        print_ctx: F.Parameters.ReprContext,
        transformations: Transformations,
        G_in: graph.GraphView,
        G_out: graph.GraphView,
    ):
        self.algorithm = algorithm
        self.iteration = iteration
        self.transformations = transformations
        self.print_ctx = print_ctx
        self.tg_in = tg_in
        self.tg_out = tg_out
        self.G_in = G_in
        self.G_out = G_out

        self.input_operables: OrderedSet[F.Parameters.is_parameter_operatable] = (
            OrderedSet(
                po
                for po in F.Parameters.is_parameter_operatable.bind_typegraph(
                    tg=self.tg_in
                ).get_instances(self.G_in)
                if not po.has_trait(is_irrelevant)
            )
        )

    @property
    @once
    def output_operables(self) -> OrderedSet[F.Parameters.is_parameter_operatable]:
        return OrderedSet(
            F.Parameters.is_parameter_operatable.bind_typegraph(
                self.tg_out
            ).get_instances(g=self.G_out)
        )

    @staticmethod
    def identity(
        tg: fbrk.TypeGraph,
        g: graph.GraphView,
        print_context: F.Parameters.ReprContext,
        algorithm: SolverAlgorithm | str = "identity",
        iteration: int = 0,
    ) -> "MutationStage":
        return MutationStage(
            tg_in=tg,
            tg_out=tg,
            G_in=g,
            G_out=g,
            algorithm=algorithm,
            iteration=iteration,
            print_ctx=print_context,
            transformations=Transformations.identity(
                tg, g, input_print_context=print_context
            ),
        )

    @property
    @once
    def is_identity(self) -> bool:
        return self.transformations.is_identity

    def as_identity(self, iteration: int = 0) -> "MutationStage":
        return MutationStage(
            self.tg_in,
            self.tg_out,
            G_in=self.G_in,
            G_out=self.G_out,
            algorithm="identity",
            iteration=iteration,
            print_ctx=self.print_ctx,
            transformations=Transformations.identity(
                self.tg_out,
                self.G_out,
                input_print_context=self.print_ctx,
            ),
        )

    def print_graph_contents(
        self,
        trait_filter: type[fabll.Node] = F.Parameters.is_parameter_operatable,
        log: Callable[[str], None] = logger.debug,
    ):
        pre_nodes = fabll.Traits.get_implementor_objects(
            trait=trait_filter.bind_typegraph(tg=self.tg_in), g=self.G_out
        )
        if SHOW_SS_IS:
            nodes = pre_nodes
        else:
            nodes = [
                n
                for n in pre_nodes
                if not (
                    MutatorUtils.is_set_literal_expression(
                        n.get_trait(F.Parameters.is_parameter_operatable)
                    )
                )
            ]
        out = ""
        node_by_depth = groupby(
            nodes,
            key=lambda n: (
                n.get_trait(F.Parameters.is_parameter_operatable).get_depth()
            ),
        )
        for depth, dnodes in sorted(node_by_depth.items(), key=lambda t: t[0]):
            out += f"\n  --Depth {depth}--"
            for n in dnodes:
                compact_repr = n.get_trait(
                    F.Parameters.is_parameter_operatable
                ).compact_repr(self.print_ctx)
                out += f"\n      {compact_repr}"

        if not nodes:
            return
        g_uuid = self.G_out.get_self_node().node().get_uuid()
        log(f"{self.G_out} {len(nodes)}/{len(pre_nodes)} [{out}\n]")

    def map_forward(
        self, param: F.Parameters.is_parameter_operatable
    ) -> F.Parameters.is_parameter_operatable | None:
        if self.is_identity:
            return param
        return self.transformations.mutated.get(param)

    @property
    @once
    def backwards_mutated(
        self,
    ) -> dict[
        F.Parameters.is_parameter_operatable,
        list[F.Parameters.is_parameter_operatable],
    ]:
        return invert_dict(self.transformations.mutated)

    @property
    @once
    def backwards_mapping(
        self,
    ) -> dict[
        F.Parameters.is_parameter_operatable,
        list[F.Parameters.is_parameter_operatable],
    ]:
        """Complete backward mapping including mutated, created, and soft_replaced."""
        result = dict(self.backwards_mutated)
        # created is already new → sources
        for new_expr, sources in self.transformations.created.items():
            if new_expr in result:
                result[new_expr] = result[new_expr] + sources
            else:
                result[new_expr] = list(sources)
        # soft_replaced needs inversion
        for src, dest in self.transformations.soft_replaced.items():
            if dest in result:
                result[dest].append(src)
            else:
                result[dest] = [src]
        return result

    def map_backward(
        self, param: F.Parameters.is_parameter_operatable
    ) -> list[F.Parameters.is_parameter_operatable]:
        if self.is_identity:
            return [param]
        return self.backwards_mapping.get(param, [])

    def print_mutation_table(self):
        if not self.transformations:
            return
        if not self.transformations.mutated:
            return

        if getattr(sys, "gettrace", lambda: None)():
            log = print
        else:
            log = logger.debug
            if not logger.isEnabledFor(logging.DEBUG):
                return

        created_ops = self.transformations.created

        def ___repr_op(op: F.Parameters.is_parameter_operatable) -> str:
            return op.compact_repr(self.print_ctx)

        rows: list[tuple[str, str]] = []

        for op, from_ops in created_ops.items():
            key = "new"
            key_from_ops = " \n  ".join(___repr_op(o) for o in from_ops)
            value = ___repr_op(op)
            if (op_e := op.as_expression.try_get()) and (
                MutatorUtils.is_set_literal_expression(op)
            ):
                expr = next(iter(op_e.get_operand_operatables()))
                lits = op_e.get_operand_literals()
                lit = next(iter(lits.values()))
                if not SHOW_SS_IS and expr in created_ops:
                    continue
                alias_type = "superset" if lits.keys() == {1} else "subset"
                key = f"new_{alias_type}\n{lit.pretty_str()}"
                value = ___repr_op(expr)
            if key_from_ops:
                key = f"{key} from\n  {key_from_ops}"
            rows.append((key, value))

        terminated = self.transformations.terminated.difference(
            co.try_get_sibling_trait(F.Expressions.is_predicate) for co in created_ops
        )
        for op in terminated:
            rows.append(
                (
                    "terminated",
                    ___repr_op(op.as_expression.get().as_parameter_operatable.get()),
                )
            )

        copied = self.transformations.copied
        printed = set[F.Parameters.is_parameter_operatable]()

        for s, d in self.transformations.mutated.items():
            if not VERBOSE_TABLE:
                if s in copied:
                    continue

                # for no-op mutations (non dirty)
                if s is d:
                    continue

            old = ___repr_op(s)
            new = ___repr_op(d)
            if VERBOSE_TABLE:
                old += "\n\n" + repr(s)
                new += "\n\n" + repr(d)
            if old == new:
                continue
            if (
                new.count("✓") == old.count("✓") + 1
                and (s_e := s.as_expression.try_get())
                and s_e.as_assertable.try_get()
                and new.replace("✓", "") == old.replace("✓", "")
                and (d_lit := d.try_extract_superset())
                and (s_lit := s.try_extract_superset())
                and d_lit.op_setic_equals(s_lit)  # TODO g & tg
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
                old = ___repr_op(s)
                new = ___repr_op(d)
                # already printed above
                if old != new:
                    continue
                if VERBOSE_TABLE:
                    old += "\n\n" + repr(s)
                rows.append((old, "merged"))

        for s in self.transformations.removed:
            old = ___repr_op(s)
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

            log(rich_to_string(table))

    def get_traceback_stage(
        self, param: F.Parameters.is_parameter_operatable
    ) -> Traceback.Stage:
        # FIXME reenable
        # assert param in self.output_operables
        dst = param
        algo = (
            self.algorithm if isinstance(self.algorithm, str) else self.algorithm.name
        )
        related = []

        if self.is_identity:
            srcs = [param]
            reason = Traceback.Type.NOOP
        elif param in self.input_operables:
            srcs = [param]
            reason = Traceback.Type.PASSTHROUGH
        elif param in self.transformations.created:
            srcs = self.transformations.created[param]
            reason = Traceback.Type.CREATED
        elif param in self.transformations.soft_replaced:
            srcs = [
                k for k, v in self.transformations.soft_replaced.items() if v is param
            ]
            reason = Traceback.Type.SOFT_REPLACED
        else:
            origins = self.map_backward(param)
            # TODO remove (when backwards_mapping @once cache is fixed)
            assert not duplicates(origins, id)
            srcs = origins
            if len(origins) == 1:
                origin = origins[0]
                if origin in self.transformations.copied:
                    new_predicates = self.transformations.get_new_predicates(origin)
                    if new_predicates:
                        reason = Traceback.Type.CONSTRAINED
                        related_ = [
                            self.get_traceback_stage(
                                e.get_sibling_trait(
                                    F.Parameters.is_parameter_operatable
                                )
                            )
                            for e in new_predicates
                        ]
                        for r in related_:
                            for r_s in r.srcs:
                                if r_s not in srcs:
                                    srcs.append(r_s)

                        # related.extend(related_)
                    else:
                        reason = Traceback.Type.COPIED
                else:
                    reason = Traceback.Type.MUTATED
            else:
                reason = Traceback.Type.MERGED

        return Traceback.Stage(
            srcs=srcs,
            dst=dst,
            reason=reason,
            related=related,
            algo=algo,
            ctx=self.print_ctx,
        )


class solver_relevant(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class MutationMap:
    @dataclass
    class LookupResult:
        maps_to: F.Parameters.is_parameter_operatable | None = None
        removed: bool = False

    def __init__(self, *stages: MutationStage):
        if not stages:
            raise ValueError("needs at least one stage")
        self.mutation_stages: list[MutationStage] = list(stages)
        self._graphs_destroyed = False

    @property
    @once
    def non_identity_stages(self) -> list[MutationStage]:
        return [m for m in self.mutation_stages if not m.is_identity]

    def map_forward(
        self, param: F.Parameters.is_parameter_operatable, seek_start: bool = False
    ) -> LookupResult:
        """
        return mapped param, True if removed or False if not mapped
        """
        # assert param.is_parameter()
        # is_root = fabll.Traits(param).get_obj_raw().get_parent() is not None

        if not self.non_identity_stages:
            out = self.first_stage.map_forward(param)
            # TODO consider
            # if out is None and is_root:
            #    raise KeyErrorNotFound(
            #        f"Looking for root parameter not in graph: {param}"
            #    )
            return MutationMap.LookupResult(maps_to=out)

        chain_end: F.Parameters.is_parameter_operatable = param
        if seek_start:
            first_stage = first(
                (
                    i
                    for i, m in enumerate(self.non_identity_stages)
                    if chain_end in m.input_operables
                ),
                None,
            )
            if first_stage is None:
                return MutationMap.LookupResult()
        else:
            first_stage = 0

        for m in self.non_identity_stages[first_stage:]:
            maps_to = m.map_forward(chain_end)
            if maps_to is None:
                # is_start = param is chain_end
                # assert not is_root or is_start, (
                #    "should never remove root parameters"
                #    f" chain_end {param} -> {chain_end} interrupted at"
                #    f" {m.algorithm}:{m.iteration}"
                # )
                # if is_root and is_start:
                #    raise KeyErrorNotFound(
                #        f"Looking for root parameter not in graph: {param}"
                #    )
                return MutationMap.LookupResult(removed=chain_end is not param)
            chain_end = maps_to
        return MutationMap.LookupResult(maps_to=chain_end)

    def map_backward(
        self, param: F.Parameters.is_parameter_operatable, only_full: bool = True
    ) -> list[F.Parameters.is_parameter_operatable]:
        chain_fronts = [param]
        collected = []

        for m in reversed(self.mutation_stages):
            next_fronts = []
            for chain_front in chain_fronts:
                maps_to = m.map_backward(chain_front)
                next_fronts.extend(maps_to)
            chain_fronts = next_fronts
            collected.extend(next_fronts)

        if only_full:
            return next_fronts

        return collected

    @property
    def compressed_mapping_forwards(
        self,
    ) -> dict[F.Parameters.is_parameter_operatable, LookupResult]:
        return {
            start: self.map_forward(start, seek_start=False)
            for start in self.input_operables
        }

    @property
    def compressed_mapping_forwards_complete(
        self,
    ) -> dict[
        F.Parameters.is_parameter_operatable, F.Parameters.is_parameter_operatable
    ]:
        return {
            k: v.maps_to
            for k, v in self.compressed_mapping_forwards.items()
            if v.maps_to is not None
        }

    @property
    @once
    def compressed_mapping_backwards(
        self,
    ) -> dict[
        F.Parameters.is_parameter_operatable,
        list[F.Parameters.is_parameter_operatable],
    ]:
        return {
            end: self.map_backward(end, only_full=True) for end in self.output_operables
        }

    def is_removed(self, param: F.Parameters.is_parameter_operatable) -> bool:
        return self.map_forward(param) is False

    def is_mapped(self, p: F.Parameters.is_parameter_operatable) -> bool:
        return self.map_forward(p) is not False

    def try_extract_superset(
        self,
        po: F.Parameters.is_parameter_operatable,
        domain_default: bool = False,
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> F.Literals.is_literal | None:
        def _default():
            if not domain_default:
                return None
            if not (p := po.as_parameter.try_get()):
                raise ValueError("domain_default only supported for parameters")
            return p.domain_set()

        maps_to = self.map_forward(po).maps_to
        if not maps_to:
            return _default()
        lit = maps_to.try_extract_superset()
        if lit is None:
            return _default()

        # solver lit has no unit (dimensionless), need to convert back to parameter unit
        if (
            (param_unit_t := po.try_get_sibling_trait(F.Units.has_unit))
            and (lit_n := fabll.Traits(lit).get_obj_raw().try_cast(F.Literals.Numbers))
            and not lit_n.are_units_compatible(param_unit := param_unit_t.get_is_unit())
        ):
            N = F.Literals.Numbers.bind_typegraph(tg or lit_n.tg)
            NumberLit = lambda value, unit: N.create_instance(  # noqa: E731
                g=g or lit_n.g
            ).setup_from_singleton(value=value, unit=unit)
            return (
                # return ((lit - offset) / multiplier) * param_unit
                lit_n.op_subtract_intervals(
                    NumberLit(param_unit._extract_offset(), lit_n.get_is_unit()),
                )
                .op_div_intervals(
                    NumberLit(param_unit._extract_multiplier(), lit_n.get_is_unit()),
                )
                .op_mul_intervals(
                    NumberLit(1, param_unit),
                )
                .is_literal.get()
            )

        return lit

    def __repr__(self) -> str:
        return f"ReprMap({str(self)})"

    def __str__(self) -> str:
        return (
            f"|stages|={len(self.mutation_stages)}"
            f", |ops|={len(self.last_stage.output_operables)}"
            f", {self.G_out}"
        )

    @staticmethod
    def _bootstrap_copy(
        g_in: graph.GraphView, tg_in: fbrk.TypeGraph
    ) -> tuple[graph.GraphView, fbrk.TypeGraph]:
        # TODO move somewhere else?
        g_out = graph.GraphView.create()
        tg_out = tg_in.copy_into(target_graph=g_out, minimal=True)
        for module in (F.Expressions, F.Parameters, F.Literals, F.Units):
            for _, expr_cls in inspect.getmembers(module):
                if not isinstance(expr_cls, type):
                    continue
                if not issubclass(expr_cls, fabll.Node):
                    continue
                fbrk.TypeGraph.copy_node_into(
                    start_node=expr_cls.bind_typegraph(tg_in).get_or_create_type(),
                    target_graph=g_out,
                )

        return g_out, tg_out

    @staticmethod
    def bootstrap(
        tg: fbrk.TypeGraph,
        g: graph.GraphView,
        algorithm: SolverAlgorithm | str = "identity",
        iteration: int = 0,
        print_context: F.Parameters.ReprContext | None = None,
        relevant: list[F.Parameters.can_be_operand] | None = None,
    ) -> "MutationMap":
        if relevant is not None:
            g_out, tg_out = MutationMap._bootstrap_copy(g, tg)
            relevant_root_predicates = MutatorUtils.get_relevant_predicates(
                *relevant,
            )
            for root_expr in relevant_root_predicates:
                root_expr.copy_into(g_out)

            nodes_uuids = {p.instance.node().get_uuid() for p in relevant}
            for p_out in fabll.Traits.get_implementors(
                F.Parameters.can_be_operand.bind_typegraph(tg_out)
            ):
                if p_out.instance.node().get_uuid() not in nodes_uuids:
                    continue
                fabll.Traits.create_and_add_instance_to(p_out, solver_relevant)

            print_context = print_context or F.Parameters.ReprContext()
            all_ops_out = F.Parameters.is_parameter_operatable.bind_typegraph(
                tg_out
            ).get_instances(g=g_out)

            mapping = {
                F.Parameters.is_parameter_operatable.bind_instance(
                    g.bind(node=op.instance.node())
                ): op
                for op in all_ops_out
            }
            # copy over source name
            for p_old, p_new in mapping.items():
                if (p_new_p := p_new.as_parameter.try_get()) is None:
                    continue

                print_context.override_name(
                    p_new_p,
                    fabll.Traits(p_old).get_obj_raw().get_full_name(include_uuid=False),
                )

            if S_LOG:
                logger.debug(
                    "Relevant root predicates: "
                    + indented_container(
                        [
                            p.as_expression.get().compact_repr(
                                context=print_context,
                                no_lit_suffix=True,
                                use_name=True,
                            )
                            for p in relevant_root_predicates
                        ]
                    )
                )
                expr_count = len(
                    fabll.Traits.get_implementors(
                        F.Expressions.is_expression.bind_typegraph(tg_out)
                    )
                )
                param_count = len(
                    fabll.Traits.get_implementors(
                        F.Parameters.is_parameter.bind_typegraph(tg_out)
                    )
                )
                lit_count = len(
                    fabll.Traits.get_implementors(
                        F.Literals.is_literal.bind_typegraph(tg_out)
                    )
                )
                logger.debug(
                    f"|lits|={lit_count}"
                    f", |exprs|={expr_count}"
                    f", |params|={param_count} {g_out}"
                )
            mut_map = MutationMap(
                MutationStage(
                    tg_in=tg,
                    tg_out=tg_out,
                    algorithm=algorithm,
                    iteration=iteration,
                    print_ctx=print_context,
                    transformations=Transformations(
                        print_ctx=print_context,
                        mutated=mapping,
                    ),
                    G_in=g,
                    G_out=g_out,
                )
            )
        else:
            mut_map = MutationMap(
                MutationStage.identity(
                    tg,
                    g,
                    algorithm=algorithm,
                    iteration=iteration,
                    print_context=print_context or F.Parameters.ReprContext(),
                )
            )

        # canonicalize
        from faebryk.core.solver.symbolic.canonical import (
            convert_to_canonical_operations,
            fix_ss_lit_invariants,
        )

        for algo in (convert_to_canonical_operations, fix_ss_lit_invariants):
            logger.debug(f"Running {algo.name}")
            algo_result = Mutator(
                mut_map,
                algo,
                iteration=0,
                terminal=False,
            ).run()

            mut_map = mut_map.extend(algo_result.mutation_stage)

        return mut_map

    def extend(self, *changes: MutationStage) -> "MutationMap":
        return MutationMap(*self.mutation_stages, *changes)

    @property
    def last_stage(self) -> MutationStage:
        return self.mutation_stages[-1]

    @property
    def G_out(self) -> graph.GraphView:
        return self.last_stage.G_out

    @property
    def output_operables(self) -> OrderedSet[F.Parameters.is_parameter_operatable]:
        return self.last_stage.output_operables

    @property
    def first_stage(self) -> MutationStage:
        return self.mutation_stages[0]

    @property
    def G_in(self) -> graph.GraphView:
        return self.first_stage.G_in

    @property
    def input_operables(self) -> OrderedSet[F.Parameters.is_parameter_operatable]:
        return self.first_stage.input_operables

    @property
    def print_ctx(self) -> F.Parameters.ReprContext:
        return self.first_stage.print_ctx

    def get_iteration_mutation(self, algo: SolverAlgorithm) -> "MutationMap | None":
        last = first(
            (
                i
                for i, m in reversed(list(enumerate(self.mutation_stages)))
                if m.algorithm is algo
            ),
            None,
        )
        if last is None:
            return None
        return self.submap(start=last)

    def submap(self, start: int = 0) -> "MutationMap":
        return MutationMap(*self.mutation_stages[start:])

    def print_name_mappings(self, log: Callable[[str], None] = logger.debug):
        table = Table(title="Name mappings", show_lines=True)
        table.add_column("Node")
        table.add_column("Variable")

        params = set(
            F.Parameters.is_parameter.bind_typegraph(self.tg_out).get_instances(
                g=self.G_out
            )
        )
        for p in sorted(
            params,
            key=lambda p: p.get_full_name(),
        ):
            table.add_row(
                fabll.Traits(p).get_obj_raw().get_full_name(),
                p.compact_repr(self.print_ctx),
            )

        if table.rows:
            log(rich_to_string(table))

    def get_traceback(self, param: F.Parameters.is_parameter_operatable) -> Traceback:
        start = self.last_stage.get_traceback_stage(param)
        out = Traceback(stage=start)
        deepest = [out]
        for m in reversed(self.mutation_stages[:-1]):
            new_deepest = []
            for tb in deepest:
                for op in tb.stage.srcs:
                    branch = m.get_traceback_stage(op)
                    new_tb = Traceback(stage=branch)
                    new_deepest.append(new_tb)
                    tb.back.append(new_tb)
                    # for r in branch.related:
                    #    related_tb = Traceback(stage=r)
                    #    new_deepest.append(related_tb)
                    #    tb.back.append(related_tb)
            deepest = new_deepest
        return out

    @property
    @once
    def has_merged(
        self,
    ) -> dict[
        F.Parameters.is_parameter_operatable,
        list[F.Parameters.is_parameter_operatable],
    ]:
        mapping = self.compressed_mapping_backwards
        return {k: v for k, v in mapping.items() if len(v) > 1}

    @property
    @once
    def non_trivial_mutated_expressions(
        self,
    ) -> OrderedSet[F.Expressions.is_expression]:
        """
        return expressions that are structurally new (did not exist in this form before)
        """
        # TODO make faster, compact repr is a pretty bad one
        # consider congruence instead, but be careful since not in same graph space
        out: OrderedSet[F.Expressions.is_expression] = OrderedSet(
            v.as_expression.force_get()
            for v, ks in self.compressed_mapping_backwards.items()
            if v.try_get_sibling_trait(F.Expressions.is_canonical)
            # if all merged changed, else covered by merged
            and all(
                k.try_get_sibling_trait(F.Expressions.is_canonical)
                and k is not v
                and k.compact_repr() != v.compact_repr()
                for k in ks
            )
        )
        return out

    @property
    def tg_in(self) -> fbrk.TypeGraph:
        return self.first_stage.tg_in

    @property
    def tg_out(self) -> fbrk.TypeGraph:
        return self.last_stage.tg_out

    def destroy(self) -> None:
        if self._graphs_destroyed:
            return
        from faebryk.libs.util import groupby

        all_gs = {stage.G_out for stage in self.mutation_stages}
        gs = groupby(all_gs, lambda g: g.get_self_node().node().get_uuid())
        g_in_uuid = self.G_in.get_self_node().node().get_uuid()
        g_out_uuid = self.G_out.get_self_node().node().get_uuid()
        if g_in_uuid in gs:
            del gs[g_in_uuid]
        if g_out_uuid in gs:
            del gs[g_out_uuid]

        for g in gs.values():
            g_to_destroy = next(iter(g))
            logger.debug(
                "destroying graph %s %s",
                g_to_destroy,
                hex(g_to_destroy.get_self_node().node().get_uuid()),
            )
            g_to_destroy.destroy()
        self._graphs_destroyed = True


@dataclass
class AlgoResult:
    mutation_stage: MutationStage
    dirty: bool


class ExpressionBuilder[
    T: F.Expressions.ExpressionNodes = F.Expressions.ExpressionNodes
](NamedTuple):
    factory: type[T]
    operands: list[F.Parameters.can_be_operand]
    assert_: bool
    terminate: bool

    def indexed_ops(self) -> dict[int, F.Parameters.can_be_operand]:
        return {i: o for i, o in enumerate(self.operands)}

    def indexed_ops_with_trait[TR: fabll.NodeT](self, trait: type[TR]) -> dict[int, TR]:
        return {
            i: op
            for i, o in self.indexed_ops().items()
            if (op := o.try_get_sibling_trait(trait))
        }

    def indexed_lits(self) -> dict[int, F.Literals.is_literal]:
        return self.indexed_ops_with_trait(F.Literals.is_literal)

    def indexed_pos(self) -> dict[int, F.Parameters.is_parameter_operatable]:
        return self.indexed_ops_with_trait(F.Parameters.is_parameter_operatable)

    def __repr__(self) -> str:
        return pretty_expr(self)

    def matches(self, other: F.Expressions.is_expression) -> bool:
        return (
            fabll.Traits(other).get_obj_raw().isinstance(self.factory)
            and other.get_operands() == self.operands
            and self.terminate == other.has_trait(is_terminated)
            and self.assert_ == other.has_trait(F.Expressions.is_predicate)
        )

    # TODO use this more
    def with_(
        self,
        factory: type[T] | None = None,
        operands: list[F.Parameters.can_be_operand] | None = None,
        assert_: bool | None = None,
        terminate: bool | None = None,
    ) -> "ExpressionBuilder[T]":
        return ExpressionBuilder(
            factory or self.factory,
            operands if operands is not None else self.operands,
            assert_ if assert_ is not None else self.assert_,
            terminate if terminate is not None else self.terminate,
        )


class Mutator:
    # Algorithm Interface --------------------------------------------------------------
    @overload
    def make_singleton(self, value: bool) -> F.Literals.Booleans: ...

    @overload
    def make_singleton(self, value: float) -> F.Literals.Numbers: ...

    @overload
    def make_singleton(self, value: Enum) -> F.Literals.AbstractEnums: ...

    @overload
    def make_singleton(self, value: str) -> F.Literals.Strings: ...

    def make_singleton(
        self, value: F.Literals.LiteralValues
    ) -> F.Literals.LiteralNodes:
        return F.Literals.make_singleton(self.G_transient, self.tg_out, value)

    def _mutate(
        self,
        po: F.Parameters.is_parameter_operatable,
        new_po: F.Parameters.is_parameter_operatable,
    ) -> F.Parameters.is_parameter_operatable:
        """
        Low-level mutation function, you are on your own.
        Consider using mutate_parameter or mutate_expression instead.
        """
        if self.has_been_mutated(po):
            if not self.get_mutated(po).is_same(new_po):
                raise ValueError(f"already mutated to: {self.get_mutated(po)}")

        if self.is_removed(po):
            raise ValueError("Object marked removed")

        self.transformations.mutated[po] = new_po
        return new_po

    def mutate_parameter(
        self,
        param: F.Parameters.is_parameter,
    ) -> F.Parameters.is_parameter:
        p_po = param.as_parameter_operatable.get()
        if p_mutated := self.try_get_mutated(p_po):
            return p_mutated.as_parameter.force_get()

        param_obj = fabll.Traits(param).get_obj_raw()

        if param_obj.has_trait(F.Units.has_unit) and param_obj.try_cast(
            F.Parameters.NumericParameter
        ):
            new_param = (
                F.Parameters.NumericParameter.bind_typegraph(self.tg_out)
                .create_instance(self.G_out)
                .setup(is_unit=None, domain=F.Parameters.NumericParameter.DOMAIN_SKIP)
            ).is_parameter_operatable.get()
        elif param_obj.try_cast(F.Parameters.EnumParameter):
            # FIXME, should just use copy_into
            # also why is setup not called?
            # started writing a test for this in
            #   Parameters.py:test_copy_into_enum_parameter
            new_param = (
                F.Parameters.EnumParameter.bind_typegraph(self.tg_out).create_instance(
                    self.G_out
                )
                # .setup(enum=p.get_enum())
            ).is_parameter_operatable.get()
        else:
            # trigger tg copy
            self.tg_out
            new_param = param.copy_into(self.G_out).get_sibling_trait(
                F.Parameters.is_parameter_operatable
            )

        # needed for non-copy transfer
        self.print_ctx.override_name(
            new_param.as_parameter.force_get(), self.print_ctx.get_or_create_name(param)
        )

        return self._mutate(
            p_po,
            new_param,
        ).as_parameter.force_get()

    def _create_and_insert_expression[T: fabll.NodeT](
        self,
        builder: ExpressionBuilder[T],
    ) -> T:
        """
        - check canonical
        - map operands to mutated (in new graph)
        - assert/terminate
        - check graph consistency
        => create expression in new graph
        """
        expr_factory, operands, assert_, terminate = builder

        # check canonical
        # only after canonicalize has run
        if self.iteration > 0:
            expr_bound = expr_factory.bind_typegraph(self.tg_out)
            assert expr_bound.check_if_instance_of_type_has_trait(
                F.Expressions.is_canonical
            )

        # map operands to mutated
        new_operands = [
            copy
            for op in operands
            if (
                copy := self.get_copy(
                    op,
                    accept_soft=not (
                        expr_factory is F.Expressions.IsSubset and assert_
                    ),
                )
            )
            is not None
        ]

        new_expr = (
            expr_factory.bind_typegraph(self.tg_out)
            .create_instance(self.G_out)
            .setup(*new_operands)  # type: ignore # TODO stupid pyright
        )

        if assert_:
            ce = new_expr.get_trait(F.Expressions.is_assertable)
            self.assert_(ce, terminate=terminate, track=False)

        op_graphs = {
            op.g.get_self_node().node().get_uuid(): op.g for op in new_operands
        }
        assert not op_graphs or set(op_graphs.keys()) == {
            self.G_out.get_self_node().node().get_uuid()
        }, f"Graph mismatch: {op_graphs} != {self.G_out}"

        return new_expr

    def create_check_and_insert_expression(
        self,
        expr_factory: type[F.Expressions.ExpressionNodes],
        *operands: F.Parameters.can_be_operand,
        from_ops: Sequence[F.Parameters.is_parameter_operatable] | None = None,
        assert_: bool = False,
        terminate: bool = False,
        allow_uncorrelated_congruence_match: bool = False,
    ) -> "InsertExpressionResult":
        import faebryk.core.solver.symbolic.invariants as invariants

        from_ops = list(set(from_ops or []))
        c_operands = [self.get_copy(op) for op in operands]

        builder = invariants.ExpressionBuilder(
            expr_factory,
            c_operands,
            assert_=assert_,
            terminate=terminate,
        )

        res = invariants.wrap_insert_expression(
            self,
            builder,
            allow_uncorrelated_congruence_match=allow_uncorrelated_congruence_match,
        )

        if res.is_new and (
            out_po := not_none(res.out_operand).as_parameter_operatable.try_get()
        ):
            self.transformations.created[out_po] = from_ops

        return res

    def mutate_expression(
        self,
        expr: F.Expressions.is_expression,
        operands: Iterable[F.Parameters.can_be_operand] | None = None,
        expression_factory: type[F.Expressions.ExpressionNodes] | None = None,
    ) -> F.Parameters.can_be_operand:
        import faebryk.core.solver.symbolic.invariants as invariants

        if expression_factory is None:
            expression_factory = self.utils.hack_get_expr_type(expr)

        if operands is None:
            operands = expr.get_operands()

        expr_po = expr.as_parameter_operatable.get()
        # if mutated
        if expr_po in self.transformations.mutated:
            return self.get_mutated(expr_po).as_operand.get()

        expr_pred = expr.try_get_sibling_trait(F.Expressions.is_predicate)
        assert_ = expr_pred is not None
        terminate = (assert_ or not expr_pred) and self.is_terminated(expr)

        expr_obj = fabll.Traits(expr).get_obj_raw()
        copy_only = (
            expr_obj.isinstance(expression_factory) and operands == expr.get_operands()
        )

        c_operands = [self.get_copy(op) for op in operands]

        builder = invariants.ExpressionBuilder(
            factory=expression_factory,
            operands=c_operands,
            assert_=assert_,
            terminate=terminate,
        )
        res = invariants.wrap_insert_expression(
            self, builder, expr_already_exists_in_old_graph=copy_only
        )
        if res.out_operand.as_literal.try_get():
            return res.out_operand

        new_expr_po = res.out_operand.as_parameter_operatable.force_get()
        out = self._mutate(expr_po, new_expr_po)
        return out.as_operand.get()

    def soft_replace(
        self,
        current: F.Parameters.is_parameter_operatable,
        new: F.Parameters.is_parameter_operatable,
    ):
        """
        Replace A in all operations with B, but keep A in the graph.
        Except for A ss! X
        """

        if self.has_been_mutated(current):
            copy = self.get_mutated(current)
            exps = copy.get_operations()  # noqa: F841
            # FIXME: reenable, but alias classes need to take this into account
            # assert all(isinstance(o, (Is, IsSubset)) and o.constrained for o in exps)

        self.transformations.soft_replaced[current] = new
        self.get_copy_po(current, accept_soft=False)

    def get_copy(
        self,
        obj: F.Parameters.can_be_operand,
        accept_soft: bool = True,
    ) -> F.Parameters.can_be_operand:
        if obj.is_in_graph(self.G_out):
            return obj
        if obj_po := obj.as_parameter_operatable.try_get():
            return self.copy_operand(obj_po, accept_soft)
        if obj_lit := obj.as_literal.try_get():
            self.tg_out
            return obj_lit.copy_into(self.G_out).as_operand.get()
        raise ValueError(f"Cannot copy {obj}")

    def copy_operand(
        self,
        obj_po: F.Parameters.is_parameter_operatable,
        accept_soft: bool = True,
    ) -> F.Parameters.can_be_operand:
        if accept_soft and obj_po in self.transformations.soft_replaced:
            return self.transformations.soft_replaced[obj_po].as_operand.get()

        if m := self.try_get_mutated(obj_po):
            return m.as_operand.get()

        # TODO: not sure if ok
        # if obj is new, no need to copy
        # TODO add guard to _mutate to not let new stuff be mutated
        if obj_po in self.transformations.created or obj_po in set(
            self.transformations.mutated.values()
        ):
            return obj_po.as_operand.get()

        # purely for debug
        self.transformations.copied.add(obj_po)

        if expr := obj_po.as_expression.try_get():
            return self.mutate_expression(expr)
        elif p := obj_po.as_parameter.try_get():
            return self.mutate_parameter(p).as_operand.get()

        assert False

    def get_copy_po(
        self,
        obj_po: F.Parameters.is_parameter_operatable,
        accept_soft: bool = True,
    ) -> F.Parameters.is_parameter_operatable:
        return self.copy_operand(
            obj_po, accept_soft=accept_soft
        ).as_parameter_operatable.force_get()

    def remove(
        self, *po: F.Parameters.is_parameter_operatable, no_check_roots: bool = False
    ):
        """
        force: Disables check for root objects
        """
        assert not any(p in self.transformations.mutated for p in po), (
            "Object already in repr_map"
        )
        if not no_check_roots:
            root_pos = [
                p for p in po if fabll.Traits(p).get_obj_raw().get_parent() is not None
            ]
            assert not root_pos, f"should never remove root parameters: {root_pos}"
        self.transformations.removed.update(po)

    def register_created_parameter(
        self,
        param: F.Parameters.is_parameter,
        from_ops: Sequence[F.Parameters.is_parameter_operatable] | None = None,
    ) -> F.Parameters.is_parameter:
        self.transformations.created[param.as_parameter_operatable.get()] = list(
            from_ops or []
        )
        return param

    def assert_(
        self,
        *po: F.Expressions.is_assertable,
        terminate: bool = False,
        track: bool = True,
    ):
        for p in po:
            if not p.is_asserted():
                p.assert_()
                if track:
                    self.transformations.asserted.add(p)
            if terminate:
                self.terminate(p.get_sibling_trait(F.Expressions.is_expression))

    def terminate(self, expr: F.Expressions.is_expression):
        if self.is_terminated(expr):
            return
        new_graph = (
            expr.g.get_self_node()
            .node()
            .is_same(other=self.G_out.get_self_node().node())
        )
        if new_graph:
            fabll.Traits.create_and_add_instance_to(
                fabll.Traits(expr).get_obj_raw(), is_terminated
            )
        else:
            self.transformations.terminated.add(expr)

    def mark_irrelevant(self, po: F.Parameters.is_parameter_operatable):
        if po.try_get_sibling_trait(is_irrelevant) is not None:
            return
        fabll.Traits.create_and_add_instance_to(
            fabll.Traits(po).get_obj_raw(), is_irrelevant
        )

    # Algorithm Query ------------------------------------------------------------------
    def is_terminated(self, expr: F.Expressions.is_expression) -> bool:
        return (
            expr in self.transformations.terminated
            or expr.try_get_sibling_trait(is_terminated) is not None
        )

    def get_parameter_operatables(
        self, include_terminated: bool = False, sort_by_depth: bool = False
    ) -> (
        list[F.Parameters.is_parameter_operatable]
        | set[F.Parameters.is_parameter_operatable]
    ):
        out = set(
            fabll.Traits.get_implementors(
                F.Parameters.is_parameter_operatable.bind_typegraph(self.tg_in),
                self.G_in,
            )
        )

        if not include_terminated:
            terminated = fabll.Traits.get_implementor_siblings(
                is_terminated.bind_typegraph(self.tg_in),
                F.Parameters.is_parameter_operatable,
                self.G_in,
            )
            out.difference_update(terminated)

        if sort_by_depth:
            out = F.Expressions.is_expression.sort_by_depth_po(out, ascending=True)

        return out

    def get_parameters(self) -> OrderedSet[F.Parameters.is_parameter]:
        return OrderedSet(
            fabll.Traits.get_implementors(
                F.Parameters.is_parameter.bind_typegraph(self.tg_in), self.G_in
            )
        )

    def get_parameters_of_type[T: fabll.NodeT](self, t: type[T]) -> OrderedSet[T]:
        return OrderedSet(t.bind_typegraph(self.tg_in).get_instances(self.G_in))

    def get_typed_expressions[T: "fabll.NodeT"](
        self,
        t: type[T] = fabll.Node[Any],
        sort_by_depth: bool = False,
        created_only: bool = False,
        new_only: bool = False,
        include_terminated: bool = False,
        required_traits: tuple[type[fabll.NodeT], ...] = (),
        include_removed: bool = False,
        include_mutated: bool = False,
    ) -> list[T] | OrderedSet[T]:
        assert not new_only or not created_only

        if new_only:
            out: OrderedSet[T] = OrderedSet(
                ne
                for n in self._new_operables
                if (ne := fabll.Traits(n).get_obj_raw().try_cast(t))
            )
        elif created_only:
            out = OrderedSet(
                ne
                for n in self.transformations.created
                if (ne := fabll.Traits(n).get_obj_raw().try_cast(t))
            )
        elif t is fabll.Node:
            if len(required_traits) == 1:
                out = cast(
                    OrderedSet[T],
                    OrderedSet(
                        fabll.Traits.get_implementor_objects(
                            required_traits[0].bind_typegraph(self.tg_in),
                            self.G_in,
                        )
                    ),
                )
            else:
                out = cast(
                    OrderedSet[T],
                    OrderedSet(
                        fabll.Traits.get_implementor_objects(
                            F.Expressions.is_expression.bind_typegraph(self.tg_in),
                            self.G_in,
                        )
                    ),
                )
        else:
            out = OrderedSet(t.bind_typegraph(self.tg_in).get_instances(self.G_in))

        if not include_terminated:
            terminated = fabll.Traits.get_implementor_objects(
                is_terminated.bind_typegraph(self.tg_in),
                self.G_in,
            )
            out.difference_update(terminated)

        if required_traits and not (t is fabll.Node and len(required_traits) == 1):
            out = OrderedSet(
                o for o in out if all(o.has_trait(t) for t in required_traits)
            )

        if not include_removed:
            out.difference_update(self.transformations.removed)
        if not include_mutated:
            out.difference_update(self.transformations.mutated.keys())

        if sort_by_depth:
            out = F.Expressions.is_expression.sort_by_depth(out, ascending=True)

        return out

    def get_expressions(
        self,
        sort_by_depth: bool = False,
        created_only: bool = False,
        new_only: bool = False,
        include_terminated: bool = False,
        required_traits: tuple[type[fabll.NodeT], ...] = (),
    ) -> OrderedSet[F.Expressions.is_expression] | list[F.Expressions.is_expression]:
        # TODO make this first class instead of calling
        typed = self.get_typed_expressions(
            t=fabll.Node,
            sort_by_depth=sort_by_depth,
            created_only=created_only,
            new_only=new_only,
            include_terminated=include_terminated,
            required_traits=required_traits,
        )
        t = OrderedSet if isinstance(typed, OrderedSet) else list
        return t(e.get_trait(F.Expressions.is_expression) for e in typed)

    def is_removed(self, po: F.Parameters.is_parameter_operatable) -> bool:
        return po in self.transformations.removed

    def has_been_mutated(self, po: F.Parameters.is_parameter_operatable) -> bool:
        return po in self.transformations.mutated

    def get_mutated(
        self, po: F.Parameters.is_parameter_operatable
    ) -> F.Parameters.is_parameter_operatable:
        return self.transformations.mutated[po]

    def try_get_mutated(
        self, po: F.Parameters.is_parameter_operatable
    ) -> F.Parameters.is_parameter_operatable | None:
        return self.transformations.mutated.get(po)

    def get_operations[T: fabll.NodeT](
        self,
        po: F.Parameters.is_parameter_operatable,
        types: type[T] = fabll.Node,
        predicates_only: bool = False,
        recursive: bool = False,
    ) -> OrderedSet[T]:
        return OrderedSet(
            expr
            for expr in po.get_operations(
                types=types, predicates_only=predicates_only, recursive=recursive
            )
            if not expr.has_trait(is_irrelevant)
        )

    # Solver Interface -----------------------------------------------------------------
    def __init__(
        self,
        mutation_map: MutationMap,
        algo: SolverAlgorithm,
        iteration: int,
        terminal: bool,
    ) -> None:
        self.algo = algo
        self.terminal = terminal
        self.mutation_map = mutation_map
        self.iteration = iteration

        self.utils = MutatorUtils(self)

        self.G_in = mutation_map.G_out
        self.G_out: graph.GraphView = graph.GraphView.create()
        # for temporary nodes like literals
        self.G_transient: graph.GraphView = graph.GraphView.create()
        self.tg_in: fbrk.TypeGraph = mutation_map.tg_out

        self.print_ctx = mutation_map.last_stage.print_ctx
        self._mutations_since_last_iteration = mutation_map.get_iteration_mutation(algo)

        self._starting_operables = OrderedSet(
            self.get_parameter_operatables(include_terminated=True)
        )

        self.transformations = Transformations(print_ctx=self.print_ctx)

    @property
    @once
    def tg_out(self) -> fbrk.TypeGraph:
        return self.tg_in.copy_into(target_graph=self.G_out, minimal=False)

    @property
    @once
    def _new_operables(self) -> OrderedSet[F.Parameters.is_parameter_operatable]:
        _last_run_operables: OrderedSet[F.Parameters.is_parameter_operatable] = (
            OrderedSet()
        )
        if self._mutations_since_last_iteration is not None:
            _last_run_operables = OrderedSet(
                self._mutations_since_last_iteration.compressed_mapping_forwards_complete.values()
            )
        assert _last_run_operables.issubset(self._starting_operables)
        return self._starting_operables - _last_run_operables

    def _run(self):
        self.algo(self)

    def _copy_terminated(self):
        """
        Copy all terminated expressions to G_out before the algorithm runs.

        This ensures invariants are upheld during expression copying:
        - Congruence checks (find_congruent_expression) look in G_out
        - Subsumption checks (find_subsuming_expression) query operations in G_out
        - If terminated expressions aren't copied first, these checks might miss
          existing expressions, leading to duplicates or invariant violations.

        Terminated expressions are "stable" - algorithms should not transform them
        further, so they can be safely pre-copied without affecting algorithm behavior.
        """
        if getattr(self, "_copied_terminated", False):
            return
        self._copied_terminated = True

        # Get all terminated expressions from G_in
        terminated_pos = self.get_expressions(
            sort_by_depth=True,
            include_terminated=True,
            required_traits=(is_terminated,),
        )

        # Copy each terminated expression to G_out
        for po in terminated_pos:
            self.copy_operand(po.as_parameter_operatable.get())

    def _copy_unmutated_optimized(self):
        # TODO we might have new types in tg_in that haven't been copied over yet
        # but we can't just blindly copy over because tg_out might be modified (pretty
        # likely)
        # with the current way of how the get_copy works, tg_out will get the new types
        # anyway so for now not a huge problem, later when we do smarter node copy we
        # need to handle this

        touched = self.transformations.mutated.keys() | self.transformations.removed

        dirtied = {
            e.get_trait(F.Parameters.is_parameter_operatable)
            for m in self.transformations.mutated.keys()
            # TODO build get_operations in zig for recursive case to be blazing
            for e in m.get_operations(recursive=True)
        } - touched

        all_ops = cast(
            set[F.Parameters.is_parameter_operatable],
            self.get_parameter_operatables(include_terminated=True),
        )
        exprs = cast(
            set[F.Expressions.is_expression],
            self.get_expressions(include_terminated=True),
        )

        clean = all_ops - dirtied - touched
        clean_exprs = clean & exprs
        from faebryk.core.solver.symbolic.structural import _get_congruent_expressions

        # TODO consider doing this also for dirty ones
        full_eq = _get_congruent_expressions(
            cast(list[F.Expressions.is_expression], clean_exprs),
            self.G_transient,
            self.tg_in,
        )
        congruencies = {
            k.get_trait(F.Parameters.is_parameter_operatable): v
            for k, v in full_eq.classes.items()
            if len(v) > 1
        }
        clean_no_congruent = clean - set(congruencies.keys())

        for p in clean_no_congruent:
            self.copy_operand(p)
            # p_copy = p.copy_into(self.G_out)
            # if (
            #    pred := p.try_get_sibling_trait(F.Expressions.is_predicate)
            # ) and pred in self.transformations.terminated:
            #    self.predicate_terminate(
            #        p_copy.get_sibling_trait(F.Expressions.is_predicate)
            #    )
            # self.transformations.mutated[p] = p_copy

        for p in dirtied - touched | set(congruencies.keys()):
            self.copy_operand(p)

        # logger.info(f"Terminated {len(self.transformations.terminated)}")
        # logger.info(f"Touched {len(touched)}")
        # logger.info(f"Dirtied {len(dirtied)}")
        # logger.info(f"All ops {len(all_ops)}")
        # logger.info(f"Clean {len(clean)}")
        # logger.info(f"Congruencies {len(congruencies)}")

        # logger.info("Touched")
        # logger.info(
        #     indented_container(
        #         [
        #             p.compact_repr(self.input_print_context, no_lit_suffix=True)
        #             for p in touched
        #         ]
        #     )
        # )
        # logger.info("Dirtied")
        # logger.info(
        #     indented_container(
        #         [
        #             p.compact_repr(self.input_print_context, no_lit_suffix=True)
        #             for p in dirtied
        #         ]
        #     )
        # )
        # logger.info("All ops")
        # logger.info(
        #     indented_container(
        #         [
        #             p.compact_repr(self.input_print_context, no_lit_suffix=True)
        #             for p in all_ops
        #         ]
        #     )
        # )
        # logger.info("Clean")
        # logger.info(
        #     indented_container(
        #         [
        #             p.compact_repr(self.input_print_context, no_lit_suffix=True)
        #             for p in clean
        #         ]
        #     )
        # )

        # TODO might not need to sort
        # to_copy = F.Expressions.is_expression.sort_by_depth(
        #     (
        #         fabll.Traits(p).get_obj_raw()
        #         for p in (
        #             set(self.get_parameter_operatables(include_terminated=True))
        #             - touched
        #         )
        #     ),
        #     ascending=True,
        # )
        # for p in to_copy:
        #     self.get_copy_po(p.get_trait(F.Parameters.is_parameter_operatable))

        # logger.info("To copy")
        # logger.info(
        #    indented_container(
        #        [
        #            p.get_trait(F.Parameters.is_parameter_operatable).compact_repr(
        #                self.input_print_context, no_lit_suffix=True
        #            )
        #            for p in to_copy
        #        ]
        #    )
        # )

        # TODO optimization: if just new_ops, no need to copy
        # just pass through untouched graphs

    def _copy_unmutated(self):
        touched = self.transformations.mutated.keys() | self.transformations.removed
        to_copy = F.Expressions.is_expression.sort_by_depth(
            (
                fabll.Traits(p).get_obj_raw()
                for p in (
                    set(self.get_parameter_operatables(include_terminated=True))
                    - touched
                )
            ),
            ascending=True,
        )
        for p in to_copy:
            self.copy_operand(p.get_trait(F.Parameters.is_parameter_operatable))

    def check_no_illegal_mutations(self):
        # TODO should only run during dev

        # Check modifications to original graph
        post_mut_nodes = set(self.get_parameter_operatables(include_terminated=True))
        removed = self._starting_operables.difference(
            post_mut_nodes, self.transformations.removed
        )
        added = post_mut_nodes.difference(
            self._starting_operables, self.transformations.created
        )
        removed_compact = (op.compact_repr(self.print_ctx) for op in removed)
        added_compact = (op.compact_repr(self.print_ctx) for op in added)
        assert not removed, (
            f"{self.__repr__(exclude_transformations=True)} untracked removed "
            f"{indented_container(removed_compact)}"
        )
        assert not added, (
            f"{self.__repr__(exclude_transformations=True)} untracked added "
            f"{indented_container(added_compact)}"
        )

        # TODO check created pos in G_out that are not in mutations.created

    def close(self) -> AlgoResult:
        # optimization: if no mutations, return identity stage
        if not self.algo.force_copy and not self.transformations.dirty:
            self.G_transient.destroy()
            self.G_out.destroy()
            return AlgoResult(
                mutation_stage=MutationStage.identity(
                    self.tg_in,
                    self.mutation_map.G_out,
                    algorithm=self.algo,
                    iteration=self.iteration,
                    print_context=self.print_ctx,
                ),
                dirty=False,
            )

        self.check_no_illegal_mutations()
        self._copy_unmutated()
        # important to check after copying unmutated
        # because invariant checking might revert 'new' state
        dirty = self.transformations.dirty
        stage = MutationStage(
            tg_in=self.tg_in,
            tg_out=self.tg_out,
            G_in=self.G_in,
            G_out=self.G_out,
            algorithm=self.algo,
            iteration=self.iteration,
            transformations=self.transformations,
            print_ctx=self.print_ctx,
        )

        self.G_transient.destroy()
        # Check if original graphs ended up in result
        # allowed if no copy was needed for graph
        # TODO

        return AlgoResult(mutation_stage=stage, dirty=dirty)

    def run(self):
        self._run()
        return self.close()

    # Debug Interface ------------------------------------------------------------------
    def __repr__(self, exclude_transformations: bool = False) -> str:
        t = f" | {self.transformations}" if not exclude_transformations else ""
        return (
            f"Mutator("
            f" |G_in|={self.G_in.get_node_count()}"
            f" |G_out|={self.G_out.get_node_count()}"
            f" '{self.algo.name}'{t})"
        )


# TESTS --------------------------------------------------------------------------------


def test_mutator_basic_bootstrap():
    from faebryk.core.solver.algorithm import algorithm

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _App(fabll.Node):
        param_str = F.Parameters.StringParameter.MakeChild()
        param_num = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Dimensionless)
        param_bool = F.Parameters.BooleanParameter.MakeChild()

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)
    param_num_op = app.param_num.get().can_be_operand.get()
    param_bool_op = app.param_bool.get().can_be_operand.get()

    app.param_str.get().set_superset("a", "b", "c")
    app.param_bool.get().set_singleton(True)
    app.param_num.get().set_superset(
        g=g,
        value=F.Literals.Numbers.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup_from_min_max(
            1,
            5,
            unit=F.Units.Dimensionless.bind_typegraph(tg=tg)
            .create_instance(g=g)
            .is_unit.get(),
        ),
    )
    F.Expressions.Add.bind_typegraph(tg=tg).create_instance(g=g).setup(
        param_num_op,
        param_num_op,
    )
    F.Expressions.Or.bind_typegraph(tg=tg).create_instance(g=g).setup(
        param_bool_op,
        param_bool_op,
        assert_=False,
    )

    @algorithm("empty", force_copy=True)
    def algo_empty(mutator: Mutator):
        pass

    @algorithm("test")
    def algo(mutator: Mutator):
        params = mutator.get_parameters()
        assert len(params) >= 3
        exprs = mutator.get_expressions(include_terminated=True)
        assert len(exprs) >= 4
        pos = mutator.get_parameter_operatables()
        assert len(pos) >= 4
        is_exprs = mutator.get_typed_expressions(F.Expressions.Is)
        assert len(is_exprs) == 0
        preds = mutator.get_expressions(required_traits=(F.Expressions.is_predicate,))
        # Canonicalization resolves Or(true, true) -> true and terminated predicates
        # are dropped
        assert len(preds) >= 0

        mutator.create_check_and_insert_expression(
            F.Expressions.Multiply,
            param_num_op,
            param_num_op,
        )
        mutator.create_check_and_insert_expression(
            F.Expressions.Not,
            param_bool_op,
            assert_=False,
        )

    mut_map = MutationMap.bootstrap(tg=tg, g=g)
    mutator0 = Mutator(
        mutation_map=mut_map,
        algo=algo_empty,
        iteration=0,
        terminal=True,
    )
    res0 = mutator0.run()
    mut_map = mut_map.extend(res0.mutation_stage)
    mutator = Mutator(
        mutation_map=mut_map,
        algo=algo,
        iteration=0,
        terminal=True,
    )
    result = mutator.run()
    # TODO next: check that params/exprs copied


def test_mutate_copy_terminated_predicate():
    # TODO move most of this into node.py
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    params = [
        F.Parameters.BooleanParameter.bind_typegraph(tg=tg).create_instance(g=g).setup()
        for _ in range(2)
    ]
    pred = (
        F.Expressions.Is.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup(*[p.can_be_operand.get() for p in params])
    ).is_parameter_operatable.get()

    p_obj = fabll.Traits(pred).get_obj_raw()

    g2 = graph.GraphView.create()
    pred2 = pred.copy_into(g2)

    pred_type = pred.get_type_node()
    pred2_type = pred2.get_type_node()
    assert pred_type is not None
    assert pred2_type is not None
    assert pred_type.node().is_same(other=pred2_type.node())
    assert not fabll.Node.nodes_match(pred_type, pred2_type)

    tg2 = pred2.tg
    assert fabll.Node.graphs_match(tg2.get_self_node().g(), g2)
    assert tg2.get_self_node().node().is_same(other=tg.get_self_node().node())

    pred2_type_built = (
        F.Parameters.is_parameter_operatable.bind_typegraph_from_instance(
            pred2.instance
        ).get_or_create_type()
    )
    assert fabll.Node.nodes_match(pred2_type, pred2_type_built)

    assert pred2.get_sibling_trait(F.Expressions.is_assertable)
    assert not pred2.try_get_sibling_trait(is_terminated)

    p2_obj = fabll.Traits(pred2).get_obj_raw()
    assert p2_obj.instance.node().is_same(other=p_obj.instance.node())

    fabll.Traits.create_and_add_instance_to(p2_obj, is_terminated)
    assert pred2.try_get_sibling_trait(is_terminated)

    g3 = graph.GraphView.create()
    pred3 = pred2.copy_into(g3)
    p3_obj = fabll.Traits(pred3).get_obj_raw()
    tg3 = pred3.tg
    p2_obj.debug_print_tree(
        show_pointers=False, show_operands=False, show_composition=False
    )
    p3_obj.debug_print_tree(
        show_pointers=False, show_operands=False, show_composition=False
    )

    assert fabll.Node.graphs_match(tg3.get_self_node().g(), g3)
    assert pred3.get_sibling_trait(F.Expressions.is_assertable)
    assert pred3.try_get_sibling_trait(is_terminated)


if __name__ == "__main__":
    import typer

    typer.run(test_mutate_copy_terminated_predicate)
