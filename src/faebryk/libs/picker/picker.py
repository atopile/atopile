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
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.parameter import (
    Parameter,
)
from faebryk.core.solver.solver import LOG_PICK_SOLVE, NotDeducibleException, Solver
from faebryk.core.solver.utils import Contradiction, get_graphs
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
    def __init__(self, message: str, *module: Module):
        super().__init__(message)
        self.message = message
        self.module = module

    def __repr__(self):
        return f"{type(self).__name__}({self.module}, {self.message})"


class PickErrorNotImplemented(PickError):
    def __init__(self, module: Module):
        message = f"Could not pick part for {module}: Not implemented"
        super().__init__(message, module)


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
    pass


class does_not_require_picker_check(Parameter.TraitT.decless()):
    pass


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


def update_pick_tree(tree: Tree[Module]):
    # TODO: have to filter the lower levels too,
    # but atm only first level is picked anyway
    return Tree((k, v) for k, v in tree.items() if not k.has_trait(F.has_part_picked))


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
def find_independent_groups(
    modules: Iterable[Module], solver: Solver
) -> list[list[Module]]:
    """
    Find groups of modules that are independent of each other.
    """
    from faebryk.core.solver.defaultsolver import DefaultSolver

    assert isinstance(solver, DefaultSolver)
    state = solver.reusable_state
    if state is None:
        return [list(modules)]

    graphs = EquivalenceClasses()
    graph_to_m = defaultdict[Graph, list[Module]](list)
    for m in modules:
        params = m.get_trait(F.is_pickable_by_type).get_parameters().values()
        new_params = {state.data.mutation_map.map_forward(p).maps_to for p in params}
        m_graphs = get_graphs(new_params)
        graphs.add_eq(*m_graphs)
        for g in m_graphs:
            graph_to_m[g].append(m)

    graph_groups: list[set[Graph]] = graphs.get()
    module_groups = [[m for g in gg for m in graph_to_m[g]] for gg in graph_groups]
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
            raise PickError(
                f"Design contains contradiction: {str(e)}",
                *_tree.keys(),
            )
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

    # heuristic: pick all single part modules in one go
    single_part_modules = [
        (module, parts[0]) for module, parts in candidates if len(parts) == 1
    ]
    if single_part_modules:
        with timings.as_global("pick single candidate modules"):
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
            except (NotCompatibleException, NotDeducibleException):
                # TODO: more informationq
                raise PickError(
                    "Could not pick all explicitly-specified parts",
                    *[m for m, _ in single_part_modules],
                )
        _update_progress(single_part_modules)

        tree = update_pick_tree(tree)
        candidates = _get_candidates(tree)

    # heuristic: try pick first candidate for rest
    with timings.as_global("fast-pick"):
        try:
            check_and_attach_candidates([(m, p[0]) for m, p in candidates], solver)
        except (Contradiction, NotCompatibleException, NotDeducibleException):
            logger.warning("Could not pick all parts atomically")
            # no need to update candidates, slow picking does by itself
        else:
            # REALLLY DO REMOVE THIS
            # TODO remove
            solver.update_superset_cache(*[m for m, _ in candidates])
            _update_progress(candidates)
            logger.info(f"Fast-picked parts in {timings.get_formatted('fast-pick')}")
            return

    logger.warning("Falling back to extremely slow picking one by one")
    # Works by looking for each module again for compatible parts
    # If no compatible parts are found,
    #   it means we need to backtrack or there is no solution
    with timings.as_global("slow-pick", context=True):
        for module in tree:
            if LOG_PICK_SOLVE:
                logger.info(f"Picking part for {module}")
            part = _get_single_candidate(module)
            attach_single_no_check(module, part, solver)
            _update_progress(module)

    logger.info(f"Slow-picked parts in {timings.get_formatted('slow-pick')}")
    logger.info("Verify design")
    solver.update_superset_cache(*tree_backup)


# TODO should be a Picker
def pick_part_recursively(module: Module, solver: Solver):
    pick_tree = get_pick_tree(module)
    if LOG_PICK_SOLVE:
        logger.info(f"Pick tree:\n{pick_tree.pretty()}")

    check_missing_picks(module)

    pp = PickerProgress(pick_tree)
    try:
        with pp.context():
            pick_topologically(pick_tree, solver, pp)
    # FIXME: This does not get called anymore
    except PickErrorChildren as e:
        failed_parts = e.get_all_children()
        for m, sube in failed_parts.items():
            logger.error(
                f"Could not find pick for {m}:\n {sube.message}\n"
                f"Params:\n{indent(m.pretty_params(solver), prefix=' '*4)}"
            )
        raise
