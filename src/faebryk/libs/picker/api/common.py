# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from dataclasses import fields
from textwrap import indent
from typing import Callable, Iterable

import more_itertools

from faebryk.core.module import Module
from faebryk.core.parameter import (
    And,
    Is,
    Parameter,
)
from faebryk.core.solver.solver import LOG_PICK_SOLVE, Solver
from faebryk.libs.picker.api.api import BaseParams, Component, get_package_candidates
from faebryk.libs.picker.lcsc import (
    LCSC_NoDataException,
    LCSC_PinmapException,
    get_raw,
)
from faebryk.libs.picker.mappings import AttributeMapping, try_get_param_mapping
from faebryk.libs.picker.picker import (
    PickError,
)
from faebryk.libs.util import cast_assert, not_none

logger = logging.getLogger(__name__)

type SIvalue = str


class PickerUnboundedParameterError(Exception):
    pass


class PickerESeriesIntersectionError(Exception):
    pass


def api_filter_by_module_params_and_attach(
    cmp: Module, parts: list[Component], solver: Solver
):
    """
    Find a component with matching parameters
    """
    mapping = try_get_param_mapping(cmp)

    # FIXME: should take the desired qty and respect it
    tried = []

    def parts_gen():
        for part in parts:
            if check_compatible_parameters([(cmp, part, mapping)], solver):
                tried.append(part)
                yield part

    try:
        try_attach(cmp, parts_gen(), mapping, qty=1)
    except PickError as ex:
        param_mappings = [
            (
                p.lcsc_display,
                [f"{name}: {lit}" for name, lit in p.attribute_literals.items()],
            )
            for p, _ in zip(parts, range(10))
        ]
        raise PickError(
            f"No parts found that are compatible with design for module:"
            f"\n{cmp.pretty_params(solver)} "
            f"\nin {len(tried)} candidate parts, "
            f"of {len(parts)} total parts:"
            f"\n{'\n'.join(f'{p}: {lits}' for p, lits in param_mappings)}",
            cmp,
        ) from ex


def try_attach(
    module: Module,
    parts: Iterable[Component],
    mapping: list[AttributeMapping],
    qty: int,
):
    # TODO remove ignore_exceptions
    # was used to handle TBDs

    failures = []
    for c in parts:
        try:
            c.attach(module, qty)
            return
        except (ValueError, Component.ParseError) as e:
            if LOG_PICK_SOLVE:
                logger.warning(f"Failed to attach {c} to {module}: {e}")
            failures.append((c, e))
        except LCSC_NoDataException as e:
            if LOG_PICK_SOLVE:
                logger.warning(f"Failed to attach {c} to {module}: {e}")
            failures.append((c, e))
        except LCSC_PinmapException as e:
            if LOG_PICK_SOLVE:
                logger.warning(f"Failed to attach {c} to {module}: {e}")
            failures.append((c, e))

    if failures:
        fail_str = indent(
            "\n" + f"{'\n'.join(f'{c}: {e}' for c, e in failures)}", " " * 4
        )

        raise PickError(
            f"Failed to attach any components to module {module}: {len(failures)}"
            f" {fail_str}",
            module,
        )

    raise PickError(
        "No components found that match the parameters and that can be attached",
        module,
    )


def get_compatible_parameters(
    module: Module, c: "Component", mapping: list[AttributeMapping], solver: Solver
):
    """
    Check if the parameters of a component are compatible with the module
    """
    # Nothing to check
    if not mapping:
        return {}

    # shortcut because solving slow
    try:
        get_raw(c.lcsc_display)
    except LCSC_NoDataException:
        return None

    param_mapping = [
        (
            (p := cast_assert(Parameter, getattr(module, name))),
            c_range if c_range is not None else p.domain.unbounded(p),
        )
        for name, c_range in c.attribute_literals.items()
    ]

    # check for any param that has few supersets whether the component's range
    # is compatible already instead of waiting for the solver
    for m_param, c_range in param_mapping:
        # TODO other loglevel
        # logger.warning(f"Checking obvious incompatibility for param {m_param}")
        known_superset = solver.inspect_get_known_supersets(m_param, force_update=False)
        if not known_superset.is_superset_of(c_range):
            if LOG_PICK_SOLVE:
                logger.warning(
                    f"Known superset {known_superset} is not a superset of {c_range}"
                    f" for part C{c.lcsc}"
                )
            return None

    return param_mapping


def check_compatible_parameters(
    module_candidates: list[tuple[Module, "Component", list[AttributeMapping]]],
    solver: Solver,
):
    # check for every param whether the candidate component's range is
    # compatible by querying the solver

    mappings = [
        get_compatible_parameters(module, c, mapping, solver)
        for module, c, mapping in module_candidates
    ]

    if any(m is None for m in mappings):
        return False

    if LOG_PICK_SOLVE:
        logger.info(f"Solving for modules:" f" {[m for m, _, _ in module_candidates]}")

    anded = And(
        *(
            Is(m_param, c_range)
            for param_mapping in mappings
            for m_param, c_range in not_none(param_mapping)
        )
    )
    result = solver.assert_any_predicate([(anded, None)], lock=False)

    if not result.true_predicates:
        return False

    return True


def pick_atomically(candidates: list[tuple[Module, "Component"]], solver: Solver):
    module_candidate_params = [
        (
            module,
            part,
            try_get_param_mapping(module),
        )
        for module, part in candidates
    ]
    if not check_compatible_parameters(module_candidate_params, solver):
        return False
    for m, part, mapping in module_candidate_params:
        try_attach(m, [part], mapping, qty=1)

    return True


def find_component_by_params[T: BaseParams](
    api_method: Callable[[T], list["Component"]],
    param_cls: type[T],
    cmp: Module,
    solver: Solver,
    qty: int,
) -> list["Component"]:
    """
    Find a component with matching parameters
    """

    fps = get_package_candidates(cmp)
    generic_field_names = {f.name for f in fields(param_cls)}
    _, known_params = more_itertools.partition(
        lambda p: p.get_name() in generic_field_names, cmp.get_parameters()
    )
    cmp_params = {
        p.get_name(): p.get_last_known_deduced_superset(solver) for p in known_params
    }

    parts = api_method(
        param_cls(package_candidates=fps, qty=qty, **cmp_params),  # type: ignore
    )

    return parts
