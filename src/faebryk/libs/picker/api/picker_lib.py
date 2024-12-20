# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import re

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.solver.solver import Solver
from faebryk.libs.picker.api.api import (
    BaseParams,
    CapacitorParams,
    Component,
    DiodeParams,
    InductorParams,
    LDOParams,
    LEDParams,
    MOSFETParams,
    ResistorParams,
    TVSParams,
    get_api_client,
)

# re-use the existing model for components from the jlcparts dataset, but as the data
# schema diverges over time we'll migrate this to separate models
from faebryk.libs.picker.api.common import (
    find_component_by_params,
)
from faebryk.libs.picker.lcsc import (
    LCSC_NoDataException,
    LCSC_PinmapException,
    attach,
    check_attachable,
)
from faebryk.libs.picker.picker import DescriptiveProperties, PickError
from faebryk.libs.util import Tree

logger = logging.getLogger(__name__)
client = get_api_client()


# TODO add way for user to specify quantity of PCBAs
qty: int = 1


def _extract_numeric_id(lcsc_id: str) -> int:
    match = re.match(r"C(\d+)", lcsc_id)
    if match is None:
        raise ValueError(f"Invalid LCSC part number {lcsc_id}")
    return int(match[1])


def _find_by_lcsc_id(module: Module, solver: Solver):
    """
    Find a part by LCSC part number
    """
    properties = module.get_trait(F.has_descriptive_properties).get_properties()
    lcsc_pn = properties["LCSC"]

    parts = client.fetch_part_by_lcsc(_extract_numeric_id(lcsc_pn))
    (part,) = parts

    if part.stock < qty:
        logger.warning(
            f"Part for {repr(module)} with LCSC part number {lcsc_pn}"
            " has insufficient stock",
        )
    return [part]


def _find_by_mfr(module: Module, solver: Solver):
    """
    Find a part by manufacturer and manufacturer part number
    """
    properties = module.get_trait(F.has_descriptive_properties).get_properties()

    if DescriptiveProperties.manufacturer not in properties:
        raise PickError("Module does not have a manufacturer", module)

    mfr = properties[DescriptiveProperties.manufacturer]
    mfr_pn = properties[DescriptiveProperties.partno]

    parts = client.fetch_part_by_mfr(mfr, mfr_pn)
    assert parts

    return parts


TYPE_SPECIFIC_LOOKUP: dict[type[Module], type[BaseParams]] = {
    F.Resistor: ResistorParams,
    F.Capacitor: CapacitorParams,
    F.Inductor: InductorParams,
    F.TVS: TVSParams,
    F.LED: LEDParams,
    F.Diode: DiodeParams,
    F.LDO: LDOParams,
    F.MOSFET: MOSFETParams,
}  # type: ignore


def _find_module_by_api(module: Module, solver: Solver) -> list[Component]:
    assert module.has_trait(F.is_pickable)
    # Error can propagate through,
    # because we expect all pickable modules to be attachable
    check_attachable(module)

    if module.has_trait(F.has_descriptive_properties):
        props = module.get_trait(F.has_descriptive_properties).get_properties()
        if "LCSC" in props:
            return _find_by_lcsc_id(module, solver)
        if DescriptiveProperties.partno in props:
            return _find_by_mfr(module, solver)

    params_t = TYPE_SPECIFIC_LOOKUP[type(module)]
    candidates = find_component_by_params(
        client.fetch_parts, params_t, module, solver, qty
    )

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


def api_get_candidates(
    modules: Tree[Module], solver: Solver
) -> dict[Module, list[Component]]:
    candidates = modules.copy()
    parts = {}
    empty = set()

    while candidates:
        # TODO use parallel (endpoint)
        # TODO deduplicate parts with same literals
        new_parts = {m: _find_module_by_api(m, solver) for m in modules}
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
                    f"No candidates found for {m}:\n{m.pretty_params(solver)}", m
                )
            candidates.update(subtree)

    # should fail earlier
    return {}


def add_api_pickers(module: Module) -> None:
    # Generic pickers
    if module.has_trait(F.has_descriptive_properties):
        props = module.get_trait(F.has_descriptive_properties).get_properties()
        if "LCSC" in props:
            logger.debug(f"Adding LCSC picker for {module.get_full_name()}")
            module.add(F.is_pickable())
            return
        if DescriptiveProperties.partno in props:
            logger.debug(f"Adding MFR picker for {module.get_full_name()}")
            module.add(F.is_pickable())
            return

    if type(module) in TYPE_SPECIFIC_LOOKUP:
        module.add(F.is_pickable())
