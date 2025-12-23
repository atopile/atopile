# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from textwrap import indent
from typing import TYPE_CHECKING, Iterable

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.solver import Solver
from faebryk.core.solver.utils import Contradiction
from faebryk.libs.test.times import Times
from faebryk.libs.util import (
    Advancable,
    ConfigFlag,
    EquivalenceClasses,
    KeyErrorAmbiguous,  # noqa: F401
    Tree,
    debug_perf,
    groupby,
    indented_container,
)

if TYPE_CHECKING:
    from faebryk.libs.picker.api.models import Component

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


class NotCompatibleException(Exception):
    def __init__(
        self,
        module: fabll.Node,
        component: "Component",
        param: F.Parameters.is_parameter_operatable | None = None,
        c_range: F.Literals.is_literal | None = None,
    ):
        self.module = module
        self.component = component
        self.param = param
        self.c_range = c_range

        if param is None or c_range is None:
            msg = f"{component.lcsc_display} is not compatible with `{module}`"
        else:
            msg = (
                f"`{param}` ({param.force_extract_literal().pretty_repr()}) is not "
                f"compatible with {component.lcsc_display} ({c_range.pretty_repr()})"
            )

        super().__init__(msg)


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
    modules: Iterable["F.Pickable.is_pickable"], solver: Solver
) -> list[set["F.Pickable.is_pickable"]]:
    """
    Find groups of modules that are independent of each other.
    """
    unique_modules: set[F.Pickable.is_pickable] = set(modules)

    # partition params into cliques by expression involvement
    p_cliques = EquivalenceClasses[F.Parameters.is_parameter]()
    tg = list(modules)[0].tg  # FIXME

    # get root predicates
    root_preds = [
        pred
        for pred in F.Expressions.is_predicate.bind_typegraph(tg).get_instances()
        if not pred.as_expression.get()
        .as_operand.get()
        .get_operations(recursive=True, predicates_only=True)
    ]
    # add related parameters for non-aliased paramops
    for root_pred in root_preds:
        pred_e = root_pred.as_expression.get()
        leaves = pred_e.get_operand_leaves_operatable()
        p_cliques.add_eq(
            *[
                p
                for leaf in leaves
                if (p := leaf.as_parameter.try_get())
                and leaf.try_get_aliased_literal() is None
            ]
        )

    # partition modules into cliques by parameter clique membership
    module_cliques = EquivalenceClasses[F.Pickable.is_pickable](unique_modules)
    p_to_module_map = dict[F.Parameters.is_parameter, F.Pickable.is_pickable_by_type]()
    for m in unique_modules:
        if not (
            m_pbt := fabll.Traits(m)
            .get_obj_raw()
            .try_cast(F.Pickable.is_pickable_by_type)
        ):
            continue
        params = m_pbt.get_params()
        for p in params:
            p_to_module_map[p] = m_pbt

    for po_clique in p_cliques.get():
        p_modules = {p_to_module_map[p] for p in po_clique if p in p_to_module_map}
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


def _get_graph(*nodes: fabll.Node) -> tuple[graph.GraphView, fbrk.TypeGraph]:
    gs = groupby(nodes, key=lambda m: m.g.get_self_node().node().get_uuid())
    assert len(gs) == 1
    m = next(iter(gs.values()))[0]
    g = m.g
    tg = m.tg
    return g, tg


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

    timings.add("setup")
    relevant = [rp for m in tree.keys() for rp in _relevant_params(m)]
    with timings.as_global("parallel slow-pick"):
        if relevant:
            g = relevant[0].g
            tg = relevant[0].tg
            logger.info(f"Simplifying with {len(relevant)} relevant parameters")
            with timings.as_global("simplify"):
                solver.simplify(g, tg, terminal=True, relevant=relevant)
            logger.info(f"Solved in {timings.get_formatted('simplify')}")
            with timings.as_global("get candidates"):
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
                with timings.context("simplify"):
                    solver.simplify(g, tg, terminal=True, relevant=relevant)
                logger.info(f"Solved in {(time.perf_counter() - now) * 1000:.3f}ms")
                with timings.as_global("get candidates"):
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
