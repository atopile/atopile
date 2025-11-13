# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Iterable, Sequence

from more_itertools import first
from rich.table import Table
from rich.tree import Tree

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
import faebryk.library.Expressions as Expressions
from faebryk.core.solver.algorithm import SolverAlgorithm
from faebryk.core.solver.utils import (
    S_LOG,
    SHOW_SS_IS,
    VERBOSE_TABLE,
    ContradictionByLiteral,
    MutatorUtils,
    SolverAll,
    SolverAllExtended,
    SolverLiteral,
    get_graphs,
)
from faebryk.library.Expressions import IsConstrainable, IsConstrained, is_canonical
from faebryk.libs.exceptions import downgrade
from faebryk.libs.logging import rich_to_string
from faebryk.libs.util import (
    KeyErrorNotFound,
    cast_assert,
    duplicates,
    groupby,
    indented_container,
    invert_dict,
    once,
    unique_ref,
)

logger = logging.getLogger(__name__)
if S_LOG:
    logger.setLevel(logging.DEBUG)


Is = F.Expressions.Is
IsSubset = F.Expressions.IsSubset


class is_terminated(fabll.Node):
    _is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()


@dataclass
class Transformations:
    input_print_context: F.Parameters.ReprContext

    mutated: dict[
        F.Parameters.is_parameter_operatable, F.Parameters.is_parameter_operatable
    ] = field(default_factory=dict)
    removed: set[F.Parameters.is_parameter_operatable] = field(default_factory=set)
    copied: set[F.Parameters.is_parameter_operatable] = field(default_factory=set)
    created: dict[
        F.Parameters.is_parameter_operatable,
        list[F.Parameters.is_parameter_operatable],
    ] = field(default_factory=lambda: defaultdict(list))
    # TODO make api for contraining
    terminated: set[F.Expressions.IsConstrained] = field(default_factory=set)
    soft_replaced: dict[
        F.Parameters.is_parameter_operatable, F.Parameters.is_parameter_operatable
    ] = field(default_factory=dict)

    @property
    def dirty(self) -> bool:
        non_no_op_mutations = any(
            k is not v for k, v in self.mutated.items() if k not in self.copied
        )

        return bool(
            self.removed or non_no_op_mutations or self.created or self.terminated
        )

    @property
    def is_identity(self) -> bool:
        return (
            not self.removed
            and all(k is v for k, v in self.mutated.items())
            and not self.created
            and not self.terminated
        )

    @property
    def touched_graphs(self) -> set[graph.GraphView]:
        """
        Return graphs that require a copy in some form
        - if a mutation happened we need to copy the whole graph to replace
         the old node with the new one
        - if a node was removed, we need to copy the graph to remove it
        """
        return set(get_graphs(self.removed | self.mutated.keys()))

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
            input_print_context=input_print_context,
        )

    # TODO careful with once, need to check if illegal call when not done
    @property
    @once
    def output_print_context(self) -> F.Parameters.ReprContext:
        context_old = self.input_print_context
        if self.is_identity:
            return context_old

        context_new = F.Parameters.ReprContext()
        context_new.variable_mapping.next_id = context_old.variable_mapping.next_id

        for s, d in self.mutated.items():
            if (s_p := s.is_parameter()) and (d_p := d.is_parameter()):
                s_p.compact_repr(context_old)
                s_mapping = context_old.variable_mapping.mapping[s_p]
                d_mapping = context_new.variable_mapping.mapping.get(d_p, None)
                if d_mapping is None or d_mapping > s_mapping:
                    context_new.variable_mapping.mapping[d_p] = s_mapping

        return context_new

    def __str__(self) -> str:
        if not self.dirty:
            return "Transformations()"
        assert self.input_print_context

        old_context = self.input_print_context
        new_context = self.output_print_context

        mutated_transformations = [
            (k.compact_repr(old_context), v.compact_repr(new_context))
            for k, v in self.mutated.items()
            if k not in self.copied
        ]
        mutated = indented_container(
            [f"{k} -> {v}" for k, v in mutated_transformations if k != v]
            + [f"copy {k}" for k, v in mutated_transformations if k == v]
        )
        created = indented_container(
            [k.compact_repr(new_context) for k in self.created]
        )
        removed = indented_container(
            [k.compact_repr(old_context) for k in self.removed]
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

    def get_new_constraints(
        self, op: F.Parameters.is_parameter_operatable
    ) -> list[F.Expressions.IsConstrainable]:
        # TODO could still happen, but then we have clash
        # keep this in mind for future
        if self.is_identity:
            return []
        if op not in self.copied:
            return []
        target = self.mutated[op]
        out = []
        for e in self.created:
            if not e.try_get_sibling_trait(F.Expressions.IsConstrained):
                continue
            if target in e.as_expression().get_operand_operatables():
                out.append(e)
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
        src_context: F.Parameters.ReprContext
        dst_context: F.Parameters.ReprContext
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

        dst_text = self.stage.dst.compact_repr(self.stage.dst_context)
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
                src_text = src.compact_repr(self.stage.src_context, use_name=True)
                reason_branch.add(Text(src_text, style="green"))
        else:
            reason_branch.add(Text("...no sources...", style="bold red"))

        return tree


class MutationStage:
    def __init__(
        self,
        tg: fbrk.TypeGraph,
        algorithm: SolverAlgorithm | str,
        iteration: int,
        print_context: F.Parameters.ReprContext,
        transformations: Transformations,
    ):
        self.algorithm = algorithm
        self.iteration = iteration
        self.transformations = transformations
        self.input_print_context = print_context
        self.tg = tg
        self.input_operables = set(
            F.Parameters.is_parameter_operatable.bind_typegraph(
                tg=self.tg
            ).get_instances(self.input_graph)
        )

    @property
    def output_graph(self) -> graph.GraphView:
        # It's enough to check for mutation graphs and not created ones
        # because the created ones always connect to graphs of the mutated ones
        # else they will be lost anyway
        # TODO
        # return get_graphs(
        #     chain(
        #         self.transformations.mutated.values(),
        #         self.transformations.created,
        #     )
        # )
        pass

    @property
    def input_graph(self) -> graph.GraphView:
        # TODO
        # return get_graphs(self.transformations.mutated.keys())
        pass

    @property
    @once
    def output_operables(self) -> set[F.Parameters.is_parameter_operatable]:
        return set(
            F.Parameters.is_parameter_operatable.bind_typegraph(self.tg).get_instances(
                g=self.output_graph
            )
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
            tg,
            algorithm=algorithm,
            iteration=iteration,
            print_context=print_context,
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
            self.tg,
            algorithm="identity",
            iteration=iteration,
            print_context=self.input_print_context,
            transformations=Transformations.identity(
                self.tg,
                self.output_graph,
                input_print_context=self.output_print_context,
            ),
        )

    def print_graph_contents(
        self,
        trait_filter: type[fabll.Node] = F.Parameters.is_parameter_operatable,
        log: Callable[[str], None] = logger.debug,
    ):
        pre_nodes = fabll.Traits.get_implementor_objects(
            trait=trait_filter.bind_typegraph(tg=self.tg), g=self.output_graph
        )
        if SHOW_SS_IS:
            nodes = pre_nodes
        else:
            nodes = [
                n
                for n in pre_nodes
                if not (
                    MutatorUtils.is_alias_is_literal(
                        (po := n.get_trait(F.Parameters.is_parameter_operatable))
                        or MutatorUtils.is_subset_literal(po)
                    )
                )
            ]
        out = ""
        node_by_depth = groupby(
            nodes,
            key=lambda n: n.get_trait(F.Parameters.is_parameter_operatable).get_depth(),
        )
        for depth, dnodes in sorted(node_by_depth.items(), key=lambda t: t[0]):
            out += f"\n  --Depth {depth}--"
            for n in dnodes:
                compact_repr = n.get_trait(
                    F.Parameters.is_parameter_operatable
                ).compact_repr(self.output_print_context)
                out += f"\n      {compact_repr}"

        if not nodes:
            return
        log(f"Graph {len(nodes)}/{len(pre_nodes)} [{out}\n]")

    def map_forward(
        self, param: F.Parameters.is_parameter_operatable
    ) -> F.Parameters.is_parameter_operatable | None:
        if self.is_identity:
            return param
        return self.transformations.mutated.get(param)

    @property
    # FIXME not sure why but this breaks stuff, but is very necessary for speed
    @once
    def backwards_mapping(
        self,
    ) -> dict[
        F.Parameters.is_parameter_operatable,
        list[F.Parameters.is_parameter_operatable],
    ]:
        return invert_dict(self.transformations.mutated)

    def map_backward(
        self, param: F.Parameters.is_parameter_operatable
    ) -> list[F.Parameters.is_parameter_operatable]:
        if self.is_identity:
            return [param]
        return self.backwards_mapping.get(param, [])

    @property
    def output_print_context(self) -> F.Parameters.ReprContext:
        if not self.transformations:
            return self.input_print_context
        return self.transformations.output_print_context

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

        context_old = self.input_print_context
        context_new = self.output_print_context

        created_ops = self.transformations.created

        rows: list[tuple[str, str]] = []

        for op, from_ops in created_ops.items():
            key = "new"
            key_from_ops = " \n  ".join(o.compact_repr(context_old) for o in from_ops)
            key_from_ops = f"  {key_from_ops}"
            value = op.compact_repr(context_new)
            if MutatorUtils.is_alias_is_literal(op) or MutatorUtils.is_subset_literal(
                op
            ):
                expr = next(iter(op.operatable_operands))
                lit = next(iter(op.get_operand_literals().values()))
                if not SHOW_SS_IS and expr in created_ops:
                    continue
                alias_type = (
                    "alias"
                    if fabll.Traits(op).get_obj_raw().isinstance(Expressions.Is)
                    else "subset"
                )
                key = f"new_{alias_type}\n{lit}"
                value = expr.compact_repr(context_new)
            if key_from_ops:
                key = f"{key} from\n{key_from_ops}"
            rows.append((key, value))

        terminated = self.transformations.terminated.difference(
            co.try_get_sibling_trait(F.Expressions.IsConstrained) for co in created_ops
        )
        for op in terminated:
            rows.append(
                (
                    "terminated",
                    fabll.Traits(op)
                    .get_trait_of_obj(F.Expressions.is_expression)
                    .compact_repr(context_new),
                )
            )

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
                s.has_trait(F.Expressions.IsConstrainable)
                and new.replace("✓", "") == old.replace("✓", "")
                and d.try_get_literal() != s.try_get_literal()
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
                    new_constraints = self.transformations.get_new_constraints(origin)
                    if new_constraints:
                        reason = Traceback.Type.CONSTRAINED
                        related_ = [
                            self.get_traceback_stage(
                                fabll.Traits(e).get_trait_of_obj(
                                    F.Parameters.is_parameter_operatable
                                )
                            )
                            for e in new_constraints
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
            src_context=self.input_print_context,
            dst_context=self.output_print_context,
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
        assert fabll.isparameteroperable(param)
        is_root = param.get_parent() is not None

        if not self.non_identity_stages:
            out = self.first_stage.map_forward(param)
            if out is None and is_root:
                raise KeyErrorNotFound(
                    f"Looking for root parameter not in graph: {param}"
                )
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
                is_start = param is chain_end
                assert not is_root or is_start, (
                    "should never remove root parameters"
                    f" chain_end {param} -> {chain_end} interrupted at"
                    f" {m.algorithm}:{m.iteration}"
                )
                if is_root and is_start:
                    raise KeyErrorNotFound(
                        f"Looking for root parameter not in graph: {param}"
                    )
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

    def try_get_literal(
        self,
        po: F.Parameters.is_parameter_operatable,
        allow_subset: bool = False,
        domain_default: bool = False,
    ) -> F.Literals.LiteralNodes | None:
        def _default():
            if not domain_default:
                return None
            if not (p := po.get_trait(F.Parameters.is_parameter)):
                raise ValueError("domain_default only supported for parameters")
            return p.domain_set()

        maps_to = self.map_forward(po).maps_to
        if not maps_to:
            return _default()
        lit = maps_to.try_extract_literal(allow_subset=allow_subset)
        if lit is None:
            return _default()
        param_units = po.get_trait(F.Units.HasUnit).get_unit()
        if (
            lit_n := lit.try_cast(F.Literals.Numbers)
        ) is not None and not lit_n.are_units_compatible(param_units):
            return lit_n.op_mul_intervals(
                F.Literals.Numbers.bind_typegraph_from_instance(lit_n.instance)
                .create_instance(lit_n.instance.g())
                .setup_from_interval(1, 1, unit=param_units)
            )
        return lit

    def __repr__(self) -> str:
        return f"ReprMap({str(self)})"

    def __str__(self) -> str:
        return (
            f"|stages|={len(self.mutation_stages)}"
            f", |graph|={self.output_graph.get_node_count()}"
            f", |V|={len(self.last_stage.output_operables)}"
        )

    @staticmethod
    def identity(
        tg: fbrk.TypeGraph,
        g: graph.GraphView,
        algorithm: SolverAlgorithm | str = "identity",
        iteration: int = 0,
        print_context: F.Parameters.ReprContext | None = None,
    ) -> "MutationMap":
        return MutationMap(
            MutationStage.identity(
                tg,
                g,
                algorithm=algorithm,
                iteration=iteration,
                print_context=print_context or F.Parameters.ReprContext(),
            )
        )

    def extend(self, *changes: MutationStage) -> "MutationMap":
        return MutationMap(*self.mutation_stages, *changes)

    @property
    def last_stage(self) -> MutationStage:
        return self.mutation_stages[-1]

    @property
    def output_graph(self) -> graph.GraphView:
        return self.last_stage.output_graph

    @property
    def output_operables(self) -> set[F.Parameters.is_parameter_operatable]:
        return self.last_stage.output_operables

    @property
    def first_stage(self) -> MutationStage:
        return self.mutation_stages[0]

    @property
    def input_graph(self) -> graph.GraphView:
        return self.first_stage.input_graph

    @property
    def input_operables(self) -> set[F.Parameters.is_parameter_operatable]:
        return self.first_stage.input_operables

    @property
    def output_print_context(self) -> F.Parameters.ReprContext:
        return self.last_stage.output_print_context

    @property
    def input_print_context(self) -> F.Parameters.ReprContext:
        return self.first_stage.input_print_context

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
        table.add_column("Variable name")
        table.add_column("fabll.Node name")

        for p in sorted(
            fabll.Node.bind_typegraph(self.input_graph).nodes_of_type(Parameter),
            key=Parameter.get_full_name,
        ):
            table.add_row(p.compact_repr(self.input_print_context), p.get_full_name())

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
    def non_trivial_mutated_expressions(self) -> set[F.Expressions.is_canonical]:
        # TODO make faster, compact repr is a pretty bad one
        # consider congruence instead, but be careful since not in same graph space
        out = {
            v.get_trait(F.Expressions.is_canonical)
            for v, ks in self.compressed_mapping_backwards.items()
            if v.has_trait(F.Expressions.is_canonical)
            # if all merged changed, else covered by merged
            and all(
                k.has_trait(F.Expressions.is_canonical)
                and k is not v
                and k.compact_repr() != v.compact_repr()
                for k in ks
            )
        }
        return out

    @property
    def tg(self) -> fbrk.TypeGraph:
        return self.first_stage.tg


@dataclass
class AlgoResult:
    mutation_stage: MutationStage
    dirty: bool


class Mutator:
    # Algorithm Interface --------------------------------------------------------------
    def make_lit(self, value: F.Literals.LiteralValues) -> F.Literals.LiteralNodes:
        return F.Literals.make_lit(self.tg, value)

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
            if self.get_mutated(po) is not new_po:
                raise ValueError(f"already mutated to: {self.get_mutated(po)}")

        if self.is_removed(po):
            raise ValueError("Object marked removed")

        self.transformations.mutated[po] = new_po
        return new_po

    def _override_repr(
        self,
        po: F.Parameters.is_parameter_operatable,
        new_po: F.Parameters.is_parameter_operatable,
    ):
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
        param: F.Parameters.is_parameter,
        units: F.Units.IsUnit | None = None,
        domain: F.NumberDomain | None = None,
        soft_set: F.Literals.Numbers | None = None,
        within: F.Literals.Numbers | None = None,
        guess: F.Literals.Numbers | None = None,
        tolerance_guess: float | None = None,
        likely_constrained: bool | None = None,
        override_within: bool = False,
    ) -> F.Parameters.is_parameter:
        if param in self.transformations.mutated:
            out = self.get_mutated(param.as_parameter_operatable())
            p = out.as_parameter()
            if np := p.try_get_sibling_trait(F.Parameters.NumericParameter):
                assert np.get_units() == units
                assert np.get_domain() == domain
                assert np.get_soft_set() == soft_set
                assert np.get_guess() == guess
                assert np.get_tolerance_guess() == tolerance_guess
            assert p.get_likely_constrained() == likely_constrained
            return p

        param_obj = fabll.Traits(param).get_obj_raw()
        if p := param_obj.try_cast(F.Parameters.NumericParameter):
            new_param = (
                F.Parameters.NumericParameter.bind_typegraph_from_instance(
                    param.instance
                )
                .create_instance(self.G)
                .setup(
                    units=units if units is not None else p.get_units(),
                    within=within if override_within else p.get_within(),
                    domain=domain if domain is not None else p.get_domain(),
                    soft_set=soft_set if soft_set is not None else p.get_soft_set(),
                    guess=guess if guess is not None else p.get_guess(),
                    tolerance_guess=tolerance_guess
                    if tolerance_guess is not None
                    else p.get_tolerance_guess(),
                    likely_constrained=likely_constrained
                    if likely_constrained is not None
                    else param.get_likely_constrained(),
                )
            )
        elif p := param_obj.try_cast(F.Parameters.BooleanParameter):
            new_param = (
                F.Parameters.BooleanParameter.bind_typegraph_from_instance(
                    param.instance
                )
                .create_instance(self.G)
                .setup()
            )
        elif p := param_obj.try_cast(F.Parameters.StringParameter):
            new_param = (
                F.Parameters.StringParameter.bind_typegraph_from_instance(
                    param.instance
                )
                .create_instance(self.G)
                .setup()
            )
        elif p := param_obj.try_cast(F.Parameters.EnumParameter):
            new_param = (
                F.Parameters.EnumParameter.bind_typegraph_from_instance(param.instance)
                .create_instance(self.G)
                .setup(enum=p.get_enum())
            )
        else:
            assert False, "Unknown parameter type"

        return self._mutate(
            param.as_parameter_operatable(),
            new_param.get_trait(F.Parameters.is_parameter_operatable),
        ).as_parameter()

    def _create_expression[T: fabll.NodeT](
        self,
        expr_factory: type[T],
        *operands: F.Parameters.can_be_operand,
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
        if non_operands is not None:
            new_expr = expr_factory(*new_operands, non_operands=non_operands)  # type: ignore
        else:
            new_expr = expr_factory(*new_operands)

        if constrain and (
            ce := new_expr.try_get_sibling_trait(F.Expressions.IsConstrainable)
        ):
            ce.constrain()
            # TODO this is better, but ends up in inf loop
            # self.constrain(new_expr)

        for op in new_operands:
            if op.has_trait(F.Parameters.is_parameter_operatable):
                assert op.get_graph() == new_expr.get_graph(), (
                    f"Graph mismatch: {op.get_graph()} != {new_expr.get_graph()}"
                )

        return new_expr

    def mutate_expression(
        self,
        expr: F.Expressions.is_expression,
        operands: Iterable[F.Parameters.can_be_operand] | None = None,
        expression_factory: type[fabll.NodeT] | None = None,
        soft_mutate: type[Is] | type[IsSubset] | None = None,
        ignore_existing: bool = False,
        from_ops: Sequence[F.Parameters.is_parameter_operatable] | None = None,
    ) -> F.Expressions.is_canonical:
        if expression_factory is None:
            expression_factory = type(expr)

        if operands is None:
            operands = expr.get_operands()

        if (po := expr.as_parameter_operatable()) in self.transformations.mutated:
            out = self.get_mutated(po)
            assert out.has_trait(F.Expressions.is_canonical)
            # TODO more checks
            assert out.isinstance(expression_factory)
            # still need to run soft_mutate even if expr already in repr
            if soft_mutate:
                expr = out.as_expression()
            else:
                return out.get_sibling_trait(F.Expressions.is_canonical)

        if soft_mutate:
            assert expression_factory.bind_typegraph_from_instance(
                expr.instance
            ).check_if_instance_of_type_has_trait(F.Expressions.is_canonical)
            # TODO: technically the return type is incorrect, but it's not used anywhere
            # if run with soft_mutaste
            return self.soft_mutate_expr(
                expression_factory, expr, operands, soft_mutate, from_ops=from_ops
            )

        if from_ops is not None:
            raise NotImplementedError("only supported for soft_mutate")

        copy_only = expression_factory is type(expr) and operands == expr.get_operands()
        if not copy_only and not ignore_existing:
            assert expression_factory.bind_typegraph_from_instance(
                expr.instance
            ).check_if_instance_of_type_has_trait(F.Expressions.is_canonical)
            exists = self.utils.find_congruent_expression(
                expression_factory, *operands, allow_uncorrelated=False
            )
            if exists is not None:
                return self._mutate(
                    expr.as_parameter_operatable(), self.get_copy(exists)
                ).get_sibling_trait(F.Expressions.is_canonical)

        constrain = expr.try_get_sibling_trait(F.Expressions.IsConstrained) is not None
        new_expr = self._create_expression(
            expression_factory,
            *operands,
            non_operands=expr.non_operands,
            constrain=constrain,
        )

        if expr.try_get_sibling_trait(F.Expressions.IsConstrainable) is not None:
            if self.is_predicate_terminated(expr):
                fabll.Traits.create_and_add_instance_to(
                    fabll.Traits(new_expr).get_obj_raw(), is_terminated
                )

        return self._mutate(expr, new_expr)  # type: ignore #TODO

    def soft_replace[T: F.Parameters.is_parameter_operatable](
        self,
        current: T,
        new: F.Parameters.is_parameter_operatable,
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
        expression_factory: type[fabll.NodeT],
        expr: F.Expressions.is_expression,
        operands: Iterable[F.Parameters.can_be_operand],
        soft: type[Is] | type[IsSubset],
        from_ops: Sequence[F.Parameters.is_parameter_operatable] | None = None,
    ):
        operands = list(operands)
        # Don't create A is A, lit is lit
        if expr.is_congruent_to_factory(
            expression_factory, operands, allow_uncorrelated=True
        ):
            return expr  # type: ignore

        # Avoid alias X to Op1(lit) if X is!! Op2(lit)
        congruent = {
            alias
            for alias in (
                self.utils.get_aliases(expr.as_parameter_operatable())
                if soft is Is
                else self.utils.get_supersets(expr.as_parameter_operatable())
            )
            if fabll.Traits(alias).get_obj_raw().isinstance(expression_factory)
            and alias.as_expression().is_congruent_to_factory(
                expression_factory, operands, allow_uncorrelated=True
            )
        }
        if congruent:
            return next(iter(congruent))

        out = self.create_expression(
            expression_factory,
            *operands,
            from_ops=[expr.as_parameter_operatable(), *(from_ops or [])],
            allow_uncorrelated=soft is IsSubset,
        )
        self.soft_mutate(soft, expr.as_parameter_operatable(), out, from_ops=from_ops)
        return out

    # TODO make more use of soft_mutate for alias & ss with non-lit
    def soft_mutate(
        self,
        soft: type[Is] | type[IsSubset],
        old: F.Parameters.is_parameter_operatable,
        new: SolverAll,
        from_ops: Sequence[F.Parameters.is_parameter_operatable] | None = None,
    ):
        # filter A is A, A ss A
        if new is old:
            return
        self.create_expression(
            soft,
            old.as_operand(),
            new.as_operand(),
            constrain=True,
            from_ops=unique_ref([old] + list(from_ops or [])),
            # FIXME
            allow_uncorrelated=True,
        )

    def mutate_unpack_expression(
        self,
        expr: F.Expressions.is_expression,
        operands: list[F.Parameters.is_parameter_operatable] | None = None,
    ) -> F.Parameters.is_parameter_operatable:
        """
        ```
        op(A, ...) -> A
        op!(A, ...) -> A!
        ```
        """
        unpacked = (
            expr.get_operands()[0].is_parameter_operatable()
            if operands is None
            else operands[0]
        )
        if unpacked is None:
            raise ValueError("Unpacked operand can't be a literal")
        out = self._mutate(expr.as_parameter_operatable(), self.get_copy(unpacked))
        if expr.try_get_sibling_trait(F.Expressions.IsConstrained):
            self.constrain(out.get_sibling_trait(F.Expressions.IsConstrainable))
        return out

    def mutator_neutralize_expressions(
        self, expr: F.Expressions.is_expression
    ) -> F.Parameters.is_parameter_operatable:
        """
        '''
        op(op_inv(A), ...) -> A
        op!(op_inv(A), ...) -> A!
        '''
        """
        inner_expr = expr.get_operands()[0]
        if not (
            inner_expr_e := inner_expr.try_get_sibling_trait(
                F.Expressions.is_expression
            )
        ):
            raise ValueError("Inner operand must be an expression")
        inner_operand = inner_expr_e.get_operands()[0]
        if not (inner_operand_po := inner_operand.as_parameter_operatable()):
            raise ValueError("Unpacked operand can't be a literal")
        out = self._mutate(
            expr.as_parameter_operatable(), self.get_copy(inner_operand_po)
        )
        if expr.try_get_sibling_trait(F.Expressions.IsConstrained):
            self.constrain(out.get_sibling_trait(F.Expressions.IsConstrainable))
        return out

    def mutate_expression_with_op_map(
        self,
        expr: F.Expressions.is_expression,
        operand_mutator: Callable[
            [int, F.Parameters.can_be_operand],
            F.Parameters.can_be_operand,
        ],
        expression_factory: type[fabll.NodeT] | None = None,
        ignore_existing: bool = False,
    ) -> F.Expressions.is_canonical:
        """
        operand_mutator: Only allowed to return old Graph objects
        """
        return self.mutate_expression(
            expr,
            operands=[
                operand_mutator(i, op) for i, op in enumerate(expr.get_operands())
            ],
            expression_factory=expression_factory,
            ignore_existing=ignore_existing,
        )

    def get_copy(
        self, obj: F.Parameters.is_parameter_operatable, accept_soft: bool = True
    ) -> F.Parameters.is_parameter_operatable:
        if not fabll.isparameteroperable(obj):
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

        if expr := obj.is_expresssion():
            return self.mutate_expression(expr).as_parameter_operatable()
        elif p := obj.is_parameter():
            return self.mutate_parameter(p).as_parameter_operatable()

        assert False

    def create_expression[T: fabll.NodeT](
        self,
        expr_factory: type[T],
        *operands: F.Parameters.can_be_operand,
        check_exists: bool = True,
        from_ops: Sequence[F.Parameters.is_parameter_operatable] | None = None,
        constrain: bool = False,
        allow_uncorrelated: bool = False,
        _relay: bool = True,
    ) -> T | IsSubset | Is | F.Literals.is_literal:
        from faebryk.core.solver.symbolic.pure_literal import (
            _exec_pure_literal_operands,
        )

        expr_bound = expr_factory.bind_typegraph(self.tg)
        assert expr_bound.check_if_instance_of_type_has_trait(
            F.Expressions.is_canonical
        )
        from_ops = [
            x for x in unique_ref(from_ops or []) if fabll.isparameteroperable(x)
        ]
        if _relay:
            if constrain and expr_factory is IsSubset:
                return self.utils.subset_to(operands[0], operands[1], from_ops=from_ops)
            if constrain and expr_factory is Is:
                return self.utils.alias_to(operands[0], operands[1], from_ops=from_ops)
            res = _exec_pure_literal_operands(expr_bound, operands)
            if res is not None:
                if constrain and res != self.make_lit(True):
                    raise ContradictionByLiteral(
                        "Literal is not true",
                        involved=from_ops,
                        literals=[res],
                        mutator=self,
                    )
                return res

        expr = None
        if check_exists:
            # TODO look in old & new graph
            expr = self.utils.find_congruent_expression(
                expr_factory,
                *operands,
                allow_uncorrelated=allow_uncorrelated,
            )

        if expr is None:
            expr = self._create_expression(
                expr_factory,
                *operands,
                constrain=constrain,
            )
            self.transformations.created[
                expr.get_trait(F.Parameters.is_parameter_operatable)
            ] = from_ops

        # TODO double constrain ugly
        if constrain and (co := expr.try_get_trait(F.Expressions.IsConstrainable)):
            self.constrain(co)

        return expr

    def remove(self, *po: F.Parameters.is_parameter_operatable):
        assert not any(p in self.transformations.mutated for p in po), (
            "Object already in repr_map"
        )
        root_pos = [p for p in po if p.get_parent() is not None]
        assert not root_pos, f"should never remove root parameters: {root_pos}"
        self.transformations.removed.update(po)

    def register_created_parameter(
        self,
        param: F.Parameters.is_parameter,
        from_ops: Sequence[F.Parameters.is_parameter_operatable] | None = None,
    ) -> F.Parameters.is_parameter:
        self.transformations.created[param.as_parameter_operatable()] = list(
            from_ops or []
        )
        return param

    def constrain(self, *po: F.Expressions.IsConstrainable, terminate: bool = False):
        for p in po:
            p.constrain()
            self.utils.alias_to(p, self.make_lit(True), terminate=terminate)

    def predicate_terminate(self, pred: F.Expressions.IsConstrained):
        if pred.has_trait(is_terminated):
            return
        fabll.Traits.create_and_add_instance_to(
            fabll.Traits(pred).get_obj_raw(), is_terminated
        )
        self.transformations.terminated.add(pred)

    def predicate_reset_termination(self, pred: F.Expressions.IsConstrained):
        if not pred.has_trait(is_terminated):
            return
        # TODO: remove trait
        raise NotImplementedError("Not implemented")

    # Algorithm Query ------------------------------------------------------------------
    def is_predicate_terminated(self, pred: F.Expressions.IsConstrained) -> bool:
        return pred.try_get_sibling_trait(is_terminated) is not None

    def get_parameter_operatables(
        self, include_terminated: bool = False, sort_by_depth: bool = False
    ) -> set[F.Parameters.is_parameter_operatable]:
        out = set(
            fabll.Traits.get_implementors(
                F.Parameters.is_parameter_operatable.bind_typegraph(self.tg), self.G
            )
        )

        if not include_terminated:
            out = {
                n
                for n in out
                if not (
                    (nc := n.try_get_trait(IsConstrained))
                    and self.is_predicate_terminated(nc)
                )
            }

        if sort_by_depth:
            out = {
                n.get_trait(F.Parameters.is_parameter_operatable)
                for n in F.Expressions.is_expression.sort_by_depth(
                    (n.get_obj() for n in out), ascending=True
                )
            }

        return out

    def get_parameters(self) -> set[F.Parameters.is_parameter]:
        return set(
            fabll.Traits.get_implementors(
                F.Parameters.is_parameter.bind_typegraph(self.tg), self.G
            )
        )

    def get_expressions[T: "fabll.Node"](
        self,
        t: type[T] = fabll.Node,
        sort_by_depth: bool = False,
        created_only: bool = False,
        new_only: bool = False,
        include_terminated: bool = False,
        required_traits: tuple[type[fabll.Node], ...] = (),
    ) -> list[T] | set[T]:
        assert not new_only or not created_only

        if new_only:
            out = {
                ne
                for n in self._new_operables
                if (ne := fabll.Traits(n).get_obj_raw().try_cast(t))
            }
        elif created_only:
            out = {
                ne
                for n in self.transformations.created
                if (ne := fabll.Traits(n).get_obj_raw().try_cast(t))
            }
        else:
            out = t.bind_typegraph(self.tg).get_instances(self.G)

        if not include_terminated:
            out = {
                n
                for n in out
                if not (
                    (nc := n.try_get_trait(IsConstrained))
                    and self.is_predicate_terminated(nc)
                )
            }

        if sort_by_depth:
            out = F.Expressions.is_expression.sort_by_depth(out, ascending=True)

        return out

    @property
    def non_copy_mutated(self) -> set[F.Expressions.is_canonical]:
        if self._mutations_since_last_iteration is None:
            return set()
        return self._mutations_since_last_iteration.non_trivial_mutated_expressions

    def get_literal_aliases(self, new_only: bool = True):
        """
        Find new ops which are Is expressions between a F.Parameters.is_parameter_operatable and a
        literal
        """

        aliases: set[CanonicalExpression]
        aliases = set(
            self.get_expressions(Is, new_only=new_only, include_terminated=True)
        )

        if new_only and self._mutations_since_last_iteration is not None:
            # Taking into account if op with no literal merged into a op with literal
            mapping = self._mutations_since_last_iteration.has_merged
            for new, olds in mapping.items():
                new_lit = self.utils.try_extract_literal(new)
                if new_lit is None:
                    continue
                old_lits = {self.utils.try_extract_literal(o) for o in olds}
                if old_lits == {new_lit}:
                    continue
                aliases.update(new.get_operations(Is, constrained_only=True))
            aliases.update(
                self._mutations_since_last_iteration.non_trivial_mutated_expressions
            )

        return (expr for expr in aliases if self.utils.is_alias_is_literal(expr))

    def _get_literal_subsets(self, new_only: bool = True):
        subsets: set[F.Expressions.IsSubset]
        subsets = set(
            self.get_expressions(IsSubset, new_only=new_only, include_terminated=True)
        )

        if new_only and self._mutations_since_last_iteration is not None:
            # Taking into account if op with no literal merged into a op with literal
            mapping = self._mutations_since_last_iteration.has_merged
            for new, olds in mapping.items():
                new_lit = self.utils.try_extract_literal(new, allow_subset=True)
                if new_lit is None:
                    continue
                old_lits = {
                    self.utils.try_extract_literal(o, allow_subset=True) for o in olds
                }
                if old_lits == {new_lit}:
                    continue
                subsets.update(new.get_operations(IsSubset, constrained_only=True))
            subsets.update(
                (
                    iss
                    for e in self._mutations_since_last_iteration.non_trivial_mutated_expressions  # noqa: E501
                    if (
                        iss := fabll.Traits(e)
                        .get_obj_raw()
                        .try_cast(F.Expressions.IsSubset)
                    )
                )
            )

        return (
            expr
            for expr in subsets
            if self.utils.is_subset_literal(
                expr.get_trait(F.Parameters.is_parameter_operatable)
            )
        )

    def get_literal_mappings(self, new_only: bool = True, allow_subset: bool = False):
        # TODO better exceptions

        ops = self.get_literal_aliases(new_only=new_only)
        mapping = {self.utils.get_lit_mapping_from_lit_expr(op) for op in ops}
        dupes = duplicates(mapping, lambda x: x[0], by_eq=True)
        if dupes:
            raise ContradictionByLiteral(
                "Literal contradictions",
                list(dupes.keys()),
                list(v[1] for vs in dupes.values() for v in vs),
                mutator=self,
            )
        mapping_dict = dict(mapping)

        if allow_subset:
            ops_ss = self._get_literal_subsets(new_only=new_only)
            mapping_ss = [self.utils.get_lit_mapping_from_lit_expr(op) for op in ops_ss]
            grouped_ss = groupby(mapping_ss, key=lambda t: t[0])
            for k, v in grouped_ss.items():
                ss_lits = [ss_lit for _, ss_lit in v]
                merged_ss = F.Literals.is_literal.intersect_all(*ss_lits)
                if merged_ss.is_empty():
                    raise ContradictionByLiteral(
                        "Empty intersection", [k], ss_lits, mutator=self
                    )
                if k in mapping_dict:
                    if not mapping_dict[k].is_subset_of(merged_ss):  # type: ignore
                        raise ContradictionByLiteral(
                            "is lit not subset of ss lits",
                            [k],
                            [mapping_dict[k], *ss_lits],
                            mutator=self,
                        )
                    continue
                mapping_dict[k] = merged_ss

        return mapping_dict

    def is_removed(self, po: F.Parameters.is_parameter_operatable) -> bool:
        return po in self.transformations.removed

    def has_been_mutated(self, po: F.Parameters.is_parameter_operatable) -> bool:
        return po in self.transformations.mutated

    def get_mutated(
        self, po: F.Parameters.is_parameter_operatable
    ) -> F.Parameters.is_parameter_operatable:
        return self.transformations.mutated[po]

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

        # TODO
        self.G = mutation_map.output_graph
        self.tg: fbrk.TypeGraph = mutation_map.tg

        self.print_context = mutation_map.output_print_context
        self._mutations_since_last_iteration = mutation_map.get_iteration_mutation(algo)

        self._starting_operables = set(
            self.get_parameter_operatables(include_terminated=True)
        )

        self.transformations = Transformations(input_print_context=self.print_context)

    @property
    @once
    def _new_operables(self) -> set[F.Parameters.is_parameter_operatable]:
        _last_run_operables = set()
        if self._mutations_since_last_iteration is not None:
            _last_run_operables = set(
                self._mutations_since_last_iteration.compressed_mapping_forwards_complete.values()
            )
        assert _last_run_operables.issubset(self._starting_operables)
        return self._starting_operables - _last_run_operables

    def _run(self):
        self.algo(self)

    def _copy_unmutated(
        self,
    ):
        _touched_graphs = self.transformations.touched_graphs
        touched = self.transformations.mutated.keys() | self.transformations.removed

        # TODO might not need to sort
        other_param_op = F.Expressions.is_expression.sort_by_depth(
            (
                fabll.Node.bind_typegraph(*_touched_graphs).nodes_of_type(
                    F.Parameters.is_parameter_operatable
                )
                - touched
            ),
            ascending=True,
        )
        for p in other_param_op:
            self.get_copy(p)

        # optimization: if just new_ops, no need to copy
        # pass through untouched graphs
        untouched_graphs = self.G - _touched_graphs
        for p in fabll.Node.bind_typegraph(*untouched_graphs).nodes_of_type(
            F.Parameters.is_parameter_operatable
        ):
            self.transformations.mutated[p] = p

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
            for op in fabll.Node.bind_typegraph(g).nodes_of_type(
                F.Parameters.is_parameter_operatable
            )
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
        if not self.transformations.dirty:
            return AlgoResult(
                mutation_stage=MutationStage.identity(
                    self.tg,
                    self.mutation_map.output_graph,
                    algorithm=self.algo,
                    iteration=self.iteration,
                    print_context=self.print_context,
                ),
                dirty=False,
            )

        touched_pre_copy = self.transformations.touched_graphs
        self.check_no_illegal_mutations()
        self._copy_unmutated()
        stage = MutationStage(
            tg=self.tg,
            algorithm=self.algo,
            iteration=self.iteration,
            transformations=self.transformations,
            print_context=self.print_context,
        )

        # Check if original graphs ended up in result
        # allowed if no copy was needed for graph
        assert not (touched_pre_copy & {stage.output_graph})

        return AlgoResult(mutation_stage=stage, dirty=True)

    def run(self):
        self._run()
        return self.close()

    # Debug Interface ------------------------------------------------------------------
    def __repr__(self) -> str:
        return f"Mutator('{self.algo.name}' {self.transformations})"
