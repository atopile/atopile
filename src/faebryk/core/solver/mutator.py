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

from more_itertools import first, zip_equal
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.logging import scope
from atopile.logging_utils import rich_to_string
from faebryk.core.solver.algorithm import SolverAlgorithm
from faebryk.core.solver.utils import (
    S_LOG,
    SHOW_SS_IS,
    VERBOSE_TABLE,
    MutatorUtils,
)
from faebryk.libs.util import (
    OrderedSet,
    duplicates,
    groupby,
    indented_container,
    invert_dict,
    once,
)

if TYPE_CHECKING:
    from faebryk.core.solver.symbolic.invariants import InsertExpressionResult

logger = logging.getLogger(__name__)
if S_LOG:
    logger.setLevel(logging.DEBUG)


Is = F.Expressions.Is
IsSubset = F.Expressions.IsSubset


class is_monotone(fabll.Node):
    is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()


class is_terminated(fabll.Node):
    """
    Mark expression as terminated.
    Tells algorithms to not further transform the expression.
    Useful for when we already folded it maximally and want to stop processing it.
    """

    is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()


class is_relevant(fabll.Node):
    """
    Explicitly marks op as relevant for solving (default is presumed-relevant, unless
    marked otherwise).

    Conflicts with is_irrelevant.
    """

    is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()
    is_monotone = fabll.Traits.MakeEdge(is_monotone.MakeChild().put_on_type())


class is_irrelevant(fabll.Node):
    """
    Marks op as irrelevant for solving.
    - mutator hides it from queries
    - gets removed at end of iterations

    Used for removing subsumed, but mutated expressions.
    Can also be used for other stuff in the future.
    Conflicts with is_relevant.
    """

    is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()
    is_monotone = fabll.Traits.MakeEdge(is_monotone.MakeChild().put_on_type())


@dataclass
class Transformations:
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

    _no_log: bool = False

    def is_dirty(self) -> bool:
        # Use allow_different_graph=True because mutations go from G_in to G_out
        # We want to detect actual changes, not just graph differences
        non_copy = (
            (k, v)
            for k, v in self.mutated.items()
            if k not in self.copied and not k.is_same(v, allow_different_graph=True)
        )

        created_preds = (
            k
            for k in self.created
            if k.try_get_sibling_trait(F.Expressions.is_predicate)
        )

        if S_LOG and not self._no_log:
            non_copy = list(non_copy)
            if bool(non_copy):
                logger.error(
                    "DIRTY: non_copy"
                    + indented_container(
                        {k.compact_repr(): v.compact_repr() for k, v in non_copy},
                        use_repr=False,
                    )
                )
            if bool(self.removed):
                logger.error(f"DIRTY: removed={len(self.removed)}")
            # Filter created to only include truly new expressions
            # If a "created" expression existed in G_in (was copied), it's not truly new
            created_preds = list(created_preds)
            if created_preds:
                x = indented_container(
                    [k.compact_repr() for k in created_preds], use_repr=False
                )
                logger.error(f"DIRTY: new preds={x}")
            if bool(self.terminated):
                logger.error(f"DIRTY: terminated={len(self.terminated)}")
            if bool(self.asserted):
                logger.error(f"DIRTY: asserted={len(self.asserted)}")

        return bool(
            self.removed
            or next(iter(non_copy), None) is not None
            or next(iter(created_preds), None) is not None
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
    def identity(tg: fbrk.TypeGraph, g: graph.GraphView) -> "Transformations":
        return Transformations(
            mutated={
                po: po
                for po in fabll.Traits.get_implementors(
                    trait=F.Parameters.is_parameter_operatable.bind_typegraph(tg),
                    g=g,
                )
            }
        )

    def __str__(self) -> str:
        self._no_log = True
        if not self.is_dirty():
            self._no_log = False
            return "Transformations()"
        self._no_log = False

        mutated_transformations = [
            (k.compact_repr(), v.compact_repr())
            for k, v in self.mutated.items()
            if k not in self.copied
        ]
        mutated = indented_container(
            [f"{k} -> {v}" for k, v in mutated_transformations if k != v]
            + [f"copy {k}" for k, v in mutated_transformations if k == v],
            use_repr=False,
        )
        created = indented_container(
            [k.compact_repr() for k in self.created], use_repr=False
        )
        removed = indented_container(
            [k.compact_repr() for k in self.removed], use_repr=False
        )
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

        dst_text = self.stage.dst.compact_repr()
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
                src_text = src.compact_repr(use_full_name=True)
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
        transformations: Transformations,
        G_in: graph.GraphView,
        G_out: graph.GraphView,
        _processed_predicate_uuids: set[int] | None = None,
    ):
        self.algorithm = algorithm
        self.iteration = iteration
        self.transformations = transformations
        self.tg_in = tg_in
        self.tg_out = tg_out
        self.G_in = G_in
        self.G_out = G_out
        self._processed_predicate_uuids: set[int] = _processed_predicate_uuids or set()
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
        iteration: int = 0,
        algorithm: str = "identity",
    ) -> "MutationStage":
        return MutationStage(
            tg_in=tg,
            tg_out=tg,
            G_in=g,
            G_out=g,
            algorithm=algorithm,
            iteration=iteration,
            transformations=Transformations.identity(tg, g),
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
            transformations=Transformations.identity(self.tg_out, self.G_out),
        )

    def print_graph_contents(
        self,
        trait_filter: type[fabll.Node] = F.Parameters.is_parameter_operatable,
        log: Callable[[str], None] = logger.debug,
    ):
        MutationStage.print_graph_contents_static(
            self.tg_out, self.G_out, trait_filter=trait_filter, log=log
        )

    @staticmethod
    def print_graph_contents_static(
        tg: fbrk.TypeGraph,
        g: graph.GraphView,
        trait_filter: type[fabll.Node] = F.Parameters.is_parameter_operatable,
        log: Callable[[str], None] = logger.debug,
    ):
        pre_nodes = fabll.Traits.get_implementor_objects(
            trait=trait_filter.bind_typegraph(tg=tg), g=g
        )
        if SHOW_SS_IS:
            nodes = pre_nodes
        else:
            nodes = [
                n
                for n in pre_nodes
                # subset/superset expressions A ss! X or X ss! A
                if not (
                    MutatorUtils.is_set_literal_expression(
                        n.get_trait(F.Parameters.is_parameter_operatable)
                    )
                )
                # parameter assignments
                and not (
                    n.try_cast(F.Expressions.Is)
                    and n.try_get_trait(F.Expressions.is_predicate)
                    and n.get_trait(
                        F.Expressions.is_expression
                    ).get_operands_with_trait(F.Parameters.is_parameter)
                )
            ]

        # note not necessarily used for a flattened expr graph
        nodes = [n for n in nodes if not n.has_trait(is_irrelevant)]
        out = ""
        node_by_depth = groupby(
            nodes,
            key=lambda n: (
                n.get_trait(F.Parameters.is_parameter_operatable).get_depth()
            ),
        )
        for depth, dnodes in sorted(node_by_depth.items(), key=lambda t: t[0]):
            out += f"\n  --Depth {depth}--"
            dnode_reprs = [
                (n, n.get_trait(F.Parameters.is_parameter_operatable).compact_repr())
                for n in dnodes
            ]
            for n, compact_repr in sorted(dnode_reprs, key=lambda t: t[1]):
                out += f"\n      {compact_repr}"
                if VERBOSE_TABLE:
                    out += f" {repr(n)}"

        if not nodes:
            return
        log(f"{g} {len(nodes)}/{len(pre_nodes)} [{out}\n]")

    @staticmethod
    def print_g_in_g_out(
        tg_in: fbrk.TypeGraph,
        g_in: graph.GraphView,
        tg_out: fbrk.TypeGraph,
        g_out: graph.GraphView,
    ) -> Table:
        collected = ""

        def _capture_log(x: str):
            nonlocal collected
            collected += x + "\n"

        t = Table("G_in", "G_out")

        MutationStage.print_graph_contents_static(tg_in, g_in, log=_capture_log)
        g_in_str = Text.from_ansi(collected)
        collected = ""

        MutationStage.print_graph_contents_static(tg_out, g_out, log=_capture_log)
        g_out_str = Text.from_ansi(collected)
        t.add_row(g_in_str, g_out_str)
        return t

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
            try:
                return op.compact_repr()
            except AssertionError:
                # Node may have been removed/orphaned and lost its trait linkages
                obj = op.get_obj()
                return f"<orphaned:{obj.get_full_name(types=True) or 'unknown'}>"

        rows: list[tuple[str, str]] = []

        for op, from_ops in created_ops.items():
            key = "new"
            key_from_ops = " \n  ".join(___repr_op(o) for o in from_ops)
            value = ___repr_op(op)
            if op.has_trait(is_irrelevant):
                continue
            if (op_e := op.as_expression.try_get()) and op_e.try_get_sibling_trait(
                F.Expressions.is_predicate
            ):
                if MutatorUtils.is_set_literal_expression(op):
                    expr = next(iter(op_e.get_operand_operatables()))
                    lits = op_e.get_operand_literals()
                    lit = next(iter(lits.values()))
                    if not SHOW_SS_IS and expr in created_ops:
                        continue
                    alias_type = "superset" if lits.keys() == {1} else "subset"
                    value = f"new {alias_type}\n{lit.pretty_str()}"
                    key = expr.compact_repr(no_lit_suffix=True)
                elif fabll.Traits(op).get_obj_raw().isinstance(F.Expressions.Is):
                    expr = next(
                        iter(op_e.get_operands_with_trait(F.Expressions.is_expression))
                    )
                    param = next(
                        iter(op_e.get_operands_with_trait(F.Parameters.is_parameter))
                    )
                    key = expr.compact_repr(no_class_suffix=True)
                    value = f"new alias\n{param.compact_repr(with_detail=False)}"
            if key_from_ops:
                key = f"{key} from\n  {key_from_ops}"
            rows.append((key, value))

        terminated = self.transformations.terminated.difference(
            co.try_get_sibling_trait(F.Expressions.is_predicate)
            and not co.try_get_sibling_trait(is_irrelevant)
            for co in created_ops
        )
        for op in terminated:
            rows.append(
                (
                    "terminated",
                    ___repr_op(op.as_parameter_operatable.get()),
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

        # Detect relevance changes in mutated operatables
        for s, d in self.transformations.mutated.items():
            s_relevant = s.try_get_sibling_trait(is_relevant) is not None
            d_relevant = d.try_get_sibling_trait(is_relevant) is not None
            s_irrelevant = s.try_get_sibling_trait(is_irrelevant) is not None
            d_irrelevant = d.try_get_sibling_trait(is_irrelevant) is not None

            if not s_relevant and d_relevant:
                rows.append(("→ relevant", ___repr_op(d)))
            if not s_irrelevant and d_irrelevant:
                rows.append(("→ irrelevant", ___repr_op(d)))

        # Detect relevance on created operatables
        for op in created_ops:
            if op.try_get_sibling_trait(is_relevant) is not None:
                rows.append(("→ relevant", ___repr_op(op)))
            if op.try_get_sibling_trait(is_irrelevant) is not None:
                rows.append(("→ irrelevant", ___repr_op(op)))

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
                # Use Text.from_ansi() to parse ANSI color codes so Rich
                # calculates column widths correctly
                row_text = tuple(Text.from_ansi(cell) for cell in row)
                if track_count:
                    table.add_row(count_str, *row_text)
                else:
                    table.add_row(*row_text)

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
            srcs=srcs, dst=dst, reason=reason, related=related, algo=algo
        )


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
                is_removed = chain_end in m.transformations.removed
                is_chain_broken = chain_end is not param
                return MutationMap.LookupResult(removed=is_removed or is_chain_broken)
            chain_end = maps_to
        return MutationMap.LookupResult(maps_to=chain_end)

    def map_backward(
        self, param: F.Parameters.is_parameter_operatable, only_full: bool = True
    ) -> list[F.Parameters.is_parameter_operatable]:
        chain_fronts = [param]
        collected = []

        next_fronts = []
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

    @classmethod
    def _identity(
        cls,
        tg: fbrk.TypeGraph,
        g: graph.GraphView,
        iteration: int = 0,
    ) -> "MutationMap":
        return cls(MutationStage.identity(tg, g, iteration))

    @classmethod
    def _with_relevance_set(
        cls,
        g: graph.GraphView,
        tg: fbrk.TypeGraph,
        relevant: list[F.Parameters.can_be_operand],
        iteration: int = 0,
        initial_state: "MutationMap | None" = None,
    ) -> "MutationMap":
        if invalid_ops := [
            op
            for op in relevant
            if (
                (po := op.as_parameter_operatable.force_get()).as_parameter.try_get()
                is None
                and po.try_get_sibling_trait(F.Expressions.is_predicate) is None
            )
        ]:
            raise ValueError(f"Invalid relevant operable(s): {invalid_ops}")

        relevant_root_predicates = MutatorUtils.get_relevant_predicates(*relevant)
        if S_LOG:
            logger.debug(
                "Relevant root predicates: "
                + indented_container(
                    [
                        p.as_expression.get().compact_repr(
                            no_lit_suffix=True, use_full_name=True
                        )
                        for p in relevant_root_predicates
                    ]
                )
            )

        current_pred_uuids = {
            pred.instance.node().get_uuid() for pred in relevant_root_predicates
        }
        prev_pred_uuids = (
            initial_state.processed_predicate_uuids
            if initial_state is not None
            else set()
        )
        new_pred_uuids = current_pred_uuids - prev_pred_uuids
        removed_pred_uuids = prev_pred_uuids - current_pred_uuids

        if initial_state is not None and not new_pred_uuids and not removed_pred_uuids:
            # no changes
            return initial_state

        if initial_state is None:
            g_out, tg_out = cls._bootstrap_copy(g, tg)
            for pred in relevant_root_predicates:
                pred.copy_into(g_out)
        elif not removed_pred_uuids:
            g_out = initial_state.G_out
            tg_out = initial_state.tg_out
            for pred in relevant_root_predicates:
                if pred.instance.node().get_uuid() in new_pred_uuids:
                    pred.copy_into(g_out)
        else:
            prev_tg_out = initial_state.tg_out
            g_out = graph.GraphView.create()
            tg_out = prev_tg_out.copy_into(target_graph=g_out, minimal=True)
            relevant_op_uuids = {
                op.instance.node().get_uuid()
                for pred in relevant_root_predicates
                for op in pred.as_expression.get().get_operand_operatables()
            }
            relevant_op_uuids |= {p.instance.node().get_uuid() for p in relevant}

            # only relevant solved ops from initial_state
            for op in initial_state.output_operables:
                if op.instance.node().get_uuid() in relevant_op_uuids:
                    op.copy_into(g_out)

            # plus current predicates
            for pred in relevant_root_predicates:
                pred.copy_into(g_out)

        mapping = {
            F.Parameters.is_parameter_operatable.bind_instance(
                g.bind(node=op.instance.node())
            ): op
            for op in F.Parameters.is_parameter_operatable.bind_typegraph(
                tg_out
            ).get_instances(g=g_out)
        }

        if initial_state is not None:
            forwarded_pos = {
                k: F.Parameters.is_parameter_operatable.bind_instance(
                    g_out.bind(node=v.instance.node())
                )
                for k, v in initial_state.compressed_mapping_forwards_complete.items()
                if v.is_in_graph(g_out)
            }
            mapping |= forwarded_pos
        else:
            forwarded_pos = None

        for p_old, p_new in mapping.items():
            if forwarded_pos is not None and p_old in forwarded_pos:
                continue

            if (p_new_p := p_new.as_parameter.try_get()) is not None:
                p_old_p = p_old.as_parameter.force_get()
                if not MutatorUtils.try_copy_trait(
                    g=g_out,
                    from_param=p_old_p,
                    to_param=p_new_p,
                    trait_t=F.has_name_override,
                ):
                    # Preserve the location-based name before it's lost
                    p_old_obj = fabll.Traits(p_old_p).get_obj_raw()
                    p_new_p.set_name(p_old_obj.get_name())

        nodes_uuids = {p.instance.node().get_uuid() for p in relevant}

        for p_out in (
            p
            for p in fabll.Traits.get_implementors(
                F.Parameters.can_be_operand.bind_typegraph(tg_out)
            )
            if p.instance.node().get_uuid() in nodes_uuids
            and not p.try_get_sibling_trait(is_relevant)
        ):
            fabll.Traits.create_and_add_instance_to(p_out.get_obj_raw(), is_relevant)

        if S_LOG:
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

        return MutationMap(
            MutationStage(
                tg_in=tg,
                tg_out=tg_out,
                algorithm="bootstrap_relevant_preds",
                iteration=iteration,
                transformations=Transformations(mutated=mapping),
                G_in=g,
                G_out=g_out,
                _processed_predicate_uuids=current_pred_uuids,
            )
        )

    @staticmethod
    def bootstrap(
        tg: fbrk.TypeGraph,
        g: graph.GraphView,
        iteration: int = 0,
        relevant: list[F.Parameters.can_be_operand] | None = None,
        initial_state: "MutationMap | None" = None,
    ) -> "MutationMap":
        from faebryk.core.solver.symbolic.canonical import (
            convert_to_canonical_operations,
            flatten_expressions,
        )

        mut_map = (
            MutationMap._with_relevance_set(g, tg, relevant, iteration, initial_state)
            if relevant
            else MutationMap._identity(tg, g, iteration)
        )

        if S_LOG:
            mut_map.last_stage.print_graph_contents()

        for algo in (
            flatten_expressions,
            convert_to_canonical_operations,
        ):
            log_scope = scope()
            if S_LOG:
                logger.debug(f"Bootstrap {algo.name}")
                log_scope.__enter__()
            mutator = Mutator(
                mut_map,
                algo,
                iteration=0,
                terminal=False,
            )
            try:
                algo_result = mutator.run()
            except:
                if S_LOG:
                    logger.error(f"Error running algorithm {algo.name}")
                    mutator.print_current_state(log=logger.error)
                raise

            mut_map = mut_map.extend(algo_result.mutation_stage)

        logger.debug("Done bootstrap ------")

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
    def processed_predicate_uuids(self) -> set[int]:
        return set.union(
            *(stage._processed_predicate_uuids for stage in self.mutation_stages)
        )

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

    def compressed(self) -> "MutationMap":
        """
        Returns a copy of the mutation map compressed to only input and output stages.
        """
        if len(self.mutation_stages) == 1:
            return MutationMap(self.mutation_stages[0])

        forwards_mapping = self.compressed_mapping_forwards_complete
        removed = self.input_operables - set(forwards_mapping.keys())
        created = {
            out_op: in_ops
            for out_op, in_ops in self.compressed_mapping_backwards.items()
            if not any(op for op in in_ops if op in self.input_operables)
        }

        return MutationMap(
            MutationStage(
                tg_in=self.tg_in,
                tg_out=self.tg_out,
                G_in=self.G_in,
                G_out=self.G_out,
                algorithm="compressed",
                iteration=0,
                transformations=Transformations(
                    mutated=forwards_mapping,
                    removed=OrderedSet(removed),
                    created=created,
                ),
                _processed_predicate_uuids=self.processed_predicate_uuids,
            )
        )


@dataclass
class AlgoResult:
    mutation_stage: MutationStage
    dirty: bool


_EXPRESSION_BUILDER_TRAIT_ALLOWLIST: list[type[fabll.NodeT]] = [
    F.has_name_override,
    is_relevant,
    is_irrelevant,
]


class ExpressionBuilder[
    T: F.Expressions.ExpressionNodes = F.Expressions.ExpressionNodes
](NamedTuple):
    factory: type[T]
    operands: list[F.Parameters.can_be_operand]
    assert_: bool
    terminate: bool
    traits: list[fabll.NodeT | None]
    # TODO make non-default
    # TODO consider including in matches
    irrelevant: bool = False

    @classmethod
    def from_e(cls, e: F.Expressions.is_expression) -> "ExpressionBuilder[T]":
        return cls(
            factory=MutatorUtils.hack_get_expr_type(e),  # pyright: ignore[reportArgumentType]
            operands=e.get_operands(),
            assert_=bool(e.try_get_sibling_trait(F.Expressions.is_predicate)),
            terminate=bool(e.try_get_sibling_trait(is_terminated)),
            traits=[
                t
                for trait_t in _EXPRESSION_BUILDER_TRAIT_ALLOWLIST
                if trait_t is not None
                and (t := e.try_get_sibling_trait(trait_t)) is not None
            ],
            irrelevant=bool(e.try_get_sibling_trait(is_irrelevant)),
        )

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
        return self.compact_repr()

    def __str__(self) -> str:
        traits = ", ".join(
            [str(t.get_type_name()) for t in self.traits if t is not None]
        )
        return (
            f"ExpressionBuilder({self.factory.__name__}, {self.operands},"
            f" {self.assert_}, {self.terminate}, traits=[{traits}])"
        )

    def matches(
        self,
        other: F.Expressions.is_expression,
        allow_different_graph: bool,
        mutator: "Mutator",
    ) -> bool:
        def _operand_matches(
            x1: F.Parameters.can_be_operand, x2: F.Parameters.can_be_operand
        ) -> bool:
            same = x1.is_same(x2, allow_different_graph=allow_different_graph)
            if same:
                return True
            if (
                allow_different_graph
                and not x1.is_in_graph(x2.g)
                and (x1_po := x1.as_parameter_operatable.try_get())
                and (x2_po := x2.as_parameter_operatable.try_get())
            ):
                if not mutator.has_been_mutated(x1_po) or not mutator.has_been_mutated(
                    x2_po
                ):
                    return False
                x1_po = mutator.get_mutated(x1_po)
                x2_po = mutator.get_mutated(x2_po)
                return x1_po.is_same(x2_po, allow_different_graph=allow_different_graph)
            return False

        same_type = fabll.Traits(other).get_obj_raw().isinstance(self.factory)
        same_operands = len(self.operands) == len(
            other_ops := other.get_operands()
        ) and all(
            _operand_matches(x1, x2) for x1, x2 in zip_equal(self.operands, other_ops)
        )
        same_terminate = self.terminate == bool(
            other.try_get_sibling_trait(is_terminated)
        )
        same_assert = self.assert_ == bool(
            other.try_get_sibling_trait(F.Expressions.is_predicate)
        )
        return same_type and same_operands and same_terminate and same_assert

    def is_alias(self) -> bool:
        return self.factory is F.Expressions.Is and self.assert_

    # TODO use this more
    def with_(
        self,
        factory: type[T] | None = None,
        operands: list[F.Parameters.can_be_operand] | None = None,
        assert_: bool | None = None,
        terminate: bool | None = None,
        traits: list[fabll.NodeT | None] | None = None,
        irrelevant: bool | None = None,
    ) -> "ExpressionBuilder[T]":
        return ExpressionBuilder(
            factory=factory or self.factory,
            operands=operands if operands is not None else self.operands,
            assert_=assert_ if assert_ is not None else self.assert_,
            terminate=terminate if terminate is not None else self.terminate,
            traits=traits if traits is not None else self.traits,
            irrelevant=irrelevant if irrelevant is not None else self.irrelevant,
        )

    def __rich_repr__(self):
        yield self.compact_repr()

    def compact_repr(
        self,
        use_full_name: bool = False,
        no_lit_suffix: bool = False,
        no_class_suffix: bool = False,
    ) -> str:
        if self.operands:
            tg = self.operands[0].tg
        else:
            g = graph.GraphView.create()
            tg = fbrk.TypeGraph.create(g=g)

        factory_type = fabll.TypeNodeBoundTG(tg, self.factory)
        is_expr_type = factory_type.try_get_type_trait(F.Expressions.is_expression_type)
        if is_expr_type is None:
            raise ValueError(f"Factory {self.factory} has no is_expression_type trait")
        repr_style = is_expr_type.get_repr_style()

        return F.Expressions.is_expression._compact_repr(
            style=repr_style,
            symbol=repr_style.symbol
            if repr_style.symbol is not None
            else self.factory.__name__,
            is_predicate=bool(self.assert_),
            is_terminated=bool(self.terminate),
            lit_suffix="",
            class_suffix="",
            use_full_name=use_full_name,
            expr_name=self.factory.__name__,
            operands=self.operands or [],
            no_lit_suffix=no_lit_suffix,
            no_class_suffix=no_class_suffix,
        )


class Mutator:
    # Algorithm Interface --------------------------------------------------------------
    @overload
    def make_singleton(self, value: bool) -> F.Literals.Booleans: ...  # pyright: ignore[reportOverlappingOverload]

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

        new_param_p = new_param.as_parameter.force_get()
        if (
            MutatorUtils.try_copy_trait(
                self.G_out, param, new_param_p, F.has_name_override
            )
            is None
        ):
            # Preserve the location-based name before it's lost
            new_param_p.set_name(param_obj.get_name())

        for trait_t in [is_relevant, is_irrelevant]:
            MutatorUtils.try_copy_trait(self.G_out, param, new_param_p, trait_t)

        return self._mutate(
            p_po,
            new_param,
        ).as_parameter.force_get()

    def _create_and_insert_expression[T: F.Expressions.ExpressionNodes](
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
        expr_factory, operands, assert_, terminate, traits, irrelevant = builder

        # check canonical
        # only after canonicalize has run
        if self.iteration > 0:
            expr_bound = expr_factory.bind_typegraph(self.tg_out)
            assert expr_bound.check_if_instance_of_type_has_trait(
                F.Expressions.is_canonical
            )

        # map operands to mutated
        assert all(op.is_in_graph(self.G_out) for op in operands)

        new_expr = (
            expr_factory.bind_typegraph(self.tg_out)
            .create_instance(self.G_out)
            .setup(*operands)  # type: ignore # TODO stupid pyright
        )
        new_expr_e = new_expr.is_expression.get()

        if assert_:
            ce = new_expr.get_trait(F.Expressions.is_assertable)
            self.assert_(ce, terminate=False, track=False)

        if terminate:
            self.terminate(new_expr_e)

        if irrelevant:
            self.mark_irrelevant(new_expr.is_parameter_operatable.get())

        for trait in traits:
            if trait is not None:
                fabll.Traits.add_instance_to(
                    node=new_expr, trait_instance=trait.copy_into(self.G_out)
                )

        from faebryk.core.solver.symbolic.invariants import I_LOG

        if I_LOG:
            logger.debug(f"Inserted expression: {new_expr_e.compact_repr()}")

        op_graphs = {op.g.get_self_node().node().get_uuid(): op.g for op in operands}
        assert not op_graphs or set(op_graphs.keys()) == {
            self.G_out.get_self_node().node().get_uuid()
        }, f"Graph mismatch: {op_graphs} != {self.G_out}"

        return cast(T, new_expr)

    def create_check_and_insert_expression_from_builder(
        self,
        builder: ExpressionBuilder,
        from_ops: Sequence[F.Parameters.is_parameter_operatable] | None = None,
        allow_uncorrelated_congruence_match: bool = False,
    ) -> "InsertExpressionResult":
        # NOTE: no point in checking congruence against old G to detect dirty
        # because during copy_unmutated we will copy the potentially existing congruent
        # expression, which will trigger the override mechanism.
        # We can consider in the future to add a shortcut for performance reasons.

        import faebryk.core.solver.symbolic.invariants as invariants

        from_ops = list(set(from_ops or []))
        s = scope()
        if S_LOG:
            logger.debug(f"Create expression from builder: {builder.compact_repr()}")
            s.__enter__()

        res = invariants.wrap_insert_expression(
            self,
            builder,
            alias=None,
            allow_uncorrelated_congruence_match=allow_uncorrelated_congruence_match,
            expr_already_exists_in_old_graph=False,
        )

        if (
            res.is_new
            and res.out is not None
            and not res.out.try_get_sibling_trait(is_irrelevant)
        ):
            res_po = res.out.as_parameter_operatable.get()
            if S_LOG:
                logger.error(f"Mark new expr: {res_po.compact_repr()}")
            # This might get reverted later on by an old congruent expression
            # so totally fine to be eager with marking this as new.
            self.transformations.created[res_po] = from_ops

        if S_LOG:
            s.__exit__(None, None, None)

        return res

    def create_check_and_insert_expression(
        self,
        expr_factory: type[F.Expressions.ExpressionNodes],
        *operands: F.Parameters.can_be_operand,
        from_ops: Sequence[F.Parameters.is_parameter_operatable] | None = None,
        assert_: bool = False,
        terminate: bool = False,
        traits: list[fabll.NodeT | None] | None = None,
        allow_uncorrelated_congruence_match: bool = False,
    ) -> "InsertExpressionResult":
        return self.create_check_and_insert_expression_from_builder(
            ExpressionBuilder(
                expr_factory,
                list(operands),
                assert_=assert_,
                terminate=terminate,
                traits=traits if traits is not None else [],
            ),
            from_ops=from_ops,
            allow_uncorrelated_congruence_match=allow_uncorrelated_congruence_match,
        )

    def mutate_expression(
        self,
        expr: F.Expressions.is_expression,
        operands: Iterable[F.Parameters.can_be_operand] | None = None,
        expression_factory: type[F.Expressions.ExpressionNodes] | None = None,
        traits: list[fabll.NodeT | None] | None = None,
    ) -> F.Parameters.can_be_operand:
        import faebryk.core.solver.symbolic.invariants as invariants

        expr_po = expr.as_parameter_operatable.get()
        # if mutated
        if expr_po in self.transformations.mutated:
            return self.get_mutated(expr_po).as_operand.get()

        assert_ = bool(expr.try_get_sibling_trait(F.Expressions.is_predicate))
        # aliases should be copied manually
        # TODO currently trying disabling, because want to congruence match
        # if expression_factory is F.Expressions.Is and assert_:
        #     return self.make_singleton(True).can_be_operand.get()

        e_operands = expr.get_operands()
        operands = operands or e_operands

        builder = ExpressionBuilder.from_e(expr).with_(
            factory=expression_factory if expression_factory is not None else None,
            operands=list(operands),
            assert_=assert_,
            terminate=self.is_terminated(expr),
            traits=traits if traits is not None else [],
        )

        expr_obj = fabll.Traits(expr).get_obj_raw()
        copy_only = (
            expr_obj.isinstance(builder.factory) and operands == expr.get_operands()
        )

        # predicates don't have aliases
        if assert_:
            alias_p = None
        else:
            alias_p = (
                invariants.AliasClass.of(expr.as_operand.get())
                .representative()
                .as_parameter_operatable.force_get()
                .as_parameter.force_get()
            )

        s = scope()
        if S_LOG:
            logger.debug(
                f"Try mutate `{expr.compact_repr()}` with builder"
                f" `{builder.compact_repr()}`"
            )
            s.__enter__()

        res = invariants.wrap_insert_expression(
            self,
            builder,
            alias_p,
            expr_already_exists_in_old_graph=copy_only,
            allow_uncorrelated_congruence_match=False,
        )

        new_expr_e = res.out
        if new_expr_e is None:
            if S_LOG:
                s.__exit__(None, None, None)
                logger.debug("Dropped and replaced with True")
        if (new_expr_e := res.out) is None:
            return self.make_singleton(True).can_be_operand.get()

        assert not self.has_been_mutated(expr_po), (
            "Expression was mutated during wrap_insert_expression"
        )
        # TODO i dont see why this would happen
        # Re-check if mutated during wrap_insert_expression (via _ss_lits_available)
        # if self.has_been_mutated(expr_po):
        #     return self.get_mutated(expr_po).as_operand.get()

        new_expr_po = new_expr_e.as_parameter_operatable.get()
        self._mutate(expr_po, new_expr_po)

        # copy detection
        if operands == e_operands and builder.matches(
            new_expr_e, allow_different_graph=True, mutator=self
        ):
            self.transformations.copied.add(expr_po)

        if S_LOG:
            s.__exit__(None, None, None)
        return new_expr_e.as_operand.get()

    def get_copy(
        self,
        obj: F.Parameters.can_be_operand,
    ) -> F.Parameters.can_be_operand:
        if obj.is_in_graph(self.G_out):
            return obj
        if obj_po := obj.as_parameter_operatable.try_get():
            if self.has_been_mutated(obj_po):
                return self.get_mutated(obj_po).as_operand.get()
            if obj_e := obj_po.as_expression.try_get():
                return self.mutate_expression(obj_e)
            if obj_p := obj_po.as_parameter.try_get():
                return self.mutate_parameter(obj_p).as_operand.get()
            assert False, "Unreachable"
        if obj_lit := obj.as_literal.try_get():
            self.tg_out
            return obj_lit.copy_into(self.G_out).as_operand.get()
        raise ValueError(f"Cannot copy {obj}")

    def get_operand_copy(
        self,
        obj: F.Parameters.can_be_operand,
    ) -> F.Parameters.can_be_operand:
        if obj.is_in_graph(self.G_out):
            return obj
        if obj_lit := obj.as_literal.try_get():
            self.tg_out
            return obj_lit.copy_into(self.G_out).as_operand.get()
        if obj_po := obj.as_parameter_operatable.try_get():
            if m := self.try_get_mutated(obj_po):
                return m.as_operand.get()

            # If the expression was removed, we can't copy it
            assert not self.is_removed(obj_po), (
                f"Cannot copy removed operand: {obj_po.compact_repr()}"
            )

            if obj_e := obj_po.as_expression.try_get():
                # TODO not sure about this
                # only alias is allowed exprs, but alias should get manual copy
                assert False, f"Expressions should never be operands in solver {obj_e}"
                return self.mutate_expression(obj_e)
            obj_p = obj_po.as_parameter.force_get()

            return self.mutate_parameter(obj_p).as_operand.get()

        assert False, "Unreachable"

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

    def mark_relevant(self, po: F.Parameters.is_parameter_operatable):
        assert not po.try_get_sibling_trait(is_irrelevant)

        if po.try_get_sibling_trait(is_relevant) is not None:
            return

        fabll.Traits.create_and_add_instance_to(
            fabll.Traits(po).get_obj_raw(), is_relevant
        )

    def mark_irrelevant(self, po: F.Parameters.is_parameter_operatable):
        if po in self.transformations.removed:
            raise ValueError(f"Cannot mark removed operatable as irrelevant: {po}")
        if po in self.transformations.mutated:
            raise ValueError(f"Cannot mark mutated operatable as irrelevant: {po}")

        if po.try_get_sibling_trait(is_irrelevant) is not None:
            return
        fabll.Traits.create_and_add_instance_to(
            fabll.Traits(po).get_obj_raw(), is_irrelevant
        )

    def mark_relevance(self):
        """
        Compute and mark relevant and irrelevant operatables with is_relevant and
        is_irrelevant traits, to enable mark-and-sweep removal of irrelevant
        operatables.

        Inclusion or descent from the originally-provided set of relevant parameters
        determines definite relevance (marked with is_relevant and carried forward
        through iterations).

        Potential relevance (not marked) is determined by inclusion in the graph
        component defined by the transitive closure through predicates from the
        known-relevant operatables.

        Anything outside of these categories is definitely irrelevant (marked with
        is_irrelevant).

        Called at start of each iteration, and after each algorithm that results in
        graph mutations.
        """
        current_relevant = [
            op
            for op in fabll.Traits.get_implementor_siblings(
                is_relevant.bind_typegraph(self.tg_in),
                F.Parameters.can_be_operand,
                self.G_in,
            )
        ]

        if not current_relevant:
            return

        maybe_relevant_predicates = MutatorUtils.get_relevant_predicates(
            *current_relevant
        )

        maybe_relevant_pos = (
            # known relevant parameters
            {op.as_parameter_operatable.force_get() for op in current_relevant}
            # relevant predicates
            | {
                pred.as_expression.get().as_parameter_operatable.get()
                for pred in maybe_relevant_predicates
            }
            # operands of relevant predicates
            | {
                po
                for pred in maybe_relevant_predicates
                for po in pred.as_expression.get().get_operands_with_trait(
                    F.Parameters.is_parameter_operatable, recursive=True
                )
            }
        )

        irrelevant_pos = (
            self.get_parameter_operatables(include_terminated=True) - maybe_relevant_pos
        )

        if S_LOG:
            logger.debug(
                f"Marking {len(list(current_relevant))} relevant operatables, "
                f"{len(irrelevant_pos)} irrelevant operatables"
            )

        for po in current_relevant:
            assert po.try_get_sibling_trait(is_irrelevant) is None, (
                f"Relevant operatable is irrelevant: {po}"
            )

            if po.try_get_sibling_trait(is_relevant) is None:
                fabll.Traits.create_and_add_instance_to(
                    fabll.Traits(po).get_obj_raw(), is_relevant
                )

        for po in irrelevant_pos:
            assert po.try_get_sibling_trait(is_relevant) is None, (
                f"Irrelevant operatable is relevant: {po}"
            )

            if po.try_get_sibling_trait(is_irrelevant) is None:
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
        self, include_terminated: bool = False, include_irrelevant: bool = False
    ) -> OrderedSet[F.Parameters.is_parameter_operatable]:
        out = OrderedSet(
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

        if not include_irrelevant:
            irrelevant = fabll.Traits.get_implementor_siblings(
                is_irrelevant.bind_typegraph(self.tg_in),
                F.Parameters.is_parameter_operatable,
                self.G_in,
            )
            out.difference_update(irrelevant)

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
        created_only: bool = False,
        include_terminated: bool = False,
        include_irrelevant: bool = False,
        required_traits: tuple[type[fabll.NodeT], ...] = (),
        require_literals: bool = False,
        require_non_literals: bool = False,
        include_removed: bool = False,
        include_mutated: bool = False,
    ) -> list[T] | OrderedSet[T]:
        if created_only:
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

        if not include_irrelevant:
            irrelevant = fabll.Traits.get_implementor_objects(
                is_irrelevant.bind_typegraph(self.tg_in),
                self.G_in,
            )
            out.difference_update(irrelevant)

        if required_traits and not (t is fabll.Node and len(required_traits) == 1):
            out = OrderedSet(
                o for o in out if all(o.has_trait(t) for t in required_traits)
            )

        # TODO use this more often in algos
        if require_literals or require_non_literals:
            out = OrderedSet(
                e
                for e in out
                if (ops := (e.get_trait(F.Expressions.is_expression)).get_operands())
                and (
                    (
                        lits := (
                            [
                                lit
                                for op in ops
                                if (
                                    lit := op.try_get_sibling_trait(
                                        F.Literals.is_literal
                                    )
                                )
                            ]
                        )
                    )
                    or not require_literals
                )
                and (not require_non_literals or len(lits) < len(ops))
            )

        if not include_removed:
            # Convert removed traits to objects for comparison
            removed_objs = {
                fabll.Traits(po).get_obj_raw() for po in self.transformations.removed
            }
            out.difference_update(removed_objs)
        if not include_mutated:
            # Convert mutated traits to objects for comparison
            mutated_objs = {
                fabll.Traits(po).get_obj_raw()
                for po in self.transformations.mutated.keys()
            }
            out.difference_update(mutated_objs)

        return out

    def get_expressions(
        self,
        created_only: bool = False,
        include_terminated: bool = False,
        required_traits: tuple[type[fabll.NodeT], ...] = (),
    ) -> OrderedSet[F.Expressions.is_expression] | list[F.Expressions.is_expression]:
        # TODO make this first class instead of calling
        typed = self.get_typed_expressions(
            t=fabll.Node,
            created_only=created_only,
            include_terminated=include_terminated,
            required_traits=required_traits,
        )
        t = OrderedSet if isinstance(typed, OrderedSet) else list
        return t(e.get_trait(F.Expressions.is_expression) for e in typed)

    def is_removed(self, po: F.Parameters.is_parameter_operatable) -> bool:
        return po in self.transformations.removed

    def has_been_mutated(self, po: F.Parameters.is_parameter_operatable) -> bool:
        return po in self.transformations.mutated or po.is_in_graph(self.G_out)

    def get_mutated(
        self, po: F.Parameters.is_parameter_operatable
    ) -> F.Parameters.is_parameter_operatable:
        if po.is_in_graph(self.G_out):
            return po
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

        self._mutations_since_last_iteration = mutation_map.get_iteration_mutation(algo)

        self._starting_operables = self.get_parameter_operatables(
            include_terminated=True, include_irrelevant=True
        )

        self.transformations = Transformations()

    @property
    @once
    def tg_out(self) -> fbrk.TypeGraph:
        return self.tg_in.copy_into(target_graph=self.G_out, minimal=False)

    def _run(self, mark_relevance: bool):
        if mark_relevance:
            self.mark_relevance()

        self.algo(self)

    def _copy_unmutated(self):
        touched = self.transformations.mutated.keys() | self.transformations.removed
        presumed_relevant_pos = self.get_parameter_operatables(
            include_terminated=True,
            include_irrelevant=False,
        )
        to_copy = presumed_relevant_pos - touched

        for p in [fabll.Traits(p).get_obj_raw() for p in to_copy]:
            self.get_copy(p.get_trait(F.Parameters.can_be_operand))

    def check_no_illegal_mutations(self):
        # TODO should only run during dev

        # Check modifications to original graph
        post_mut_nodes = self.get_parameter_operatables(
            include_terminated=True, include_irrelevant=True
        )

        removed = self._starting_operables.difference(
            post_mut_nodes, self.transformations.removed
        )
        added = post_mut_nodes.difference(
            self._starting_operables, self.transformations.created
        )
        removed_compact = (op.compact_repr() for op in removed)
        added_compact = (op.compact_repr() for op in added)
        assert not removed, (
            f"{self.__repr__(exclude_transformations=True)} untracked removed "
            f"{indented_container(removed_compact)}"
        )
        assert not added, (
            f"{self.__repr__(exclude_transformations=True)} untracked added "
            f"{indented_container(added_compact)}"
        )

        for po in post_mut_nodes:
            if po.try_get_sibling_trait(is_irrelevant) is not None:
                assert po not in self.transformations.mutated, (
                    f"{self.__repr__(exclude_transformations=True)} "
                    f"mutated & irrelevant: {po.compact_repr()}"
                )

        # TODO check created pos in G_out that are not in mutations.created

    def close(self) -> AlgoResult:
        # optimization: if no mutations, return identity stage
        if not self.algo.force_copy and not self.transformations.is_dirty():
            self.G_transient.destroy()
            self.G_out.destroy()
            return AlgoResult(
                mutation_stage=MutationStage.identity(
                    self.tg_in, self.mutation_map.G_out, self.iteration
                ),
                dirty=False,
            )

        self.check_no_illegal_mutations()
        if S_LOG:
            logger.debug("Copying unmutated")
            # TODO remove log
            MutationStage.print_graph_contents_static(
                self.tg_out, self.G_out, log=logger.debug
            )
        self._copy_unmutated()
        self.G_transient.destroy()

        # important to check after copying unmutated
        # because invariant checking might revert 'new' state
        dirty = self.transformations.is_dirty()
        if not self.algo.force_copy and not dirty:
            self.G_out.destroy()
            return AlgoResult(
                mutation_stage=MutationStage.identity(
                    self.tg_in,
                    self.mutation_map.G_out,
                    algorithm=self.algo.name,
                    iteration=self.iteration,
                ),
                dirty=False,
            )

        stage = MutationStage(
            tg_in=self.tg_in,
            tg_out=self.tg_out,
            G_in=self.G_in,
            G_out=self.G_out,
            algorithm=self.algo,
            iteration=self.iteration,
            transformations=self.transformations,
        )

        if S_LOG:
            logger.debug(f"Dirty after {self.algo.name}")
            stage.print_mutation_table()
            self.print_current_state(log=logger.debug)

        return AlgoResult(mutation_stage=stage, dirty=dirty)

    def run(self, mark_relevance: bool = False):
        self._run(mark_relevance=mark_relevance)
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

    def print_current_state(self, log: Callable[[Any], None] = logger.debug):
        log(Text.from_ansi(str(self.transformations)))
        t = MutationStage.print_g_in_g_out(
            self.tg_in, self.G_in, self.tg_out, self.G_out
        )
        log(rich_to_string(t))


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
    mutator.run()
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


def test_mutation_map_compressed_single_stage():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    mut_map = MutationMap.bootstrap(tg=tg, g=g)
    compressed = mut_map.compressed()

    assert len(compressed.mutation_stages) == 1
    assert (
        compressed.G_in.get_self_node().node().get_uuid()
        == mut_map.G_in.get_self_node().node().get_uuid()
    )
    assert (
        compressed.G_out.get_self_node().node().get_uuid()
        == mut_map.G_out.get_self_node().node().get_uuid()
    )


def test_mutation_map_compressed_with_creations():
    from faebryk.core.solver.algorithm import algorithm

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _AppCreations(fabll.Node):
        param_a = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Dimensionless)
        param_b = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Dimensionless)

    app = _AppCreations.bind_typegraph(tg=tg).create_instance(g=g)
    param_a_op = app.param_a.get().can_be_operand.get()
    param_b_op = app.param_b.get().can_be_operand.get()
    param_a_po = app.param_a.get().is_parameter_operatable.get()

    @algorithm("create_exprs", force_copy=True)
    def algo_create(mutator: Mutator):
        mutator.create_check_and_insert_expression(
            F.Expressions.Add,
            param_a_op,
            param_b_op,
            from_ops=[param_a_po],
        )
        mutator.create_check_and_insert_expression(
            F.Expressions.Multiply,
            param_a_op,
            param_b_op,
            from_ops=[param_a_po],
        )

    mut_map = MutationMap.bootstrap(tg=tg, g=g)
    input_count = len(mut_map.input_operables)

    result = Mutator(mut_map, algo_create, iteration=0, terminal=False).run()
    mut_map = mut_map.extend(result.mutation_stage)

    assert len(mut_map.output_operables) > input_count

    compressed = mut_map.compressed()

    assert len(compressed.mutation_stages) == 1
    assert len(compressed.output_operables) == len(mut_map.output_operables)

    for inp in mut_map.input_operables:
        orig = mut_map.map_forward(inp)
        comp = compressed.map_forward(inp)
        assert (orig.maps_to is None) == (comp.maps_to is None)
        if orig.maps_to and comp.maps_to:
            assert orig.maps_to.is_same(comp.maps_to)


def test_mutation_map_compressed_with_mutations():
    from faebryk.core.solver.algorithm import algorithm

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _AppMutations(fabll.Node):
        param_a = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Dimensionless)
        param_b = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Dimensionless)

    app = _AppMutations.bind_typegraph(tg=tg).create_instance(g=g)
    param_a_op = app.param_a.get().can_be_operand.get()
    param_b_op = app.param_b.get().can_be_operand.get()

    add_expr = (
        F.Expressions.Add.bind_typegraph(tg)
        .create_instance(g)
        .setup(param_a_op, param_b_op)
    )
    add_expr_po = add_expr.is_parameter_operatable.get()

    @algorithm("mutate_expr", force_copy=True)
    def algo_mutate(mutator: Mutator):
        mutator.mutate_expression(
            add_expr.is_expression.get(),
            operands=[param_a_op, param_a_op],
        )

    mut_map = MutationMap.bootstrap(tg=tg, g=g)

    result = Mutator(mut_map, algo_mutate, iteration=0, terminal=False).run()
    mut_map = mut_map.extend(result.mutation_stage)

    orig_forward = mut_map.map_forward(add_expr_po)
    assert orig_forward.maps_to is not None
    assert not orig_forward.removed

    compressed = mut_map.compressed()

    comp_forward = compressed.map_forward(add_expr_po)
    assert comp_forward.maps_to is not None
    assert orig_forward.maps_to.is_same(comp_forward.maps_to)

    orig_back = mut_map.map_backward(orig_forward.maps_to)
    comp_back = compressed.map_backward(comp_forward.maps_to)
    orig_uuids = {op.instance.node().get_uuid() for op in orig_back}
    comp_uuids = {op.instance.node().get_uuid() for op in comp_back}
    assert orig_uuids == comp_uuids


def test_mutation_map_compressed_with_removals():
    from faebryk.core.solver.algorithm import algorithm

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _AppRemovals(fabll.Node):
        param = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Dimensionless)

    app = _AppRemovals.bind_typegraph(tg=tg).create_instance(g=g)
    param_op = app.param.get().can_be_operand.get()

    add_expr = (
        F.Expressions.Add.bind_typegraph(tg)
        .create_instance(g)
        .setup(param_op, param_op)
    )
    add_expr_po = add_expr.is_parameter_operatable.get()

    mut_map = MutationMap.bootstrap(tg=tg, g=g)

    # Find the Add expression in the bootstrapped graph
    add_expr_mapped = mut_map.map_forward(add_expr_po).maps_to
    assert add_expr_mapped is not None

    @algorithm("remove_expr", force_copy=True)
    def algo_remove(mutator: Mutator):
        mutator.remove(add_expr_mapped, no_check_roots=True)

    result = Mutator(mut_map, algo_remove, iteration=0, terminal=False).run()
    mut_map = mut_map.extend(result.mutation_stage)

    # After removal, using the ORIGINAL operable should show removed=True
    # (because the chain was broken after the first stage)
    orig_forward = mut_map.map_forward(add_expr_po)
    assert orig_forward.removed

    compressed = mut_map.compressed()

    # The original operable should also be removed in compressed
    comp_forward = compressed.map_forward(add_expr_po)
    assert comp_forward.removed


def test_mutation_map_compressed_combined():
    """
    Comprehensive test: creations, mutations, AND removals across multiple stages.
    """
    from faebryk.core.solver.algorithm import algorithm

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _AppCombined(fabll.Node):
        param_a = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Dimensionless)
        param_b = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Dimensionless)

    app = _AppCombined.bind_typegraph(tg=tg).create_instance(g=g)
    param_a_op = app.param_a.get().can_be_operand.get()
    param_b_op = app.param_b.get().can_be_operand.get()
    param_a_po = app.param_a.get().is_parameter_operatable.get()
    param_b_po = app.param_b.get().is_parameter_operatable.get()

    add_expr = (
        F.Expressions.Add.bind_typegraph(tg)
        .create_instance(g)
        .setup(param_a_op, param_b_op)
    )
    add_expr_po = add_expr.is_parameter_operatable.get()

    mut_map = MutationMap.bootstrap(tg=tg, g=g)

    # Get mapped references from bootstrapped graph
    add_expr_mapped = mut_map.map_forward(add_expr_po).maps_to
    assert add_expr_mapped is not None
    add_expr_mapped_expr = add_expr_mapped.as_expression.force_get()

    mutated_add_po: F.Parameters.is_parameter_operatable | None = None

    @algorithm("stage1_create_and_mutate", force_copy=True)
    def algo_stage1(mutator: Mutator):
        nonlocal mutated_add_po
        mutator.create_check_and_insert_expression(
            F.Expressions.Multiply,
            param_a_op,
            param_b_op,
            from_ops=[param_a_po],
        )
        mutated = mutator.mutate_expression(
            add_expr_mapped_expr,
            operands=[param_a_op, param_a_op],
        )
        mutated_add_po = mutated.as_parameter_operatable.force_get()

    @algorithm("stage2_remove_and_create", force_copy=True)
    def algo_stage2(mutator: Mutator):
        assert mutated_add_po is not None
        mutator.remove(mutated_add_po, no_check_roots=True)

    result1 = Mutator(mut_map, algo_stage1, iteration=0, terminal=False).run()
    mut_map = mut_map.extend(result1.mutation_stage)

    result2 = Mutator(mut_map, algo_stage2, iteration=0, terminal=False).run()
    mut_map = mut_map.extend(result2.mutation_stage)

    assert len(mut_map.mutation_stages) >= 3

    compressed = mut_map.compressed()

    assert len(compressed.mutation_stages) == 1

    assert (
        compressed.G_in.get_self_node().node().get_uuid()
        == mut_map.G_in.get_self_node().node().get_uuid()
    )
    assert (
        compressed.G_out.get_self_node().node().get_uuid()
        == mut_map.G_out.get_self_node().node().get_uuid()
    )

    # Use ORIGINAL operables for map_forward (from first stage's input)
    for param_po in [param_a_po, param_b_po]:
        orig_result = mut_map.map_forward(param_po)
        comp_result = compressed.map_forward(param_po)
        assert orig_result.maps_to is not None
        assert comp_result.maps_to is not None
        assert orig_result.maps_to.is_same(comp_result.maps_to)

    # The original Add was mutated then removed
    orig_add_result = mut_map.map_forward(add_expr_po)
    comp_add_result = compressed.map_forward(add_expr_po)
    assert orig_add_result.removed == comp_add_result.removed

    assert len(compressed.output_operables) == len(mut_map.output_operables)

    for out_op in mut_map.output_operables:
        orig_back = mut_map.map_backward(out_op)
        comp_back = compressed.map_backward(out_op)
        orig_back_uuids = {op.instance.node().get_uuid() for op in orig_back}
        comp_back_uuids = {op.instance.node().get_uuid() for op in comp_back}
        assert orig_back_uuids == comp_back_uuids


def test_bootstrap_with_initial_state_no_new_operables():
    """
    Bootstrap with initial_state when no new operables exist.
    Should reuse the initial_state directly (no new stages).
    """
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _AppNoNew(fabll.Node):
        param_a = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Dimensionless)
        param_b = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Dimensionless)

    app = _AppNoNew.bind_typegraph(tg=tg).create_instance(g=g)
    param_a_op = app.param_a.get().can_be_operand.get()
    param_b_op = app.param_b.get().can_be_operand.get()
    param_a_po = app.param_a.get().is_parameter_operatable.get()
    param_b_po = app.param_b.get().is_parameter_operatable.get()

    initial = MutationMap.bootstrap(tg=tg, g=g, relevant=[param_a_op, param_b_op])
    compressed_initial = initial.compressed()

    resumed = MutationMap.bootstrap(
        tg=tg, g=g, relevant=[param_a_op, param_b_op], initial_state=compressed_initial
    )

    # When no new operables exist, we should reuse initial_state directly
    # Check that the mappings point to the same nodes
    result_a_init = compressed_initial.map_forward(param_a_po)
    result_a_resumed = resumed.map_forward(param_a_po)
    assert result_a_init.maps_to is not None
    assert result_a_resumed.maps_to is not None
    assert result_a_init.maps_to.is_same(
        result_a_resumed.maps_to, allow_different_graph=True
    )

    result_b_init = compressed_initial.map_forward(param_b_po)
    result_b_resumed = resumed.map_forward(param_b_po)
    assert result_b_init.maps_to is not None
    assert result_b_resumed.maps_to is not None
    assert result_b_init.maps_to.is_same(
        result_b_resumed.maps_to, allow_different_graph=True
    )


def test_bootstrap_with_initial_state_new_operables():
    """
    Bootstrap with initial_state when new operables have been added.
    Should include the new operables in the output.
    """
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _AppNewOps(fabll.Node):
        param_a = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Dimensionless)

    app = _AppNewOps.bind_typegraph(tg=tg).create_instance(g=g)
    param_a_op = app.param_a.get().can_be_operand.get()
    param_a_po = app.param_a.get().is_parameter_operatable.get()

    initial = MutationMap.bootstrap(tg=tg, g=g, relevant=[param_a_op])
    compressed_initial = initial.compressed()

    # Add a new parameter to the graph
    class _ParamB(fabll.Node):
        param_b = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Dimensionless)

    new_node = _ParamB.bind_typegraph(tg=tg).create_instance(g=g)
    param_b_op = new_node.param_b.get().can_be_operand.get()
    param_b_po = new_node.param_b.get().is_parameter_operatable.get()

    resumed = MutationMap.bootstrap(
        tg=tg, g=g, relevant=[param_a_op, param_b_op], initial_state=compressed_initial
    )

    # Should have the new stage with the new mapping
    assert resumed is not compressed_initial

    # param_a should map forward from original
    result_a = resumed.map_forward(param_a_po)
    assert result_a.maps_to is not None

    # param_b should also map forward (newly added)
    result_b = resumed.map_forward(param_b_po)
    assert result_b.maps_to is not None


def test_bootstrap_with_initial_state_relevance_change():
    """
    Bootstrap with initial_state when a new parameter is added to the graph.
    Initial solve only includes param_a, then param_b is created and added.
    Resume should detect and include the new param_b.
    """
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _AppRelevanceA(fabll.Node):
        param_a = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Dimensionless)

    app = _AppRelevanceA.bind_typegraph(tg=tg).create_instance(g=g)
    param_a_op = app.param_a.get().can_be_operand.get()
    param_a_po = app.param_a.get().is_parameter_operatable.get()

    # Initial solve only includes param_a
    initial = MutationMap.bootstrap(tg=tg, g=g, relevant=[param_a_op])
    compressed_initial = initial.compressed()

    # Now add param_b to the graph (after initial solve)
    class _AppRelevanceB(fabll.Node):
        param_b = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Dimensionless)

    app_b = _AppRelevanceB.bind_typegraph(tg=tg).create_instance(g=g)
    param_b_op = app_b.param_b.get().can_be_operand.get()
    param_b_po = app_b.param_b.get().is_parameter_operatable.get()

    # Verify param_b is NOT in the initial state's input operables
    assert param_b_po not in compressed_initial.input_operables

    # Resume with param_a AND param_b relevant
    resumed = MutationMap.bootstrap(
        tg=tg, g=g, relevant=[param_a_op, param_b_op], initial_state=compressed_initial
    )

    # Should create a new map since param_b needs to be added
    assert resumed is not compressed_initial

    # param_a should still map forward correctly
    result_a = resumed.map_forward(param_a_po)
    assert result_a.maps_to is not None

    # param_b should now map forward (newly added)
    result_b = resumed.map_forward(param_b_po)
    assert result_b.maps_to is not None


def test_bootstrap_with_initial_state_reduced_relevance():
    """
    Bootstrap with initial_state when relevance is reduced.
    Initial solve includes param_a and param_b, resume only includes param_a.
    The output should only contain param_a (filtered).
    """
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _AppReduced(fabll.Node):
        param_a = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Dimensionless)
        param_b = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Dimensionless)

    app = _AppReduced.bind_typegraph(tg=tg).create_instance(g=g)
    param_a_op = app.param_a.get().can_be_operand.get()
    param_b_op = app.param_b.get().can_be_operand.get()
    param_a_po = app.param_a.get().is_parameter_operatable.get()
    param_b_po = app.param_b.get().is_parameter_operatable.get()

    # Initial solve includes both param_a and param_b
    initial = MutationMap.bootstrap(tg=tg, g=g, relevant=[param_a_op, param_b_op])
    compressed_initial = initial.compressed()

    # Verify both are in initial state
    assert param_a_po in compressed_initial.input_operables
    assert param_b_po in compressed_initial.input_operables

    # Resume with ONLY param_a relevant (reduced relevance)
    resumed = MutationMap.bootstrap(
        tg=tg, g=g, relevant=[param_a_op], initial_state=compressed_initial
    )

    # Should NOT reuse initial_state (relevance changed)
    assert resumed is not compressed_initial

    # param_a should map forward
    result_a = resumed.map_forward(param_a_po)
    assert result_a.maps_to is not None

    # param_b should NOT map forward (filtered out of output)
    result_b = resumed.map_forward(param_b_po)
    assert result_b.maps_to is None


def test_bootstrap_with_initial_state_reuses_solved_versions():
    """
    Test that resuming from initial_state reuses solved operables.
    When an operable was solved/simplified in the initial state,
    the resumed state should use that solved version, not copy fresh.
    """
    from faebryk.core.solver.algorithm import algorithm

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _AppSolved(fabll.Node):
        param_a = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Dimensionless)

    app = _AppSolved.bind_typegraph(tg=tg).create_instance(g=g)
    param_a_op = app.param_a.get().can_be_operand.get()
    param_a_po = app.param_a.get().is_parameter_operatable.get()

    # Create initial bootstrap
    initial = MutationMap.bootstrap(tg=tg, g=g, relevant=[param_a_op])

    # Simulate solving by running a mutation that creates a simplified version
    @algorithm("simulate_solve", force_copy=True)
    def simulate_solve(mutator: Mutator):
        # Just copy param_a - this simulates that it was "processed"
        mutator.get_copy(param_a_op)

    result = Mutator(initial, simulate_solve, iteration=0, terminal=False).run()
    solved_state = initial.extend(result.mutation_stage)
    compressed = solved_state.compressed()

    # Get the solved version of param_a
    solved_a = compressed.map_forward(param_a_po).maps_to
    assert solved_a is not None

    # Now add param_b and resume
    class _ParamBReuse(fabll.Node):
        param_b = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Dimensionless)

    new_node = _ParamBReuse.bind_typegraph(tg=tg).create_instance(g=g)
    param_b_op = new_node.param_b.get().can_be_operand.get()
    param_b_po = new_node.param_b.get().is_parameter_operatable.get()

    # Resume with both param_a and param_b
    resumed = MutationMap.bootstrap(
        tg=tg, g=g, relevant=[param_a_op, param_b_op], initial_state=compressed
    )

    # param_a in resumed should be the SOLVED version (same UUID as solved_a)
    resumed_a = resumed.map_forward(param_a_po).maps_to
    assert resumed_a is not None

    # The solved version should be in the resumed graph
    # (copied from initial_state.G_out). Verify by checking the UUID matches
    solved_uuid = solved_a.instance.node().get_uuid()
    resumed_uuid = resumed_a.instance.node().get_uuid()
    assert solved_uuid == resumed_uuid

    # param_b should also be in the resumed state
    resumed_b = resumed.map_forward(param_b_po).maps_to
    assert resumed_b is not None


if __name__ == "__main__":
    import typer

    typer.run(test_mutate_copy_terminated_predicate)
