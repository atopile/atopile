# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from itertools import combinations
from textwrap import indent
from typing import Iterable

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.solver import Solver
from faebryk.core.solver.utils import Contradiction
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


def _get_anticorrelated_pairs(tg) -> set[frozenset["F.Parameters.is_parameter"]]:
    """
    Collect all parameter pairs that are explicitly marked as uncorrelated
    via Not(Correlated(...)) expressions.
    """
    out: set[frozenset[F.Parameters.is_parameter]] = set()

    for expr in F.Expressions.Correlated.bind_typegraph(tg).get_instances():
        ops = expr.can_be_operand.get().get_operations(
            recursive=False, predicates_only=False
        )

        is_negated = any(op.try_cast(F.Expressions.Not) is not None for op in ops)

        if not is_negated:
            continue

        corr_params = [
            p
            for leaf in expr.is_expression.get().get_operand_leaves_operatable()
            if (p := leaf.as_parameter.try_get())
        ]

        for p1, p2 in combinations(corr_params, 2):
            out.add(frozenset([p1, p2]))

    return out


def find_independent_groups(
    modules: Iterable["F.Pickable.is_pickable"], solver: Solver
) -> list[set["F.Pickable.is_pickable"]]:
    """
    Find groups of modules that are independent of each other.

    Independence is determined by:
    - no transitive expression involvement (distinct cliques)
    - explicit Not(Correlated(...)) overrides transitive relationships
    """
    unique_modules: set[F.Pickable.is_pickable] = set(modules)
    tg = list(modules)[0].tg  # FIXME

    anticorrelated_pairs = _get_anticorrelated_pairs(tg)

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

    root_preds: set[F.Expressions.is_expression] = {
        pred.as_expression.get()
        for pred in F.Expressions.is_predicate.bind_typegraph(tg).get_instances()
        if not pred.as_expression.get()
        .as_operand.get()
        .get_operations(recursive=True, predicates_only=True)
    }

    # Traverse parameter → expression → other parameters
    def get_neighbors(
        path: list[F.Parameters.is_parameter],
    ) -> list[F.Parameters.is_parameter]:
        current = path[-1]
        neighbors: set[F.Parameters.is_parameter] = set()

        for expr in current.as_operand.get().get_operations(predicates_only=True):
            if (
                expr_e := expr.get_trait(F.Expressions.is_expression)
            ) not in root_preds:
                continue

            for leaf in expr_e.get_operand_leaves_operatable():
                if (p := leaf.as_parameter.try_get()) and p != current:
                    # Anti-correlation breaks the transitive chain
                    if frozenset({current, p}) not in anticorrelated_pairs:
                        neighbors.add(p)

        return list(neighbors)

    visited: set[F.Parameters.is_parameter] = set()
    p_cliques: list[set[F.Parameters.is_parameter]] = []

    for start_p in all_params:
        if start_p in visited:
            continue
        component = bfs_visit(get_neighbors, [start_p])
        visited.update(component)
        p_cliques.append(component)

    # Group modules by parameter clique membership
    module_cliques = EquivalenceClasses[F.Pickable.is_pickable](unique_modules)
    for p_clique in p_cliques:
        p_modules = {p_to_module_map[p] for p in p_clique if p in p_to_module_map}
        if p_modules:
            module_cliques.add_eq(*[n._is_pickable.get() for n in p_modules])

    out = module_cliques.get()
    logger.debug(
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

    F.Expressions.Not.c(
        F.Expressions.Correlated.c(
            *[p.as_operand.get() for p in uncorrelated_params], g=g, tg=tg
        ),
        g=g,
        tg=tg,
        assert_=True,
    )


def pick_topologically(
    tree: Tree["F.Pickable.is_pickable"],
    solver: Solver,
    progress: Advancable | None = None,
):
    # TODO implement backtracking

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

    def _relevant_params(m: F.Pickable.is_pickable) -> set[F.Parameters.can_be_operand]:
        pbt = m.get_parent_of_type(
            F.Pickable.is_pickable_by_type, direct_only=True, include_root=False
        )
        if not pbt:
            return set()
        params = pbt.get_params()
        return {p.as_operand.get() for p in params}

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
    relevant = [rp for m in tree.keys() for rp in _relevant_params(m)]
    with timings.measure("parallel slow-pick"):
        if relevant:
            g = relevant[0].g
            tg = relevant[0].tg
            logger.info(f"Simplifying with {len(relevant)} relevant parameters")
            with timings.measure("simplify"):
                solver.simplify(g, tg, terminal=True, relevant=relevant)
            logger.info(f"Solved in {timings.get_formatted('simplify')}")
            with timings.measure("get candidates"):
                candidates = picker_lib.get_candidates(tree, solver)
            no_candidates = [m for m, cs in candidates.items() if not cs]
            if no_candidates:
                raise PickError(
                    f"No candidates found for {no_candidates}", *no_candidates
                )

            while tree:
                groups = find_independent_groups(tree.keys(), solver)
                # pick module with least candidates first
                picked = [
                    (
                        m := min(group, key=lambda _m: len(candidates[_m])),
                        candidates[m][0],
                    )
                    for group in groups
                ]
                logger.info(f"Picking {len(groups)} independent groups")
                for m, part in picked:
                    logger.info(f"Picking {m.get_pickable_node()}")
                    picker_lib.attach_single_no_check(m, part, solver)
                    if progress:
                        progress.advance()
                tree, _ = update_pick_tree(tree)
                if not tree:
                    break
                relevant = [rp for m in tree.keys() for rp in _relevant_params(m)]
                g = relevant[0].g
                tg = relevant[0].tg
                if not relevant:
                    break
                now = time.perf_counter()
                with timings.measure("simplify"):
                    solver.simplify(g, tg, terminal=True, relevant=relevant)
                logger.info(f"Solved in {(time.perf_counter() - now) * 1000:.3f}ms")
                with timings.measure("get candidates"):
                    candidates = picker_lib.get_candidates(tree, solver)
                no_candidates = [m for m, cs in candidates.items() if not cs]
                if no_candidates:
                    raise PickError(
                        f"No candidates found for {no_candidates}", *no_candidates
                    )

    if _pick_count:
        logger.info(
            f"Slow-picked parts in {timings.get_formatted('parallel slow-pick')}"
        )

    logger.info(f"Picked complete: picked {_pick_count} parts")
    relevant = [rp for m in tree_backup for rp in _relevant_params(m)]
    if relevant:
        with timings.measure("verify design"):
            logger.info("Verify design")
            try:
                # hack
                n = next(iter(relevant), None)
                if n:
                    g = n.g
                    tg = n.tg
                    solver.simplify(g, tg, terminal=True, relevant=relevant)
            except Contradiction as e:
                raise PickVerificationError(str(e), *tree_backup) from e
        logger.info(f"Verified design in {timings.get_formatted('verify design')}")
    else:
        logger.info("No relevant parameters to verify design with")


# TODO should be a Picker
@debug_perf
def pick_part_recursively(
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
