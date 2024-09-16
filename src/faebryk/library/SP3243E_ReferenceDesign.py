# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P  # noqa: F401

logger = logging.getLogger(__name__)


class SP3243E_ReferenceDesign(Module):
    """
    Reference design for the SP3243E RS232 transceiver.
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    sp3243e: F.SP3243E

    # ----------------------------------------
    #                 traits
    # ----------------------------------------

    def __preinit__(self):
        # ----------------------------------------
        #              connections
        # ----------------------------------------
        for pwr in self.get_children(direct_only=True, types=F.ElectricPower):
            cap = pwr.decoupled.decouple()
            # TODO: min values according to self.power.voltage
            # 3.0V to 3.6V > C_all = 0.1μF
            # 4.5V to 5.5V > C1 = 0.047µF, C2,Cvp, Cvn = 0.33µF
            # 3.0V to 5.5V > C_all = 0.22μF
            #
            cap.capacitance.merge(F.Range.from_center(0.22 * P.uF, 0.22 * 0.05 * P.uF))

            if isinstance(pwr.voltage.get_most_narrow(), F.TBD):
                pwr.voltage.merge(
                    F.Constant(8 * P.V)
                    # F.Range.lower_bound(16 * P.V)
                )  # TODO: fix merge
                # TODO: merge conflict
