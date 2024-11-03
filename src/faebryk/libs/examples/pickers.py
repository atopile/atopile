# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
Example picker library. Used both for demonstration and as the dedicated example picker.
"""

import logging
from typing import TYPE_CHECKING

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.app.parameters import replace_tbd_with_any
from faebryk.libs.picker.lcsc import LCSC_Part
from faebryk.libs.picker.picker import PickerOption, pick_module_by_params
from faebryk.libs.units import P

if TYPE_CHECKING:
    from faebryk.library.Switch import _TSwitch

logger = logging.getLogger(__name__)


def pick_fuse(module: F.Fuse):
    pick_module_by_params(
        module,
        [
            PickerOption(
                part=LCSC_Part(partno="C914087"),
                params={
                    "fuse_type": F.Constant(F.Fuse.FuseType.RESETTABLE),
                    "response_type": F.Constant(F.Fuse.ResponseType.SLOW),
                    "trip_current": F.Constant(1 * P.A),
                },
            ),
            PickerOption(
                part=LCSC_Part(partno="C914085"),
                params={
                    "fuse_type": F.Constant(F.Fuse.FuseType.RESETTABLE),
                    "response_type": F.Constant(F.Fuse.ResponseType.SLOW),
                    "trip_current": F.Constant(0.5 * P.A),
                },
            ),
        ],
    )


def pick_mosfet(module: F.MOSFET):
    standard_pinmap = {
        "1": module.gate,
        "2": module.source,
        "3": module.drain,
    }
    pick_module_by_params(
        module,
        [
            PickerOption(
                part=LCSC_Part(partno="C20917"),
                params={
                    "channel_type": F.Constant(F.MOSFET.ChannelType.N_CHANNEL),
                },
                pinmap=standard_pinmap,
            ),
            PickerOption(
                part=LCSC_Part(partno="C15127"),
                params={
                    "channel_type": F.Constant(F.MOSFET.ChannelType.P_CHANNEL),
                },
                pinmap=standard_pinmap,
            ),
        ],
    )


def pick_capacitor(module: F.Capacitor):
    """
    Link a partnumber/footprint to a Capacitor

    Uses 0402 when possible
    """

    pick_module_by_params(
        module,
        [
            PickerOption(
                part=LCSC_Part(partno="C1525"),
                params={
                    "temperature_coefficient": F.Range(
                        F.Capacitor.TemperatureCoefficient.Y5V,
                        F.Capacitor.TemperatureCoefficient.X7R,
                    ),
                    "capacitance": F.Constant(100 * P.nF),
                    "rated_voltage": F.Constant(16 * P.V),
                },
            ),
            PickerOption(
                part=LCSC_Part(partno="C19702"),
                params={
                    "temperature_coefficient": F.Range(
                        F.Capacitor.TemperatureCoefficient.Y5V,
                        F.Capacitor.TemperatureCoefficient.X7R,
                    ),
                    "capacitance": F.Constant(10 * P.uF),
                    "rated_voltage": F.Constant(10 * P.V),
                },
            ),
        ],
    )


def pick_resistor(resistor: F.Resistor):
    """
    Link a partnumber/footprint to a Resistor

    Selects only 1% 0402 resistors
    """

    pick_module_by_params(
        resistor,
        [
            PickerOption(
                part=LCSC_Part(partno="C25111"),
                params={"resistance": F.Constant(40.2 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25076"),
                params={"resistance": F.Constant(100 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25087"),
                params={"resistance": F.Constant(200 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C11702"),
                params={"resistance": F.Constant(1 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25879"),
                params={"resistance": F.Constant(2.2 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25900"),
                params={"resistance": F.Constant(4.7 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25905"),
                params={"resistance": F.Constant(5.1 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25917"),
                params={"resistance": F.Constant(6.8 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25744"),
                params={"resistance": F.Constant(10 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25752"),
                params={"resistance": F.Constant(12 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25771"),
                params={"resistance": F.Constant(27 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25741"),
                params={"resistance": F.Constant(100 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25782"),
                params={"resistance": F.Constant(390 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25790"),
                params={"resistance": F.Constant(470 * P.kohm)},
            ),
        ],
    )


def pick_led(module: F.LED):
    pick_module_by_params(
        module,
        [
            PickerOption(
                part=LCSC_Part(partno="C72043"),
                params={
                    "color": F.Constant(F.LED.Color.EMERALD),
                    "max_brightness": F.Constant(285 * P.mcandela),
                    "forward_voltage": F.Constant(3.7 * P.volt),
                    "max_current": F.Constant(100 * P.mA),
                },
                pinmap={"1": module.cathode, "2": module.anode},
            ),
            PickerOption(
                part=LCSC_Part(partno="C72041"),
                params={
                    "color": F.Constant(F.LED.Color.BLUE),
                    "max_brightness": F.Constant(28.5 * P.mcandela),
                    "forward_voltage": F.Constant(3.1 * P.volt),
                    "max_current": F.Constant(100 * P.mA),
                },
                pinmap={"1": module.cathode, "2": module.anode},
            ),
            PickerOption(
                part=LCSC_Part(partno="C72038"),
                params={
                    "color": F.Constant(F.LED.Color.YELLOW),
                    "max_brightness": F.Constant(180 * P.mcandela),
                    "forward_voltage": F.Constant(2.3 * P.volt),
                    "max_current": F.Constant(60 * P.mA),
                },
                pinmap={"1": module.cathode, "2": module.anode},
            ),
        ],
    )


def pick_tvs(module: F.TVS):
    pick_module_by_params(
        module,
        [
            PickerOption(
                part=LCSC_Part(partno="C85402"),
                params={
                    "reverse_working_voltage": F.Constant(5 * P.V),
                },
                pinmap={
                    "1": module.cathode,
                    "2": module.anode,
                },
            ),
        ],
    )


def pick_battery(module: F.Battery):
    if not isinstance(module, F.ButtonCell):
        bcell = F.ButtonCell()
        replace_tbd_with_any(bcell, recursive=False)
        module.specialize(bcell)
        bcell.add(
            F.has_multi_picker(0, F.has_multi_picker.FunctionPicker(pick_battery))
        )
        return

    pick_module_by_params(
        module,
        [
            PickerOption(
                part=LCSC_Part(partno="C5239862"),
                params={
                    "voltage": F.Constant(3 * P.V),
                    "capacity": F.Range.from_center(225 * P.mAh, 50 * P.mAh),
                    "material": F.Constant(F.ButtonCell.Material.Lithium),
                    "size": F.Constant(F.ButtonCell.Size.N_2032),
                    "shape": F.Constant(F.ButtonCell.Shape.Round),
                },
                pinmap={
                    "1": module.power.lv,
                    "2": module.power.hv,
                },
            ),
        ],
    )


def pick_switch(module: "_TSwitch[F.Electrical]"):
    module.add(F.can_attach_to_footprint_symmetrically())
    pick_module_by_params(
        module,
        [
            PickerOption(
                part=LCSC_Part(partno="C318884"),
                pinmap={
                    "1": module.unnamed[0],
                    "2": module.unnamed[0],
                    "3": module.unnamed[1],
                    "4": module.unnamed[1],
                },
            )
        ],
    )


def add_example_pickers(module: Module):
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
        F.has_multi_picker.FunctionPicker,
    )
