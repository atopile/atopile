# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from textwrap import indent
from typing import Iterable

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.solver import Solver
from faebryk.core.solver.utils import Contradiction
from faebryk.libs.app.keep_picked_parts import (
    get_pcb_sourced_constraints,
    has_pcb_source,
)
from faebryk.libs.test.times import Times
from faebryk.libs.util import (
    Advancable,
    ConfigFlag,
    EquivalenceClasses,
    Tree,
    bfs_visit,
    debug_perf,
    indented_container,
)

NO_PROGRESS_BAR = ConfigFlag("NO_PROGRESS_BAR", default=False)

logger = logging.getLogger(__name__)


class PickSupplier(ABC):
    supplier_id: str

    @abstractmethod
    def attach(self, module: "fabll.Node", part: "PickedPart"): ...


@dataclass(frozen=True)
class PickedPart:
    manufacturer: str
    partno: str
    supplier_partno: str
    supplier: PickSupplier


class PickError(Exception):
    def __init__(self, message: str, *modules: fabll.Node):
        self.message = message
        self.modules = modules

    def __repr__(self):
        return f"{type(self).__name__}({self.modules}, {self.message})"

    def __str__(self):
        return self.message


class PickErrorNotImplemented(PickError):
    def __init__(self, module: fabll.Node):
        message = f"Could not pick part for {module}: Not implemented"
        super().__init__(message, module)


class PickVerificationError(PickError):
    def __init__(self, message: str, *modules: fabll.Node):
        message = f"Post-pick verification failed for picked parts:\n{message}"
        super().__init__(message, *modules)


class PickErrorChildren(PickError):
    def __init__(self, module: fabll.Node, children: dict[fabll.Module, PickError]):
        self.children = children

        message = f"Could not pick parts for children of {module}:\n" + "\n".join(
            f"{m}: caused by {v.message}" for m, v in self.get_all_children().items()
        )
        super().__init__(message, module)

    def get_all_children(self):
        return {
            k: v
            for k, v in self.children.items()
            if not isinstance(v, PickErrorChildren)
        } | {
            module: v2
            for v in self.children.values()
            if isinstance(v, PickErrorChildren)
            for module, v2 in v.get_all_children().items()
        }


class does_not_require_picker_check(fabll.Node):
    pass


# module should be root node
def get_pick_tree(
    module_or_interface_obj: fabll.Node, explore_only: bool = False
) -> Tree["F.Pickable.is_pickable"]:
    # TODO no specialization
    # if module.has_trait(fabll.is_module):
    #     module = module.get_most_special()

    tree = Tree()
    merge_tree = tree

    module = module_or_interface_obj.try_get_trait(fabll.is_module)

    if module:
        traits = module_or_interface_obj.try_get_traits(
            F.Pickable.has_part_picked,
            F.has_part_removed,
            F.Pickable.is_pickable_by_type,
            F.Pickable.is_pickable_by_supplier_id,
        )

        if traits.get(F.Pickable.has_part_picked):
            return tree

        # Handle has_part_removed: create a has_part_picked trait with the removed marker # noqa: E501
        if traits.get(F.has_part_removed):
            picked_trait = fabll.Traits.create_and_add_instance_to(
                module_or_interface_obj, F.Pickable.has_part_picked
            )
            fabll.Traits.create_and_add_instance_to(picked_trait, F.has_part_removed)
            return tree

        explore = True
        if pbt := traits.get(F.Pickable.is_pickable_by_type):
            merge_tree = Tree()
            pickable_trait = pbt.get_trait(F.Pickable.is_pickable)
            tree[pickable_trait] = merge_tree
        elif pbsi := traits.get(F.Pickable.is_pickable_by_supplier_id):
            merge_tree = Tree()
            pickable_trait = pbsi.get_trait(F.Pickable.is_pickable)
            tree[pickable_trait] = merge_tree
        elif pbpn := F.Pickable.is_pickable_by_part_number.try_check_or_convert(module):
            merge_tree = Tree()
            pickable_trait = pbpn.get_trait(F.Pickable.is_pickable)
            tree[pickable_trait] = merge_tree
        else:
            explore = False
        explore_only = explore_only or explore

    module_children = module_or_interface_obj.get_children(
        direct_only=True,
        types=fabll.Node,
        required_trait=fabll.is_module,
    )
    interface_children = module_or_interface_obj.get_children(
        direct_only=True,
        types=fabll.Node,
        required_trait=fabll.is_interface,
    )

    if module and not module_children and not explore_only:
        if module_or_interface_obj.has_trait(F.Footprints.has_associated_footprint):
            logger.warning(f"No pickers for {module_or_interface_obj.get_full_name()}")
        else:
            logger.warning(
                f"ATTENTION: No pickers and no footprint for {module_or_interface_obj.get_full_name()}."  # noqa: E501
                " Will not appear in netlist or pcb."
            )

    for child in module_children + interface_children:
        child_tree = get_pick_tree(child, explore_only=explore_only)
        merge_tree.update(child_tree)

    return tree


def update_pick_tree(
    tree: Tree["F.Pickable.is_pickable"],
) -> tuple[Tree["F.Pickable.is_pickable"], bool]:
    if not tree:
        return tree, False

    filtered_tree = Tree(
        (k, sub[0])
        for k, v in tree.items()
        if not k.get_pickable_node().has_trait(F.Pickable.has_part_picked)
        and not (sub := update_pick_tree(v))[1]
    )
    if not filtered_tree:
        return filtered_tree, True

    return filtered_tree, False


def _list_to_hack_tree(
    modules: Iterable["F.Pickable.is_pickable"],
) -> Tree["F.Pickable.is_pickable"]:
    return Tree({m: Tree() for m in modules})


def find_independent_groups(
    modules: Iterable["F.Pickable.is_pickable"],
) -> list[set["F.Pickable.is_pickable"]]:
    """
    Find groups of modules that are independent of each other.

    Independence is determined by transitive closure through predicates involving a
    module's picked parameters. Picking a module in one such graph component cannot
    influence the constraints derivable for modules in other components.

    TODO: more aggressive splitting by examining predicate expressions
    """
    unique_modules: set[F.Pickable.is_pickable] = set(modules)
    tg = next(iter(modules)).tg

    # Map picked parameters to modules
    all_params: set[F.Parameters.is_parameter] = set()
    p_to_module_map = dict[F.Parameters.is_parameter, F.Pickable.is_pickable_by_type]()
    for m in unique_modules:
        if (
            m_pbt := fabll.Traits(m)
            .get_obj_raw()
            .try_cast(F.Pickable.is_pickable_by_type)
        ):
            for p in m_pbt.get_params():
                all_params.add(p)
                p_to_module_map[p] = m_pbt

    root_preds: set[F.Expressions.is_predicate] = set()
    pred_to_params: dict[
        F.Expressions.is_predicate, set[F.Parameters.is_parameter]
    ] = {}

    # Build cache of params per predicate
    for pred in F.Expressions.is_predicate.bind_typegraph(tg).get_instances():
        expr = pred.as_expression.get()

        # Root predicates only
        if expr.as_operand.get().get_operations(recursive=True, predicates_only=True):
            continue

        # Skip correlation predicates
        if expr.is_non_constraining():
            continue

        params = {
            p
            for leaf in expr.get_operand_leaves_operatable()
            if (p := leaf.as_parameter.try_get())
        }
        pred_to_params[pred] = params
        root_preds.add(pred)

    def get_predicate_neighbors(
        path: list[F.Expressions.is_predicate],
    ) -> list[F.Expressions.is_predicate]:
        current = path[-1]
        return list(
            {
                other_pred
                for param in pred_to_params[current]
                for expr in param.as_operand.get().get_operations(predicates_only=True)
                if (other_pred := expr.try_get_trait(F.Expressions.is_predicate))
                and other_pred in root_preds
                and other_pred != current
            }
        )

    visited_preds: set[F.Expressions.is_predicate] = set()
    pred_components: list[set[F.Expressions.is_predicate]] = []

    # BFS to find predicate components (connected subgraphs)
    for start_pred in root_preds:
        if start_pred in visited_preds:
            continue
        component = bfs_visit(get_predicate_neighbors, [start_pred])
        visited_preds.update(component)
        pred_components.append(component)

    # Map predicate components to parameter components
    p_components: list[set[F.Parameters.is_parameter]] = [
        params_in_component
        for pred_component in pred_components
        if (
            params_in_component := {
                p for pred in pred_component for p in pred_to_params[pred]
            }
        )
    ]

    # Group modules by parameter component membership
    module_components = EquivalenceClasses[F.Pickable.is_pickable](unique_modules)
    for p_component in p_components:
        if p_modules := {
            p_to_module_map[p] for p in p_component if p in p_to_module_map
        }:
            module_components.add_eq(*[n._is_pickable.get() for n in p_modules])

    out = module_components.get()
    logger.info(
        indented_container(
            [{m.get_pickable_node() for m in g} for g in out],
            recursive=True,
        )
    )
    return out


def _infer_uncorrelated_params(tree: Tree["F.Pickable.is_pickable"]):
    """
    Add inferred correlation information.

    We can infer that all parameters used directly for picking are mutually
    uncorrelated.

    IMPORTANT: parameters chosen for is_pickable_by_type must not correspond.
    """
    uncorrelated_params = {
        p
        for m in tree.flat()
        if (pbt := m.get_pickable_node().try_get_trait(F.Pickable.is_pickable_by_type))
        for p in pbt.get_params()
    }

    if len(uncorrelated_params) < 2:
        return

    g = next(iter(uncorrelated_params)).g
    tg = next(iter(uncorrelated_params)).tg
    corr = F.Expressions.Correlated.c(
        *[p.as_operand.get() for p in uncorrelated_params], g=g, tg=tg
    )
    F.Expressions.Not.c(corr, g=g, tg=tg, assert_=True)


def _collect_relevant_params(
    modules: Iterable["F.Pickable.is_pickable"],
) -> list["F.Parameters.can_be_operand"]:
    """Collect all pickable parameters from modules."""
    return [
        p.as_operand.get()
        for m in modules
        if (
            pbt := m.get_parent_of_type(
                F.Pickable.is_pickable_by_type, direct_only=True, include_root=False
            )
        )
        for p in pbt.get_params()
    ]


def _format_pcb_contradiction_error(
    contradiction: Contradiction, tg: fbrk.TypeGraph
) -> str:
    """
    Format a nice error message when PCB constraints conflict with design.

    Checks if any PCB-sourced constraints are involved in the contradiction
    and includes details about the conflicting values.
    """
    base_msg = str(contradiction)

    # Find PCB-sourced constraints
    pcb_constraints = get_pcb_sourced_constraints(tg)
    if not pcb_constraints:
        return base_msg

    # Find which PCB constraints might be involved
    involved_pcb: list[tuple[fabll.Node, has_pcb_source]] = []
    for owner, pcb_source in pcb_constraints:
        # Check if this is a parameter constraint
        if pcb_source.is_param_constraint():
            involved_pcb.append((owner, pcb_source))

    if not involved_pcb:
        return base_msg

    # Build a nice error message
    lines = [
        "Design constraints conflict with values saved in PCB.",
        "",
        "The following PCB-saved values conflict with your design:",
    ]

    for owner, pcb_source in involved_pcb:
        module_path = pcb_source.module_path
        param_name = pcb_source.param_name

        # Try to get the PCB value from the constraint
        pcb_value_str = "unknown"
        if owner.has_trait(F.Expressions.is_expression):
            expr = owner.get_trait(F.Expressions.is_expression)
            operands = expr.get_operands()
            for operand in operands:
                if lit := operand.as_literal.try_get():
                    pcb_value_str = lit.pretty_str()
                    break

        lines.append(f"  - {module_path}.{param_name}: PCB has {pcb_value_str}")

    lines.extend(
        [
            "",
            "To fix this, either:",
            "  1. Update your design constraints to match the PCB values",
            "  2. Run a regular build (without --keep-picked-parts) to re-pick parts",
            "",
            f"Original error: {contradiction.msg}",
        ]
    )

    return "\n".join(lines)


@dataclass(frozen=True)
class PickNodeData:
    depth: int
    module_count: int
    branching_factor: int
    module_name: str

    def __repr__(self) -> str:
        return f"{self.module_name} (d={self.depth} b={self.branching_factor})"


@dataclass
class PickWorkItem:
    modules: set["F.Pickable.is_pickable"]
    solver: Solver
    depth: int
    parent_key: PickNodeData | None = None


def _pick_tree(
    initial_modules: set["F.Pickable.is_pickable"],
    solver: Solver,
    picker_lib,
    progress: Advancable | None,
) -> Tree[PickNodeData]:
    """
    Pick all modules using breadth-first iteration with batched API calls.

    Algorithm:
    1. Expand: Find independent groups for all work items at current level
    2. Batch fetch: Collect candidates for all modules at this level
    3. Pick and advance: Select parts, prepare work items for next level
    """
    work_queue = deque([PickWorkItem(initial_modules, solver, depth=0)])
    pick_tree: Tree[PickNodeData] = Tree()
    subtrees: dict[PickNodeData | None, Tree[PickNodeData]] = {None: pick_tree}

    while work_queue:
        expanded: deque[PickWorkItem] = deque()

        for item in work_queue:
            if not (relevant := _collect_relevant_params(item.modules)):
                continue

            g, tg = next(iter(relevant)).g, next(iter(relevant)).tg
            item.solver.simplify(g, tg, terminal=False, relevant=relevant)

            groups = find_independent_groups(item.modules)
            group_solvers = [next(item.solver.fork()) for _ in range(len(groups))]

            for group, group_solver in zip(groups, group_solvers):
                expanded.append(
                    PickWorkItem(
                        modules=group,
                        solver=group_solver,
                        depth=item.depth,
                        parent_key=item.parent_key,
                    )
                )

        if not expanded:
            break

        depth = expanded[0].depth
        logger.info(
            f"[depth={depth}] Processing {len(expanded)} groups, "
            f"{sum(len(item.modules) for item in expanded)} total modules"
        )

        all_modules = _list_to_hack_tree(m for item in expanded for m in item.modules)
        all_candidates = picker_lib.get_candidates(all_modules, solver)
        next_queue: deque[PickWorkItem] = deque()

        for item in expanded:
            group_candidates = {m: all_candidates[m] for m in item.modules}
            if no_candidates := [m for m, cs in group_candidates.items() if not cs]:
                raise PickError(
                    f"No candidates found for {no_candidates}", *no_candidates
                )

            # Heuristic: pick most-constrained module (fewest candidates)
            module = min(item.modules, key=lambda m: len(group_candidates[m]))
            part = next(iter(group_candidates[module]))

            module_name = module.get_pickable_node().get_full_name()
            logger.info(f"  Picking {module_name}")
            picker_lib.attach_single_no_check(module, part, item.solver)

            if progress:
                progress.advance()

            node_data = PickNodeData(
                depth=item.depth,
                module_count=len(item.modules),
                branching_factor=len(expanded),
                module_name=module_name,
            )
            parent_tree = subtrees[item.parent_key]
            child_tree: Tree[PickNodeData] = Tree()
            parent_tree[node_data] = child_tree
            subtrees[node_data] = child_tree
            if remaining := item.modules - {module}:
                next_queue.append(
                    PickWorkItem(
                        modules=remaining,
                        solver=item.solver,
                        depth=item.depth + 1,
                        parent_key=node_data,
                    )
                )

        work_queue = next_queue

    return pick_tree


def pick_topologically(
    tree: Tree["F.Pickable.is_pickable"],
    solver: Solver,
    progress: Advancable | None = None,
):
    import faebryk.libs.picker.api.picker_lib as picker_lib

    def _pick_explicit_modules(explicit_modules: list["F.Pickable.is_pickable"]):
        explicit_parts = picker_lib._find_modules(
            _list_to_hack_tree(explicit_modules), solver
        )
        for m, parts in explicit_parts.items():
            part = parts[0]
            picker_lib.attach_single_no_check(m, part, solver)
            if progress:
                progress.advance()

    timings = Times(name="pick")
    tree_backup = set(tree.keys())
    _pick_count = len(tree)

    logger.info(f"Picking {_pick_count} modules")

    if explicit_modules := [
        m
        for m in tree.keys()
        if m.get_pickable_node().has_trait(F.Pickable.is_pickable_by_part_number)
        or m.get_pickable_node().has_trait(F.Pickable.is_pickable_by_supplier_id)
    ]:
        _pick_explicit_modules(explicit_modules)
        tree, _ = update_pick_tree(tree)

    _infer_uncorrelated_params(tree)

    timings.add("setup")

    with timings.measure("pick tree"):
        if all_modules := set(tree.keys()):
            pick_tree: Tree[PickNodeData] = _pick_tree(
                all_modules, solver, picker_lib, progress
            )
            logger.info(
                "Picking tree (d=depth, b=branching_factor):\n" + pick_tree.pretty()
            )
        else:
            pick_tree = Tree()

    if _pick_count:
        logger.info(f"Picked parts in {timings.get_formatted('pick tree')}")

    if relevant := _collect_relevant_params(tree_backup):
        g, tg = next(iter(relevant)).g, next(iter(relevant)).tg

        with timings.measure("verify design"):
            logger.info("Verify design")
            try:
                solver.simplify(g, tg, terminal=True, relevant=relevant)
            except Contradiction as e:
                error_msg = _format_pcb_contradiction_error(e, tg)
                raise PickVerificationError(error_msg, *tree_backup) from e
        logger.info(f"Verified design in {timings.get_formatted('verify design')}")


# TODO should be a Picker
@debug_perf
def pick_parts_recursively(
    module: fabll.Node, solver: Solver, progress: Advancable | None = None
):
    pick_tree = get_pick_tree(module)
    if progress:
        progress.set_total(len(pick_tree))

    try:
        pick_topologically(pick_tree, solver, progress)
    # FIXME: This does not get called anymore
    except PickErrorChildren as e:
        failed_parts = e.get_all_children()
        for m, sube in failed_parts.items():
            logger.error(
                f"Could not find pick for {m}:\n {sube.message}\n"
                f"Params:\n{indent(m.pretty_params(solver), prefix=' ' * 4)}"
            )
        raise
