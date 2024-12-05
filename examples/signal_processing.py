# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
This file contains a faebryk sample.
"""

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.examples.pickers import add_example_pickers
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class App(Module):
    lowpass: F.Filter

    def __preinit__(self) -> None:
        # TODO actually do something with the filter

        # Parametrize
        self.lowpass.cutoff_frequency.merge(200 * P.Hz)
        self.lowpass.response.merge(F.Filter.Response.LOWPASS)

        # Specialize
        special = self.lowpass.specialize(F.FilterElectricalLC())

        # set reference voltage
        # TODO: this will be automatically set by the power supply
        # once this example is more complete
        special.in_.reference.voltage.merge(3 * P.V)
        special.out.reference.voltage.merge(3 * P.V)

        # Construct
        special.get_trait(F.has_construction_dependency).construct()

    def __postinit__(self) -> None:
        for m in self.get_children_modules(types=Module):
            add_example_pickers(m)
