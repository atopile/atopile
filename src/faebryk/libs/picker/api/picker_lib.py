# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import re
from typing import Callable

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.solver.solver import Solver
from faebryk.libs.e_series import E_SERIES_VALUES
from faebryk.libs.picker.api.api import (
    CapacitorParams,
    DiodeParams,
    InductorParams,
    LDOParams,
    LEDParams,
    MOSFETParams,
    ResistorParams,
    TVSParams,
    api_filter_by_module_params_and_attach,
    api_generate_si_values,
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


def _find_component_by_lcsc_id(lcsc_id: str) -> Component:
    def extract_numeric_id(lcsc_id: str) -> int:
        match = re.match(r"C(\d+)", lcsc_id)
        if match is None:
            raise ValueError(f"Invalid LCSC part number {lcsc_id}")
        return int(match[1])

    parts = client.fetch_part_by_lcsc(extract_numeric_id(lcsc_id))

    if len(parts) < 1:
        raise KeyErrorNotFound(f"Could not find part with LCSC part number {lcsc_id}")

    if len(parts) > 1:
        raise KeyErrorAmbiguous(
            parts, f"Found multiple parts with LCSC part number {lcsc_id}"
        )

    return next(iter(parts))


def _find_component_by_mfr(mfr: str, mfr_pn: str) -> Component:
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
        part = _find_component_by_lcsc_id(lcsc_pn)
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
        parts = [_find_component_by_mfr(mfr, mfr_pn)]
    except KeyErrorNotFound as e:
        raise PickError(
            f"Could not find part with manufacturer part number {mfr_pn}", module
        ) from e
    except KeyErrorAmbiguous as e:
        parts = e.duplicates

    api_filter_by_module_params_and_attach(module, parts, solver)


def find_resistor(cmp: Module, solver: Solver):
    """
    Find a resistor with matching parameters
    """
    if not isinstance(cmp, F.Resistor):
        raise PickError("Module is not a resistor", cmp)

    parts = client.fetch_resistors(
        ResistorParams(
            resistances=api_generate_si_values(
                cmp.resistance, solver, E_SERIES_VALUES.E96
            ),
            package_candidates=get_package_candidates(cmp),
            qty=qty,
        ),
    )

    api_filter_by_module_params_and_attach(cmp, parts, solver)


def find_capacitor(cmp: Module, solver: Solver):
    """
    Find a capacitor with matching parameters
    """
    if not isinstance(cmp, F.Capacitor):
        raise PickError("Module is not a capacitor", cmp)

    parts = client.fetch_capacitors(
        CapacitorParams(
            capacitances=api_generate_si_values(
                cmp.capacitance, solver, E_SERIES_VALUES.E24
            ),
            package_candidates=get_package_candidates(cmp),
            qty=qty,
        ),
    )

    api_filter_by_module_params_and_attach(cmp, parts, solver)


def find_inductor(cmp: Module, solver: Solver):
    """
    Find an inductor with matching parameters
    """
    if not isinstance(cmp, F.Inductor):
        raise PickError("Module is not an inductor", cmp)

    parts = client.fetch_inductors(
        InductorParams(
            inductances=api_generate_si_values(
                cmp.inductance, solver, E_SERIES_VALUES.E24
            ),
            package_candidates=get_package_candidates(cmp),
            qty=qty,
        ),
    )

    api_filter_by_module_params_and_attach(cmp, parts, solver)


def find_tvs(cmp: Module, solver: Solver):
    """
    Find a TVS diode with matching parameters
    """
    if not isinstance(cmp, F.TVS):
        raise PickError("Module is not a TVS diode", cmp)

    parts = client.fetch_tvs(
        TVSParams(package_candidates=get_package_candidates(cmp), qty=qty),
    )

    api_filter_by_module_params_and_attach(cmp, parts, solver)


def find_diode(cmp: Module, solver: Solver):
    """
    Find a diode with matching parameters
    """
    if not isinstance(cmp, F.Diode):
        raise PickError("Module is not a diode", cmp)

    parts = client.fetch_diodes(
        DiodeParams(
            max_currents=api_generate_si_values(
                cmp.max_current, solver, E_SERIES_VALUES.E3
            ),
            reverse_working_voltages=api_generate_si_values(
                cmp.reverse_working_voltage, solver, E_SERIES_VALUES.E3
            ),
            package_candidates=get_package_candidates(cmp),
            qty=qty,
        ),
    )

    api_filter_by_module_params_and_attach(cmp, parts, solver)


def find_led(cmp: Module, solver: Solver):
    """
    Find an LED with matching parameters
    """
    if not isinstance(cmp, F.LED):
        raise PickError("Module is not an LED", cmp)

    parts = client.fetch_leds(
        LEDParams(package_candidates=get_package_candidates(cmp), qty=qty)
    )

    api_filter_by_module_params_and_attach(cmp, parts, solver)


def find_mosfet(cmp: Module, solver: Solver):
    """
    Find a MOSFET with matching parameters
    """

    if not isinstance(cmp, F.MOSFET):
        raise PickError("Module is not a MOSFET", cmp)

    parts = client.fetch_mosfets(
        MOSFETParams(package_candidates=get_package_candidates(cmp), qty=qty)
    )

    api_filter_by_module_params_and_attach(cmp, parts, solver)


def find_ldo(cmp: Module, solver: Solver):
    """
    Find an LDO with matching parameters
    """

    if not isinstance(cmp, F.LDO):
        raise PickError("Module is not a LDO", cmp)

    parts = client.fetch_ldos(
        LDOParams(package_candidates=get_package_candidates(cmp), qty=qty)
    )

    api_filter_by_module_params_and_attach(cmp, parts, solver)


TYPE_SPECIFIC_LOOKUP: dict[type[Module], Callable[[Module, Solver], None]] = {
    F.Resistor: find_resistor,
    F.Capacitor: find_capacitor,
    F.Inductor: find_inductor,
    F.TVS: find_tvs,
    F.LED: find_led,
    F.Diode: find_diode,
    F.MOSFET: find_mosfet,
    F.LDO: find_ldo,
}
