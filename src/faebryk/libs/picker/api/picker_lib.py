# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import re
from dataclasses import fields
from textwrap import indent
from typing import Iterable

import more_itertools

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.parameter import And, Is, Parameter, ParameterOperatable
from faebryk.core.solver.solver import LOG_PICK_SOLVE, Solver
from faebryk.libs.exceptions import UserException, downgrade
from faebryk.libs.picker.api.api import (
    ApiHTTPError,
    get_api_client,
    get_package_candidates,
)
from faebryk.libs.picker.api.models import (
    BaseParams,
    CapacitorParams,
    Component,
    DiodeParams,
    InductorParams,
    LCSCParams,
    LDOParams,
    LEDParams,
    ManufacturerPartParams,
    MOSFETParams,
    ResistorParams,
    TVSParams,
)
from faebryk.libs.picker.lcsc import (
    LCSC_NoDataException,
    LCSC_PinmapException,
    attach,
    check_attachable,
    get_raw,
)
from faebryk.libs.picker.picker import MultiPickError, PickError
from faebryk.libs.sets.sets import P_Set
from faebryk.libs.util import (
    Tree,
    cast_assert,
    groupby,
    indented_container,
    not_none,
    partition,
)

logger = logging.getLogger(__name__)
client = get_api_client()


type SIvalue = str

# TODO add way for user to specify quantity of PCBAs
qty: int = 1


class PickerUnboundedParameterError(Exception):
    pass


class PickerESeriesIntersectionError(Exception):
    pass


def _extract_numeric_id(lcsc_id: str) -> int:
    match = re.match(r"C(\d+)", lcsc_id)
    if match is None:
        raise ValueError(f"Invalid LCSC part number {lcsc_id}")
    return int(match[1])


TYPE_SPECIFIC_LOOKUP: dict[F.is_pickable_by_type.Type, type[BaseParams]] = {
    F.is_pickable_by_type.Type.Resistor: ResistorParams,
    F.is_pickable_by_type.Type.Capacitor: CapacitorParams,
    F.is_pickable_by_type.Type.Inductor: InductorParams,
    F.is_pickable_by_type.Type.TVS: TVSParams,
    F.is_pickable_by_type.Type.LED: LEDParams,
    F.is_pickable_by_type.Type.Diode: DiodeParams,
    F.is_pickable_by_type.Type.LDO: LDOParams,
    F.is_pickable_by_type.Type.MOSFET: MOSFETParams,
}


def _prepare_query(
    module: Module, solver: Solver
) -> BaseParams | LCSCParams | ManufacturerPartParams:
    assert module.has_trait(F.is_pickable)
    # Error can propagate through,
    # because we expect all pickable modules to be attachable
    check_attachable(module)

    if trait := module.try_get_trait(F.is_pickable_by_part_number):
        return ManufacturerPartParams(
            manufacturer_name=trait.get_manufacturer(),
            part_number=trait.get_partno(),
            quantity=qty,
        )
    elif trait := module.try_get_trait(F.is_pickable_by_supplier_id):
        if trait.get_supplier() == F.is_pickable_by_supplier_id.Supplier.LCSC:
            return LCSCParams(
                lcsc=_extract_numeric_id(trait.get_supplier_part_id()), quantity=qty
            )
    elif trait := module.try_get_trait(F.is_pickable_by_type):
        pick_type = trait.get_pick_type()
        params_t = TYPE_SPECIFIC_LOOKUP[pick_type]

        fps = get_package_candidates(module)
        generic_field_names = {f.name for f in fields(params_t)}
        _, known_params = more_itertools.partition(
            lambda p: p.get_name() in generic_field_names, module.get_parameters()
        )
        cmp_params = {
            p.get_name(): p.get_last_known_deduced_superset(solver)
            for p in known_params
        }
        return params_t(package_candidates=fps, qty=qty, **cmp_params)  # type: ignore

    raise NotImplementedError(
        f"Unsupported pickable trait: {module.get_trait(F.is_pickable)}"
    )


def _process_candidates(module: Module, candidates: list[Component]) -> list[Component]:
    # Filter parts with weird pinmaps
    it = iter(candidates)
    filtered_candidates = []
    for c in it:
        try:
            attach(module, c.lcsc_display, check_only=True, get_model=False)
            filtered_candidates.append(c)
            # If we found one that's ok, just continue since likely enough
            filtered_candidates.extend(it)
            break
        except LCSC_NoDataException:
            if len(candidates) == 1:
                raise
        except LCSC_PinmapException:
            # if all filtered by pinmap something is fishy
            if not filtered_candidates and candidates[-1] is c:
                raise

    return filtered_candidates


def _find_modules(
    modules: Tree[Module], solver: Solver
) -> dict[Module, list[Component]]:
    params = {m: _prepare_query(m, solver) for m in modules}
    grouped = groupby(params.items(), lambda p: p[1])
    queries = list(grouped.keys())
    try:
        results = client.fetch_parts_multiple(queries)
    except ApiHTTPError as e:
        if e.response.status_code == 404:
            raise MultiPickError("Failed to fetch one or more parts", modules) from e
        raise e

    assert len(results) == len(queries)

    return {
        m: _process_candidates(m, r)
        for ms, r in zip(grouped.values(), results)
        for m, _ in ms
    }


def get_candidates(
    modules: Tree[Module], solver: Solver
) -> dict[Module, list[Component]]:
    candidates = modules.copy()
    parts = {}
    empty = set()

    while candidates:
        # TODO deduplicate parts with same literals
        new_parts = _find_modules(modules, solver)
        parts.update({m: p for m, p in new_parts.items() if p})
        empty = {m for m, p in new_parts.items() if not p}
        for m in parts:
            if m in candidates:
                candidates.pop(m)
        if not empty:
            return parts
        for m in empty:
            subtree = candidates.pop(m)
            if not subtree:
                raise PickError(
                    f"No candidates found for `{m}`:\n{m.pretty_params(solver)}", m
                )
            candidates.update(subtree)

    # should fail earlier
    return {}


def filter_by_module_params_and_attach(
    cmp: Module, parts: list[Component], solver: Solver
):
    """
    Find a component with matching parameters
    """
    # FIXME: should take the desired qty and respect it
    tried = []

    def parts_gen():
        for part in parts:
            if check_compatible_parameters([(cmp, part)], solver):
                tried.append(part)
                yield part

    try:
        try_attach(cmp, parts_gen(), qty=1)
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


def try_attach(module: Module, parts: Iterable[Component], qty: int):
    # TODO remove ignore_exceptions
    # was used to handle TBDs

    failures = []
    for c in parts:
        try:
            c.attach(module, qty)
            return
        except (ValueError, Component.ParseError) as e:
            if LOG_PICK_SOLVE:
                logger.warning(f"Failed to attach {c} to `{module}`: {e}")
            failures.append((c, e))
        except LCSC_NoDataException as e:
            if LOG_PICK_SOLVE:
                logger.warning(f"Failed to attach {c} to `{module}`: {e}")
            failures.append((c, e))
        except LCSC_PinmapException as e:
            if LOG_PICK_SOLVE:
                logger.warning(f"Failed to attach {c} to `{module}`: {e}")
            failures.append((c, e))

    if failures:
        fail_str = indent(
            "\n" + f"{'\n'.join(f'{c}: {e}' for c, e in failures)}", " " * 4
        )

        raise PickError(
            f"Failed to attach any components to module `{module}`: {len(failures)}"
            f" {fail_str}",
            module,
        )

    raise PickError(
        "No components found that match the parameters and that can be attached",
        module,
    )


def get_compatible_parameters(
    module: Module, c: "Component", solver: Solver
) -> dict[Parameter, ParameterOperatable.Literal] | None:
    """
    Check if the parameters of a component are compatible with the module
    """
    # Nothing to check
    if not c.attribute_literals:
        return {}

    # shortcut because solving slow
    try:
        get_raw(c.lcsc_display)
    except LCSC_NoDataException:
        return None

    no_attr, have_attr = partition(
        lambda x: hasattr(module, x), c.attribute_literals.keys()
    )
    no_attr, have_attr = list(no_attr), list(have_attr)

    if no_attr:
        with downgrade(UserException):
            raise UserException(
                f"Module `{module}` is missing attributes"
                f" {indented_container(no_attr)}. "
                "This likely means you could use a more precise"
                " module/component in your design."
            )

    def _map_param(name: str) -> tuple[Parameter, P_Set]:
        p = cast_assert(Parameter, getattr(module, name))
        c_range = c.attribute_literals[name]
        if c_range is None:
            c_range = p.domain.unbounded(p)
        return p, c_range

    param_mapping = [_map_param(name) for name in have_attr]

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

    return {p: c_range for p, c_range in param_mapping}


def check_compatible_parameters(
    module_candidates: list[tuple[Module, Component]], solver: Solver
):
    # check for every param whether the candidate component's range is
    # compatible by querying the solver

    mappings = [get_compatible_parameters(m, c, solver) for m, c in module_candidates]

    if any(m is None for m in mappings):
        return False

    if LOG_PICK_SOLVE:
        logger.info(f"Solving for modules:" f" {[m for m, _ in module_candidates]}")

    anded = And(
        *(
            Is(m_param, c_range)
            for param_mapping in mappings
            for m_param, c_range in not_none(param_mapping).items()
        )
    )
    result = solver.assert_any_predicate([(anded, None)], lock=False)

    if not result.true_predicates:
        return False

    return True


def pick_atomically(candidates: list[tuple[Module, Component]], solver: Solver):
    module_candidate_params = [(module, part) for module, part in candidates]
    if not check_compatible_parameters(module_candidate_params, solver):
        return False
    for m, part in module_candidate_params:
        try_attach(m, [part], qty=1)

    return True
