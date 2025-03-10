# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum
from textwrap import indent
from typing import TYPE_CHECKING, Any, Iterable

from rich.progress import Progress

import faebryk.library._F as F
from atopile.cli.console import error_console
from faebryk.core.cpp import Graph
from faebryk.core.graph import GraphFunctions
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.parameter import (
    ConstrainableExpression,
    Parameter,
)
from faebryk.core.solver.solver import LOG_PICK_SOLVE, NotDeducibleException, Solver
from faebryk.core.solver.utils import Contradiction, get_graphs
from faebryk.libs.sets.sets import P_Set
from faebryk.libs.test.times import Times
from faebryk.libs.util import (
    ConfigFlag,
    EquivalenceClasses,
    KeyErrorAmbiguous,
    KeyErrorNotFound,
    Tree,
    indented_container,
    partition,
    try_or,
)

if TYPE_CHECKING:
    from faebryk.libs.picker.api.models import Component
    from faebryk.libs.picker.localpick import PickerOption


NO_PROGRESS_BAR = ConfigFlag("NO_PROGRESS_BAR", default=False)

logger = logging.getLogger(__name__)


class DescriptiveProperties(StrEnum):
    manufacturer = "Manufacturer"
    partno = "Partnumber"
    datasheet = "Datasheet"


class Supplier(ABC):
    @abstractmethod
    def attach(self, module: Module, part: "PickerOption"): ...


@dataclass(frozen=True)
class Part:
    partno: str
    supplier: Supplier


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


# FIXME: remove? uses wrong console
class PickerProgress:
    def __init__(self, tree: Tree[Module]):
        self.tree = tree
        self.progress = Progress(
            disable=bool(NO_PROGRESS_BAR),
            transient=True,
            # This uses the error console to properly interleave with logging
            console=error_console,
        )
        leaves = list(tree.leaves())
        count = len(leaves)

        logger.info(f"Picking parts for {count} leaf modules")
        self.task = self.progress.add_task("Picking", total=count)

    def advance(self, module: Module):
        leaf_count = len(list(self.tree.get_subtree(module).leaves()))
        # module is leaf
        if not leaf_count:
            leaf_count = 1
        self.progress.advance(self.task, leaf_count)

    @contextmanager
    def context(self):
        with self.progress:
            yield self


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


# TODO: tests & use
# TODO: consider grouping by relation
# e.g if its just aliases (all same repr), then very different
def find_independent_groups(
    modules: Iterable[Module], solver: Solver
) -> list[set[Module]]:
    """
    Find groups of modules that are independent of each other.
    """
    from faebryk.core.solver.defaultsolver import DefaultSolver

    if (
        not isinstance(solver, DefaultSolver)
        or (state := solver.reusable_state) is None
    ):
        module_eqs = EquivalenceClasses[Module](modules)
        for e in GraphFunctions(*get_graphs(modules)).nodes_of_type(
            ConstrainableExpression
        ):
            if not e.constrained:
                continue
            ps = e.get_operand_parameters(recursive=True)
            modules = {
                m
                for p in ps
                if (parent := p.get_parent()) is not None
                and isinstance(m := parent[0], Module)
            }
            module_eqs.add_eq(*modules)
        return module_eqs.get()

    graphs = EquivalenceClasses()
    graph_to_m = defaultdict[Graph, set[Module]](set)
    for m in modules:
        params = m.get_trait(F.is_pickable_by_type).get_parameters().values()
        new_params = {state.data.mutation_map.map_forward(p).maps_to for p in params}
        m_graphs = get_graphs(new_params)
        graphs.add_eq(*m_graphs)
        for g in m_graphs:
            graph_to_m[g].add(m)

    graph_groups: list[set[Graph]] = graphs.get()
    module_groups = [{m for g in gg for m in graph_to_m[g]} for gg in graph_groups]
    return module_groups


def pick_topologically(
    tree: Tree[Module],
    solver: Solver,
    progress: PickerProgress | None = None,
):
    # TODO implement backtracking

    from faebryk.libs.picker.api.picker_lib import (
        attach_single_no_check,
        check_and_attach_candidates,
        get_candidates,
    )

    tree_backup = set(tree.keys())
    timings = Times(name="pick")

    if LOG_PICK_SOLVE:
        pickable_modules = next(iter(tree.iter_by_depth()))
        names = sorted(p.get_full_name(types=True) for p in pickable_modules)
        logger.info(f"Picking parts for \n\t{'\n\t'.join(names)}")

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
            candidates = list(get_candidates(_tree, solver).items())
        if LOG_PICK_SOLVE:
            logger.info(
                "Candidates: \n\t"
                f"{'\n\t'.join(f'{m}: {len(p)}' for m, p in candidates)}"
            )
        return candidates

    def _get_single_candidate(module: Module):
        parts = _get_candidates(Tree({module: Tree()}))[0][1]
        return parts[0]

    def _update_progress(done: list[tuple[Module, Any]] | Module):
        if not progress:
            return

        if isinstance(done, Module):
            modules = [done]
        else:
            modules = [m for m, _ in done]

        for m in modules:
            progress.advance(m)

    timings.add("setup")

    candidates = _get_candidates(tree)
    _pick_count = len(candidates)

    # heuristic: pick all single part modules in one go
    # TODO split explicit from single-candidate
    with timings.as_global("pick single candidate modules"):
        single_part_modules = [
            (module, parts[0])
            for module, parts in candidates
            if len(parts) == 1 or module.has_trait(F.has_explicit_part)
        ]
        if single_part_modules:
            logger.info("Picking single part modules")
            try:
                check_and_attach_candidates(
                    single_part_modules, solver, allow_not_deducible=True
                )
            except Contradiction as e:
                raise PickError(
                    "Could not pick all explicitly-specified parts."
                    f" Likely contradicting constraints: {str(e)}",
                    *[m for m, _ in single_part_modules],
                )
            except (NotCompatibleException, NotDeducibleException) as e:
                raise PickError(
                    f"Could not pick all explicitly-specified parts: {e}",
                    *[m for m, _ in single_part_modules],
                )
            _update_progress(single_part_modules)

            tree, _ = update_pick_tree(tree)
            candidates = _get_candidates(tree)

    with timings.as_global("singleton group fast-pick"):
        pickable_modules = [m for (m, _) in candidates]
        # solver.simplify(*pickable_modules)
        groups = find_independent_groups(pickable_modules, solver)
        singletons = {next(iter(g)) for g in groups if len(g) == 1}
        singleton_candidates = [(m, cs[0]) for m, cs in candidates if m in singletons]
        if singleton_candidates:
            logger.info("Picking independent parts")
            try:
                check_and_attach_candidates(
                    singleton_candidates, solver, allow_not_deducible=True
                )
            except Contradiction as e:
                raise PickError(
                    "Could not pick all independent parts." f"  {str(e)}",
                    *singletons,
                )
            except (NotCompatibleException, NotDeducibleException):
                # TODO: more information
                raise PickError(
                    "Could not pick all independent parts",
                    *singletons,
                )
            _update_progress(singleton_candidates)
            tree, _ = update_pick_tree(tree)
            candidates = [(m, cs) for m, cs in candidates if m not in singletons]

    # Works by looking for each module again for compatible parts
    # If no compatible parts are found,
    #   it means we need to backtrack or there is no solution
    with timings.as_global("slow-pick", context=True):
        if candidates:
            logger.warning("Falling back to extremely slow picking one by one")
            for module in tree:
                if LOG_PICK_SOLVE:
                    logger.info(f"Picking part for {module}")
                part = _get_single_candidate(module)
                attach_single_no_check(module, part, solver)
                _update_progress(module)

    if candidates:
        logger.info(f"Slow-picked parts in {timings.get_formatted('slow-pick')}")

    logger.info(f"Picked complete: picked {_pick_count} parts")
    logger.info("Verify design")
    try:
        solver.update_superset_cache(*tree_backup)
    except Contradiction as e:
        raise PickVerificationError(str(e), *tree_backup) from e


# TODO should be a Picker
def pick_part_recursively(module: Module, solver: Solver):
    pick_tree = get_pick_tree(module)
    if LOG_PICK_SOLVE:
        logger.info(f"Pick tree:\n{pick_tree.pretty()}")

    check_missing_picks(module)

    try:
        pick_topologically(pick_tree, solver)
    # FIXME: This does not get called anymore
    except PickErrorChildren as e:
        failed_parts = e.get_all_children()
        for m, sube in failed_parts.items():
            logger.error(
                f"Could not find pick for {m}:\n {sube.message}\n"
                f"Params:\n{indent(m.pretty_params(solver), prefix=' '*4)}"
            )
        raise
