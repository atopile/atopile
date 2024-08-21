# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
Example picker library. Used both for demonstration and as the dedicated example picker.
"""

import logging

import faebryk.library._F as F
from faebryk.core.core import Module
from faebryk.core.util import specialize_module
from faebryk.library._F import Constant, Range
from faebryk.library.Switch import _TSwitch
from faebryk.libs.app.parameters import replace_tbd_with_any
from faebryk.libs.picker.lcsc import LCSC_Part
from faebryk.libs.picker.picker import PickerOption, pick_module_by_params
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


def pick_fuse(module: F.Fuse):
    pick_module_by_params(
        module,
        [
            PickerOption(
                part=LCSC_Part(partno="C914087"),
                params={
                    "fuse_type": Constant(F.Fuse.FuseType.RESETTABLE),
                    "response_type": Constant(F.Fuse.ResponseType.SLOW),
                    "trip_current": Constant(1 * P.A),
                },
            ),
            PickerOption(
                part=LCSC_Part(partno="C914085"),
                params={
                    "fuse_type": Constant(F.Fuse.FuseType.RESETTABLE),
                    "response_type": Constant(F.Fuse.ResponseType.SLOW),
                    "trip_current": Constant(0.5 * P.A),
                },
            ),
        ],
    )


def pick_mosfet(module: F.MOSFET):
    standard_pinmap = {
        "1": module.IFs.gate,
        "2": module.IFs.source,
        "3": module.IFs.drain,
    }
    pick_module_by_params(
        module,
        [
            PickerOption(
                part=LCSC_Part(partno="C20917"),
                params={
                    "channel_type": Constant(F.MOSFET.ChannelType.N_CHANNEL),
                },
                pinmap=standard_pinmap,
            ),
            PickerOption(
                part=LCSC_Part(partno="C15127"),
                params={
                    "channel_type": Constant(F.MOSFET.ChannelType.P_CHANNEL),
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
                    "temperature_coefficient": Range(
                        F.Capacitor.TemperatureCoefficient.Y5V,
                        F.Capacitor.TemperatureCoefficient.X7R,
                    ),
                    "capacitance": Constant(100 * P.nF),
                    "rated_voltage": Range(0 * P.V, 16 * P.V),
                },
            ),
            PickerOption(
                part=LCSC_Part(partno="C19702"),
                params={
                    "temperature_coefficient": Range(
                        F.Capacitor.TemperatureCoefficient.Y5V,
                        F.Capacitor.TemperatureCoefficient.X7R,
                    ),
                    "capacitance": Constant(10 * P.uF),
                    "rated_voltage": Range(0 * P.V, 10 * P.V),
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
                params={"resistance": Constant(40.2 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25076"),
                params={"resistance": Constant(100 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25087"),
                params={"resistance": Constant(200 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C11702"),
                params={"resistance": Constant(1 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25879"),
                params={"resistance": Constant(2.2 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25900"),
                params={"resistance": Constant(4.7 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25905"),
                params={"resistance": Constant(5.1 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25917"),
                params={"resistance": Constant(6.8 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25744"),
                params={"resistance": Constant(10 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25752"),
                params={"resistance": Constant(12 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25771"),
                params={"resistance": Constant(27 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25741"),
                params={"resistance": Constant(100 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25782"),
                params={"resistance": Constant(390 * P.kohm)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25790"),
                params={"resistance": Constant(470 * P.kohm)},
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
                    "color": Constant(F.LED.Color.EMERALD),
                    "max_brightness": Constant(285 * P.mcandela),
                    "forward_voltage": Constant(3.7 * P.volt),
                    "max_current": Constant(100 * P.mA),
                },
                pinmap={"1": module.IFs.cathode, "2": module.IFs.anode},
            ),
            PickerOption(
                part=LCSC_Part(partno="C72041"),
                params={
                    "color": Constant(F.LED.Color.BLUE),
                    "max_brightness": Constant(28.5 * P.mcandela),
                    "forward_voltage": Constant(3.1 * P.volt),
                    "max_current": Constant(100 * P.mA),
                },
                pinmap={"1": module.IFs.cathode, "2": module.IFs.anode},
            ),
            PickerOption(
                part=LCSC_Part(partno="C72038"),
                params={
                    "color": Constant(F.LED.Color.YELLOW),
                    "max_brightness": Constant(180 * P.mcandela),
                    "forward_voltage": Constant(2.3 * P.volt),
                    "max_current": Constant(60 * P.mA),
                },
                pinmap={"1": module.IFs.cathode, "2": module.IFs.anode},
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
                    "reverse_working_voltage": Constant(5 * P.V),
                },
                pinmap={
                    "1": module.IFs.cathode,
                    "2": module.IFs.anode,
                },
            ),
        ],
    )


def pick_battery(module: F.Battery):
    if not isinstance(module, F.ButtonCell):
        bcell = F.ButtonCell()
        replace_tbd_with_any(bcell, recursive=False)
        specialize_module(module, bcell)
        F.has_multi_picker.add_to_module(
            bcell, 0, F.has_multi_picker.FunctionPicker(pick_battery)
        )
        return

    pick_module_by_params(
        module,
        [
            PickerOption(
                part=LCSC_Part(partno="C5239862"),
                params={
                    "voltage": Constant(3 * P.V),
                    "capacity": Range.from_center(225 * P.mAh, 50 * P.mAh),
                    "material": Constant(F.ButtonCell.Material.Lithium),
                    "size": Constant(F.ButtonCell.Size.N_2032),
                    "shape": Constant(F.ButtonCell.Shape.Round),
                },
                pinmap={
                    "1": module.IFs.power.IFs.lv,
                    "2": module.IFs.power.IFs.hv,
                },
            ),
        ],
    )


def pick_switch(module: _TSwitch[F.Electrical]):
    module.add_trait(F.can_attach_to_footprint_symmetrically())
    pick_module_by_params(
        module,
        [
            PickerOption(
                part=LCSC_Part(partno="C318884"),
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
