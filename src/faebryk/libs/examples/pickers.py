# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
Example picker library. Used both for demonstration and as the dedicated example picker.
"""

import logging
from typing import TYPE_CHECKING

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.solver import DefaultSolver, Solver
from faebryk.libs.library import L
from faebryk.libs.picker.lcsc import LCSC_Part
from faebryk.libs.picker.picker import PickerOption, pick_module_by_params
from faebryk.libs.units import P

if TYPE_CHECKING:
    from faebryk.library.Switch import _TSwitch

logger = logging.getLogger(__name__)


# TODO replace Single with actual Range.from_center_rel


def pick_fuse(module: F.Fuse, solver: Solver):
    pick_module_by_params(
        module,
        solver,
        [
            PickerOption(
                part=LCSC_Part(partno="C914087"),
                params={
                    "fuse_type": L.PlainSet(F.Fuse.FuseType.RESETTABLE),
                    "response_type": L.PlainSet(F.Fuse.ResponseType.SLOW),
                    "trip_current": 1 * P.A,
                },
            ),
            PickerOption(
                part=LCSC_Part(partno="C914085"),
                params={
                    "fuse_type": L.PlainSet(F.Fuse.FuseType.RESETTABLE),
                    "response_type": L.PlainSet(F.Fuse.ResponseType.SLOW),
                    "trip_current": 0.5 * P.A,
                },
            ),
        ],
    )


def pick_mosfet(module: F.MOSFET, solver: Solver):
    standard_pinmap = {
        "1": module.gate,
        "2": module.source,
        "3": module.drain,
    }
    pick_module_by_params(
        module,
        solver,
        [
            PickerOption(
                part=LCSC_Part(partno="C20917"),
                params={
                    "channel_type": L.PlainSet(F.MOSFET.ChannelType.N_CHANNEL),
                },
                pinmap=standard_pinmap,
            ),
            PickerOption(
                part=LCSC_Part(partno="C15127"),
                params={
                    "channel_type": L.PlainSet(F.MOSFET.ChannelType.P_CHANNEL),
                },
                pinmap=standard_pinmap,
            ),
        ],
    )


def pick_capacitor(module: F.Capacitor, solver: Solver):
    """
    Link a partnumber/footprint to a Capacitor

    Uses 0402 when possible
    """

    pick_module_by_params(
        module,
        solver,
        [
            PickerOption(
                part=LCSC_Part(partno="C1525"),
                params={
                    "temperature_coefficient": L.Range(
                        F.Capacitor.TemperatureCoefficient.Y5V,
                        F.Capacitor.TemperatureCoefficient.X7R,
                    ),
                    "capacitance": L.Single(100 * P.nF),
                    "max_voltage": 16 * P.V,
                },
            ),
            PickerOption(
                part=LCSC_Part(partno="C19702"),
                params={
                    "temperature_coefficient": L.Range(
                        F.Capacitor.TemperatureCoefficient.Y5V,
                        F.Capacitor.TemperatureCoefficient.X7R,
                    ),
                    "capacitance": L.Single(10 * P.uF),
                    "max_voltage": 10 * P.V,
                },
            ),
        ],
    )


def pick_resistor(resistor: F.Resistor, solver: Solver):
    """
    Link a partnumber/footprint to a Resistor

    Selects only 1% 0402 resistors
    """

    pick_module_by_params(
        resistor,
        solver,
        [
            PickerOption(
                part=LCSC_Part(partno="C25111"),
                params={"resistance": L.Single(40.2 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25076"),
                params={"resistance": L.Single(100 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25087"),
                params={"resistance": L.Single(200 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C11702"),
                params={"resistance": L.Single(1 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25879"),
                params={"resistance": L.Single(2.2 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25900"),
                params={"resistance": L.Single(4.7 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25905"),
                params={"resistance": L.Single(5.1 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25917"),
                params={"resistance": L.Single(6.8 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25744"),
                params={"resistance": L.Single(10 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25752"),
                params={"resistance": L.Single(12 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25771"),
                params={"resistance": L.Single(27 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25741"),
                params={"resistance": L.Single(100 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25782"),
                params={"resistance": L.Single(390 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25790"),
                params={"resistance": L.Single(470 * P.kohm)},
            ),
        ],
    )


def pick_led(module: F.LED, solver: Solver):
    pick_module_by_params(
        module,
        solver,
        [
            PickerOption(
                part=LCSC_Part(partno="C72043"),
                params={
                    "color": L.PlainSet(F.LED.Color.EMERALD),
                    "max_brightness": 285 * P.mcandela,
                    "forward_voltage": L.Single(3.7 * P.volt),
                    "max_current": 100 * P.mA,
                },
                pinmap={"1": module.cathode, "2": module.anode},
            ),
            PickerOption(
                part=LCSC_Part(partno="C72041"),
                params={
                    "color": L.PlainSet(F.LED.Color.BLUE),
                    "max_brightness": 28.5 * P.mcandela,
                    "forward_voltage": L.Single(3.1 * P.volt),
                    "max_current": 100 * P.mA,
                },
                pinmap={"1": module.cathode, "2": module.anode},
            ),
            PickerOption(
                part=LCSC_Part(partno="C72038"),
                params={
                    "color": L.PlainSet(F.LED.Color.YELLOW),
                    "max_brightness": 180 * P.mcandela,
                    "forward_voltage": L.Single(2.3 * P.volt),
                    "max_current": 60 * P.mA,
                },
                pinmap={"1": module.cathode, "2": module.anode},
            ),
        ],
    )


def pick_tvs(module: F.TVS, solver: Solver):
    pick_module_by_params(
        module,
        solver,
        [
            PickerOption(
                part=LCSC_Part(partno="C85402"),
                params={
                    "reverse_working_voltage": L.Single(5 * P.V),
                },
                pinmap={
                    "1": module.cathode,
                    "2": module.anode,
                },
            ),
        ],
    )


def pick_battery(module: F.Battery | Module, solver: Solver):
    if not isinstance(module, F.Battery):
        raise ValueError("Module is not a Battery")
    if not isinstance(module, F.ButtonCell):
        bcell = F.ButtonCell()
        module.specialize(bcell)
        bcell.add(
            F.has_multi_picker(
                0, F.has_multi_picker.FunctionPicker(pick_battery, solver)
            )
        )
        return

    pick_module_by_params(
        module,
        solver,
        [
            PickerOption(
                part=LCSC_Part(partno="C5239862"),
                params={
                    "voltage": L.Single(3 * P.V),
                    "capacity": L.Range.from_center(225 * P.mAh, 50 * P.mAh),
                    "material": L.PlainSet(F.ButtonCell.Material.Lithium),
                    "size": L.Single(F.ButtonCell.Size.N_2032),
                    "shape": L.PlainSet(F.ButtonCell.Shape.Round),
                },
                pinmap={
                    "1": module.power.lv,
                    "2": module.power.hv,
                },
            ),
        ],
    )


def pick_switch(module: "_TSwitch[F.Electrical]", solver: Solver):
    module.add(F.can_attach_to_footprint_symmetrically())
    pick_module_by_params(
        module,
        solver,
        [
            PickerOption(
                part=LCSC_Part(partno="C318884"),
                pinmap={
                    "1": module.unnamed[0],  # type: ignore
                    "2": module.unnamed[0],  # type: ignore
                    "3": module.unnamed[1],  # type: ignore
                    "4": module.unnamed[1],  # type: ignore
                },
            )
        ],
    )


def add_example_pickers(module: Module, solver: Solver):
    lookup = {
        F.Resistor: pick_resistor,
        F.LED: pick_led,
        F.Fuse: pick_fuse,
        F.TVS: pick_tvs,
        F.MOSFET: pick_mosfet,
        F.Capacitor: pick_capacitor,
        F.Battery: pick_battery,
        F.Switch(F.Electrical): pick_switch,
    }
    F.has_multi_picker.add_pickers_by_type(
        module,
        lookup,
        lambda pick_fn: F.has_multi_picker.FunctionPicker(pick_fn, solver),
    )
