# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import re
from dataclasses import fields
from typing import Callable

import more_itertools

import faebryk.library._F as F
from atopile.errors import UserException
from faebryk.core.module import Module
from faebryk.core.solver.solver import Solver
from faebryk.libs.exceptions import downgrade
from faebryk.libs.picker.api.api import (
    BaseParams,
    CapacitorParams,
    DiodeParams,
    InductorParams,
    LDOParams,
    LEDParams,
    MOSFETParams,
    ResistorParams,
    TVSParams,
    api_filter_by_module_params_and_attach,
    get_api_client,
    get_package_candidates,
)

# re-use the existing model for components from the jlcparts dataset, but as the data
# schema diverges over time we'll migrate this to separate models
from faebryk.libs.picker.jlcpcb.jlcpcb import Component
from faebryk.libs.picker.picker import DescriptiveProperties, PickError
from faebryk.libs.util import KeyErrorAmbiguous, KeyErrorNotFound

logger = logging.getLogger(__name__)
client = get_api_client()


# TODO add trait to module that specifies the quantity of the part
qty: int = 1


def extract_numeric_id(lcsc_id: str) -> int:
    match = re.match(r"C(\d+)", lcsc_id)
    if match is None:
        raise ValueError(f"Invalid LCSC part number {lcsc_id}")
    return int(match[1])


def find_component_by_lcsc_id(lcsc_id: str) -> Component:
    parts = client.fetch_part_by_lcsc(extract_numeric_id(lcsc_id))

    if len(parts) < 1:
        raise KeyErrorNotFound(f"Could not find part with LCSC part number {lcsc_id}")

    if len(parts) > 1:
        raise KeyErrorAmbiguous(
            parts, f"Found multiple parts with LCSC part number {lcsc_id}"
        )

    return next(iter(parts))


def find_component_by_mfr(mfr: str, mfr_pn: str) -> Component:
    parts = client.fetch_part_by_mfr(mfr, mfr_pn)

    if len(parts) < 1:
        raise KeyErrorNotFound(
            f"Could not find part with manufacturer part number {mfr_pn}"
        )

    if len(parts) > 1:
        raise KeyErrorAmbiguous(
            parts, f"Found multiple parts with manufacturer part number {mfr_pn}"
        )

    return next(iter(parts))


def find_and_attach_by_lcsc_id(module: Module, solver: Solver):
    """
    Find a part by LCSC part number
    """
    if not module.has_trait(F.has_descriptive_properties):
        raise PickError("Module does not have any descriptive properties", module)
    properties = module.get_trait(F.has_descriptive_properties).get_properties()

    if "LCSC" not in properties:
        raise PickError("Module does not have an LCSC part number", module)

    lcsc_pn = properties["LCSC"]

    # TODO: pass through errors from API
    try:
        part = find_component_by_lcsc_id(lcsc_pn)
    except KeyErrorNotFound as e:
        raise PickError(
            f"Could not find part with LCSC part number {lcsc_pn}", module
        ) from e
    except KeyErrorAmbiguous as e:
        raise PickError(
            f"Found no exact match for LCSC part number {lcsc_pn}", module
        ) from e

    if part.stock < qty:
        logger.warning(
            f"Part for {repr(module)} with LCSC part number {lcsc_pn}"
            " has insufficient stock",
        )
    api_filter_by_module_params_and_attach(module, [part], solver)


def find_and_attach_by_mfr(module: Module, solver: Solver):
    """
    Find a part by manufacturer and manufacturer part number
    """
    if not module.has_trait(F.has_descriptive_properties):
        raise PickError("Module does not have any descriptive properties", module)
    properties = module.get_trait(F.has_descriptive_properties).get_properties()

    if DescriptiveProperties.manufacturer not in properties:
        raise PickError("Module does not have a manufacturer", module)

    if DescriptiveProperties.partno not in properties:
        raise PickError("Module does not have a manufacturer part number", module)

    mfr = properties[DescriptiveProperties.manufacturer]
    mfr_pn = properties[DescriptiveProperties.partno]

    try:
        parts = [find_component_by_mfr(mfr, mfr_pn)]
    except KeyErrorNotFound as e:
        raise PickError(
            f"Could not find part with manufacturer part number {mfr_pn}", module
        ) from e
    except KeyErrorAmbiguous as e:
        parts = e.duplicates

    api_filter_by_module_params_and_attach(module, parts, solver)


def _find_component_by_params[T: BaseParams](
    api_method: Callable[[T], list[Component]],
    cmp_class: type[Module],
    param_cls: type[T],
    cmp: Module,
    solver: Solver,
) -> None:
    """
    Find a component with matching parameters
    """
    if not isinstance(cmp, cmp_class):
        raise PickError(f"Module is not a {cmp_class.__name__}", cmp)

    fps = get_package_candidates(cmp)
    generic_field_names = {f.name for f in fields(param_cls)}
    unknown_params, known_params = more_itertools.partition(
        lambda p: p.get_name() in generic_field_names, cmp.get_parameters()
    )
    cmp_params = {
        p.get_name(): p.get_last_known_deduced_superset(solver) for p in known_params
    }

    for p in unknown_params:
        with downgrade(UserException):
            raise UserException(
                f'Parameter "{p.get_name()}" isn\'t a supported parameter of'
                f' the generic parameter class "{cmp_class.__name__}" and is'
                " being ignored"
            )

    parts = api_method(param_cls(package_candidates=fps, qty=qty, **cmp_params))

    api_filter_by_module_params_and_attach(cmp, parts, solver)


def find_resistor(cmp: Module, solver: Solver):
    return _find_component_by_params(
        client.fetch_resistors, F.Resistor, ResistorParams, cmp, solver
    )


def find_capacitor(cmp: Module, solver: Solver):
    return _find_component_by_params(
        client.fetch_capacitors, F.Capacitor, CapacitorParams, cmp, solver
    )


def find_inductor(cmp: Module, solver: Solver):
    return _find_component_by_params(
        client.fetch_inductors, F.Inductor, InductorParams, cmp, solver
    )


def find_tvs(cmp: Module, solver: Solver):
    return _find_component_by_params(client.fetch_tvs, F.TVS, TVSParams, cmp, solver)


def find_led(cmp: Module, solver: Solver):
    return _find_component_by_params(client.fetch_leds, F.LED, LEDParams, cmp, solver)


def find_diode(cmp: Module, solver: Solver):
    return _find_component_by_params(
        client.fetch_diodes, F.Diode, DiodeParams, cmp, solver
    )


def find_ldo(cmp: Module, solver: Solver):
    return _find_component_by_params(client.fetch_ldos, F.LDO, LDOParams, cmp, solver)


def find_mosfet(cmp: Module, solver: Solver):
    return _find_component_by_params(
        client.fetch_mosfets, F.MOSFET, MOSFETParams, cmp, solver
    )


TYPE_SPECIFIC_LOOKUP: dict[type[Module], Callable[[Module, Solver], None]] = {
    F.Resistor: find_resistor,
    F.Capacitor: find_capacitor,
    F.Inductor: find_inductor,
    F.TVS: find_tvs,
    F.LED: find_led,
    F.Diode: find_diode,
    F.LDO: find_ldo,
    F.MOSFET: find_mosfet,
}
