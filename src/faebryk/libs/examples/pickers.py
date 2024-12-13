# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
Example picker library. Used both for demonstration and as the dedicated example picker.
"""

import logging
from typing import TYPE_CHECKING

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.solver.solver import Solver
from faebryk.libs.library import L
from faebryk.libs.picker.lcsc import LCSC_Part
from faebryk.libs.picker.picker import PickerOption, pick_module_by_params
from faebryk.libs.units import P

if TYPE_CHECKING:
    from faebryk.library.Switch import _TSwitch

logger = logging.getLogger(__name__)


def pick_fuse(module: F.Fuse | Module, solver: Solver):
    pick_module_by_params(
        module,
        solver,
        [
            PickerOption(
                part=LCSC_Part(partno="C914087"),
                params={
                    "fuse_type": L.EnumSet(F.Fuse.FuseType.RESETTABLE),
                    "response_type": L.EnumSet(F.Fuse.ResponseType.SLOW),
                    "trip_current": 1 * P.A,
                },
            ),
            PickerOption(
                part=LCSC_Part(partno="C914085"),
                params={
                    "fuse_type": L.EnumSet(F.Fuse.FuseType.RESETTABLE),
                    "response_type": L.EnumSet(F.Fuse.ResponseType.SLOW),
                    "trip_current": 0.5 * P.A,
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
            F.has_multi_picker(0, F.has_multi_picker.FunctionPicker(pick_battery))
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
                    "material": L.EnumSet(F.ButtonCell.Material.Lithium),
                    "size": L.Single(F.ButtonCell.Size.N_2032),
                    "shape": L.EnumSet(F.ButtonCell.Shape.Round),
                },
                pinmap={
                    "1": module.power.lv,
                    "2": module.power.hv,
                },
            ),
        ],
    )


def pick_switch(module: "_TSwitch", solver: Solver):
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


def add_example_pickers(module: Module):
    lookup = {
        F.Battery: pick_battery,
        F.Switch(F.Electrical): pick_switch,
        F.Fuse: pick_fuse,
    }
    F.has_multi_picker.add_pickers_by_type(
        module,
        lookup,
        lambda pick_fn: F.has_multi_picker.FunctionPicker(pick_fn),
    )
