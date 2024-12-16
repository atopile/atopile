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
        self.sp3243e.power.decoupled.decouple(self)
        for pwr in [
            self.sp3243e.positive_charge_pump_power,
            self.sp3243e.negative_charge_pump_power,
            self.sp3243e.voltage_doubler_charge_pump_power,
            self.sp3243e.inverting_charge_pump_power,
        ]:
            cap = self.add(F.Capacitor())
            # TODO: min values according to self.power.voltage
            # 3.0V to 3.6V > C_all = 0.1μF
            # 4.5V to 5.5V > C1 = 0.047µF, C2,Cvp, Cvn = 0.33µF
            # 3.0V to 5.5V > C_all = 0.22μF
            #
            cap.capacitance.constrain_subset(
                L.Range.from_center(0.22 * P.uF, 0.22 * 0.05 * P.uF)
            )

            pwr.voltage.constrain_superset(L.Range(0 * P.V, 16 * P.V))
            cap.max_voltage.constrain_ge(16 * P.V)
