# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from textwrap import indent
from typing import TYPE_CHECKING, Iterable

import faebryk.library._F as F
from faebryk.core.cpp import Graph
from faebryk.core.graph import GraphFunctions
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.parameter import (
    ConstrainableExpression,
    Is,
    Parameter,
    ParameterOperatable,
)
from faebryk.core.solver.solver import LOG_PICK_SOLVE, Solver
from faebryk.core.solver.utils import Contradiction, ContradictionByLiteral, get_graphs
from faebryk.libs.sets.sets import P_Set
from faebryk.libs.test.times import Times
from faebryk.libs.util import (
    Advancable,
    ConfigFlag,
    EquivalenceClasses,
    KeyErrorAmbiguous,
    KeyErrorNotFound,
    Tree,
    indented_container,
    partition,
    try_or,
    unique,
)

if TYPE_CHECKING:
    from faebryk.libs.picker.api.models import Component
    from faebryk.libs.picker.localpick import PickerOption


NO_PROGRESS_BAR = ConfigFlag("NO_PROGRESS_BAR", default=False)

logger = logging.getLogger(__name__)


class PickSupplier(ABC):
    supplier_id: str

    @abstractmethod
    def attach(self, module: Module, part: "PickerOption"): ...


@dataclass(frozen=True)
class PickedPart:
    manufacturer: str
    partno: str
    supplier_partno: str
    supplier: PickSupplier


class PickError(Exception):
    def __init__(self, message: str, *modules: Module):
        self.message = message
        self.modules = modules

    def __repr__(self):
        return f"{type(self).__name__}({self.modules}, {self.message})"

    def __str__(self):
        return self.message


class PickErrorNotImplemented(PickError):
    def __init__(self, module: Module):
        message = f"Could not pick part for {module}: Not implemented"
        super().__init__(message, module)


class PickVerificationError(PickError):
    def __init__(self, message: str, *modules: Module):
        message = f"Post-pick verification failed for picked parts:\n{message}"
        super().__init__(message, *modules)


class PickErrorChildren(PickError):
    def __init__(self, module: Module, children: dict[Module, PickError]):
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
        module: Module,
        component: "Component",
        param: Parameter | None = None,
        c_range: P_Set | None = None,
    ):
        self.module = module
        self.component = component
        self.param = param
        self.c_range = c_range

        if param is None or c_range is None:
            msg = f"{component.lcsc_display} is not compatible with `{module}`"
        else:
            msg = (
                f"`{param}` ({param.try_get_literal_subset()}) is not "
                f"compatible with {component.lcsc_display} ({c_range})"
            )

        super().__init__(msg)


class does_not_require_picker_check(Parameter.TraitT.decless()):
    pass


def get_pick_tree(module: Module | ModuleInterface) -> Tree[Module]:
    if isinstance(module, Module):
        module = module.get_most_special()

    tree = Tree()
    merge_tree = tree

    if module.has_trait(F.has_part_picked):
        return tree

    if module.has_trait(F.is_pickable):
        merge_tree = Tree()
        tree[module] = merge_tree

    for child in module.get_children(
        direct_only=True, types=(Module, ModuleInterface), include_root=False
    ):
        child_tree = get_pick_tree(child)
        merge_tree.update(child_tree)

    return tree


def update_pick_tree(tree: Tree[Module]) -> tuple[Tree[Module], bool]:
    if not tree:
        return tree, False

    filtered_tree = Tree(
        (k, sub[0])
        for k, v in tree.items()
        if not k.has_trait(F.has_part_picked) and not (sub := update_pick_tree(v))[1]
    )
    if not filtered_tree:
        return filtered_tree, True

    return filtered_tree, False


def check_missing_picks(module: Module):
    # - not skip self pick
    # - no parent with part picked
    # - not specialized
    # - no module children
    # - no parent with picker

    missing = module.get_children_modules(
        types=Module,
        direct_only=False,
        include_root=True,
        # not specialized
        most_special=True,
        # leaf == no children
        f_filter=lambda m: not m.get_children_modules(
            types=Module, f_filter=lambda x: not isinstance(x, F.Footprint)
        )
        and not isinstance(m, F.Footprint)
        # no parent with part picked
        and not try_or(
            lambda: m.get_parent_with_trait(F.has_part_picked),
            default=False,
            catch=KeyErrorNotFound,
        )
        # no parent with picker
        and not try_or(
            lambda: try_or(
                lambda: m.get_parent_with_trait(F.is_pickable),
                default=False,
                catch=KeyErrorNotFound,
            ),
            default=True,
            catch=KeyErrorAmbiguous,
        ),
    )

    if missing:
        no_fp, with_fp = map(
            list, partition(lambda m: m.has_trait(F.has_footprint), missing)
        )

        if with_fp:
            logger.warning(f"No pickers for {indented_container(with_fp)}")
        if no_fp:
            logger.warning(
                f"No pickers and no footprint for {indented_container(no_fp)}."
                "\nATTENTION: These modules will not appear in netlist or pcb."
            )


def find_independent_groups(
    modules: Iterable[Module], solver: Solver
) -> list[set[Module]]:
    """
    Find groups of modules that are independent of each other.
    """
    from faebryk.core.solver.defaultsolver import DefaultSolver

    modules = set(modules)

    if (
        not isinstance(solver, DefaultSolver)
        or (state := solver.reusable_state) is None
    ):
        # Find params aliased to lits
        aliased = EquivalenceClasses[ParameterOperatable]()
        lits = dict[ParameterOperatable, ParameterOperatable.Literal]()
        for e in GraphFunctions(*get_graphs(modules)).nodes_of_type(Is):
            if not e.constrained:
                continue
            aliased.add_eq(*e.operatable_operands)
            if e.get_operand_literals():
                lits[e.get_operand_operatables().pop()] = next(
                    iter(e.get_operand_literals().values())
                )
        for alias_group in aliased.get():
            lits_eq = unique((lits[p] for p in alias_group if p in lits), lambda x: x)
            if not lits_eq:
                continue
            if len(lits_eq) > 1:
                # TODO
                raise ContradictionByLiteral("", [], [], None)
            for p in alias_group:
                lits[p] = lits_eq[0]

        # find params related to each other
        param_eqs = EquivalenceClasses[Parameter]()
        for e in GraphFunctions(*get_graphs(modules)).nodes_of_type(
            ConstrainableExpression
        ):
            if not e.constrained:
                continue
            ps = e.get_operand_parameters(recursive=True)
            ps.difference_update(lits.keys())
            param_eqs.add_eq(*ps)

        # find modules that are dependent on each other
        module_eqs = EquivalenceClasses[Module](modules)
        for p_eq in param_eqs.get():
            p_modules = {
                m
                for p in p_eq
                if (parent := p.get_parent()) is not None
                and isinstance(m := parent[0], Module)
                and m in modules
            }
            module_eqs.add_eq(*p_modules)
        out = module_eqs.get()
        logger.debug(indented_container(out, recursive=True))
        return out

    graphs = EquivalenceClasses()
    graph_to_m = defaultdict[Graph, set[Module]](set)
    for m in modules:
        params = m.get_trait(F.is_pickable_by_type).params
        new_params = {state.data.mutation_map.map_forward(p).maps_to for p in params}
        m_graphs = get_graphs(new_params)
        graphs.add_eq(*m_graphs)
        for g in m_graphs:
            graph_to_m[g].add(m)

    graph_groups: list[set[Graph]] = graphs.get()
    module_groups = [{m for g in gg for m in graph_to_m[g]} for gg in graph_groups]
    return module_groups


def _list_to_hack_tree(modules: Iterable[Module]) -> Tree[Module]:
    return Tree({m: Tree() for m in modules})


def pick_topologically(
    tree: Tree[Module], solver: Solver, progress: Advancable | None = None
):
    # TODO implement backtracking

    import faebryk.libs.picker.api.picker_lib as picker_lib

    def _pick_explicit_modules(explicit_modules: list[Module]):
        logger.info(f"Picking {len(explicit_modules)} explicit parts")
        explicit_parts = picker_lib._find_modules(
            _list_to_hack_tree(explicit_modules), solver
        )
        for m, parts in explicit_parts.items():
            part = parts[0]
            picker_lib.attach_single_no_check(m, part, solver)
            if progress:
                progress.advance()

    def _get_candidates(_tree: Tree[Module]):
        # with timings.as_global("pre-solve"):
        #    solver.simplify(*get_graphs(tree.keys()))
        try:
            with timings.as_global("new estimates"):
                # Rerun solver for new system
                solver.update_superset_cache(*_tree)
        except Contradiction as e:
            raise PickError(str(e), *_tree.keys())
        with timings.as_global("get candidates"):
            candidates = picker_lib.get_candidates(_tree, solver)
        if LOG_PICK_SOLVE:
            logger.info(
                "Candidates: \n\t"
                f"{'\n\t'.join(f'{m}: {len(p)}' for m, p in candidates.items())}"
            )
        return candidates

    timings = Times(name="pick")

    tree_backup = set(tree.keys())
    _pick_count = len(tree)

    logger.info(f"Picking {_pick_count} modules")

    if explicit_modules := [
        m
        for m in tree.keys()
        if m.has_trait(F.is_pickable_by_part_number)
        or m.has_trait(F.is_pickable_by_supplier_id)
    ]:
        _pick_explicit_modules(explicit_modules)
        tree, _ = update_pick_tree(tree)

    timings.add("setup")

    # Works by looking for each module again for compatible parts
    # If no compatible parts are found,
    #   it means we need to backtrack or there is no solution
    with timings.as_global("parallel slow-pick", context=True):
        if tree:
            logger.info(f"Picking {len(tree)} modules in parallel")
        while tree:
            try:
                candidates = _get_candidates(tree)
            except Contradiction as e:
                # TODO better error, also remove from get_candidates
                raise PickError(
                    "Contradiction in system."
                    "Unfixable due to lack of backtracking." + str(e),
                    *[],
                )
            groups = find_independent_groups(candidates.keys(), solver)
            # pick module with least candidates first
            picked = [
                (
                    m := min(group, key=lambda _m: len(candidates[_m])),
                    candidates[m][0],
                )
                for group in groups
            ]
            logger.info(
                f"Picking {len(groups)} independent groups: "
                f"{indented_container([m for m, _ in picked])}"
            )
            for m, part in picked:
                picker_lib.attach_single_no_check(m, part, solver)
                if progress:
                    progress.advance()

            tree, _ = update_pick_tree(tree)

    if _pick_count:
        logger.info(
            f"Slow-picked parts in {timings.get_formatted('parallel slow-pick')}"
        )

    logger.info(f"Picked complete: picked {_pick_count} parts")
    logger.info("Verify design")
    try:
        solver.update_superset_cache(*tree_backup)
    except Contradiction as e:
        raise PickVerificationError(str(e), *tree_backup) from e


# TODO should be a Picker
def pick_part_recursively(
    module: Module, solver: Solver, progress: Advancable | None = None
):
    pick_tree = get_pick_tree(module)
    if progress:
        progress.set_total(len(pick_tree))
    check_missing_picks(module)

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
