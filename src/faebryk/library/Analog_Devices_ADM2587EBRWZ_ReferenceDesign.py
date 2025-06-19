# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import itertools
import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.smd import SMDSize
from faebryk.libs.units import P  # noqa: F401

logger = logging.getLogger(__name__)


class Analog_Devices_ADM2587EBRWZ_ReferenceDesign(Module):
    """
    Reference implementation of ADM2587EBRWZ isolated RS485 transceiver
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    transceiver = L.f_field(F.Analog_Devices_ADM2587EBRWZ)(full_duplex=False)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    @L.rt_field
    def pcb_layout(self):
        from faebryk.exporters.pcb.layout.absolute import LayoutAbsolute
        from faebryk.exporters.pcb.layout.typehierarchy import LayoutTypeHierarchy

        Point = F.has_pcb_position.Point
        L = F.has_pcb_position.layer_type
        LVL = LayoutTypeHierarchy.Level

        return F.has_pcb_layout_defined(
            layout=LayoutTypeHierarchy(
                layouts=[
                    LVL(
                        mod_type=F.Analog_Devices_ADM2587EBRWZ,
                        layout=LayoutAbsolute(Point((0, 0, 0, L.NONE))),
                    ),
                ]
            )
        )

    def __preinit__(self):
        # ------------------------------------
        #           connections
        # ------------------------------------
        self.transceiver.power_isolated_in.connect(self.transceiver.power_isolated_out)

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        # decoupling unisolated power
        power_unisolated_capacitors = (
            self.transceiver.power_unisolated.decoupled.decouple(self)
            .specialize(F.MultiCapacitor(4))
            .capacitors
        )
        capacitance_values = [100, 10]  # in nF

        for cap, value in zip(
            power_unisolated_capacitors, itertools.cycle(capacitance_values)
        ):
            cap.capacitance.constrain_subset(
                L.Range.from_center_rel(value * P.nF, 0.05)
            )
            cap.add(F.has_package_requirements(size=SMDSize.I0603))
        # decoupling isolated power in
        for i, cap in enumerate(
            self.transceiver.power_isolated_in.decoupled.decouple(self)
            .specialize(F.MultiCapacitor(2))
            .capacitors
        ):
            cap.capacitance.constrain_subset(
                L.Range.from_center_rel(capacitance_values[i] * P.nF, 0.05)
            )
            cap.add(F.has_package_requirements(size=SMDSize.I0603))
        # decoupling isolated power out
        for i, cap in enumerate(
            self.transceiver.power_isolated_out.decoupled.decouple(self)
            .specialize(F.MultiCapacitor(2))
            .capacitors
        ):
            cap.capacitance.constrain_subset(
                L.Range.from_center_rel(capacitance_values[i] * P.nF, 0.05)
            )
            cap.add(F.has_package_requirements(size=SMDSize.I0603))

        # connect read enable (active high) and write enable (active low) together
        self.transceiver.read_enable.connect(self.transceiver.write_enable)
