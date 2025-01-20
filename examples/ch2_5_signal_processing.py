# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
This file contains a faebryk sample.
"""

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class App(Module):
    lowpass: F.Filter

    def __preinit__(self) -> None:
        # TODO actually do something with the filter

        # Parametrize
        self.lowpass.cutoff_frequency.constrain_subset(
            L.Range.from_center_rel(10 * P.MHz, 0.05)
        )
        self.lowpass.response.constrain_subset(F.Filter.Response.LOWPASS)

        # Specialize
        special = self.lowpass.specialize(F.FilterElectricalLC())

        # set reference voltage
        # TODO: this will be automatically set by the power supply
        # once this example is more complete
        special.in_.reference.voltage.constrain_subset(
            L.Range.from_center_rel(3 * P.V, 0.05)
        )
        special.out.reference.voltage.constrain_subset(
            L.Range.from_center_rel(3 * P.V, 0.05)
        )

        # TODO
        # Construct
        # special.get_trait(F.has_construction_dependency).construct()
