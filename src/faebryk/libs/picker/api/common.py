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
from faebryk.libs.util import cast_assert

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
            print(part.lcsc_display)
            if check_compatible_parameters(cmp, part, mapping, solver):
                print(f"tried: {part.lcsc_display}")
                tried.append(part)
                yield part

    try:
        try_attach(cmp, parts_gen(), mapping, qty=1)
    except PickError as ex:
        param_mappings = [
            (
                p.lcsc_display,
                [
                    f"{m.name}: {lit}"
                    for m, lit in p.get_literal_for_mappings(mapping).items()
                ],
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


def check_compatible_parameters(
    module: Module, c: "Component", mapping: list[AttributeMapping], solver: Solver
) -> bool:
    """
    Check if the parameters of a component are compatible with the module
    """
    # Nothing to check
    if not mapping:
        return True

    # shortcut because solving slow
    try:
        get_raw(c.lcsc_display)
    except LCSC_NoDataException:
        print(f"No data for {c.lcsc_display}")
        return False

    param_mapping = [
        (
            (p := cast_assert(Parameter, getattr(module, name))),
            c_range if c_range is not None else p.domain.unbounded(p),
        )
        for name, c_range in c.attribute_literals.items()
    ]

    print(c.attribute_literals)
    print(param_mapping)

    # check for any param that has few supersets whether the component's range
    # is compatible already instead of waiting for the solver
    for m_param, c_range in param_mapping:
        # TODO other loglevel
        # logger.warning(f"Checking obvious incompatibility for param {m_param}")
        known_superset = solver.inspect_get_known_supersets(m_param, force_update=False)
        print(f"{known_superset=}")
        print(f"{c_range=}")
        if not known_superset.is_superset_of(c_range):
            print(f"Known superset {known_superset} is not a superset of {c_range}")
            # TODO reenable
            # if LOG_PICK_SOLVE:
            #    logger.warning(
            #        f"Known superset {known_superset} is not a superset of {c_range}"
            #        f" for part C{c.lcsc}"
            #    )
            return False

    # check for every param whether the candidate component's range is
    # compatible by querying the solver
    anded = And(*(Is(m_param, c_range) for m_param, c_range in param_mapping))

    if LOG_PICK_SOLVE:
        logger.info(f"Solving for module: {module}")
    result = solver.assert_any_predicate([(anded, None)], lock=False)
    if not result.true_predicates:
        return False

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Found part {c.lcsc:8} "
            f"Basic: {bool(c.is_basic)}, Preferred: {bool(c.is_preferred)}, "
            f"Price: ${c.get_price(1):2.4f}, "
            f"{c.description:15},"
        )

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

    parts = api_method(param_cls(package_candidates=fps, qty=qty, **cmp_params))  # type: ignore

    return parts
