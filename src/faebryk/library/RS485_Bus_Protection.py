# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.exporters.pcb.layout.absolute import LayoutAbsolute
from faebryk.exporters.pcb.layout.extrude import LayoutExtrude
from faebryk.exporters.pcb.layout.typehierarchy import LayoutTypeHierarchy
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class RS485_Bus_Protection(Module):
    """
    RS485 bus protection.
    - Overvoltage protection
    - Overcurrent protection
    - Common mode filter
    - Termination resistor
    - ESD protection
    - Lightning protection

    based on: https://www.mornsun-power.com/public/uploads/pdf/TD(H)541S485H.pdf
    """

    class CompositeTVS(Module):
        """
        Wrapper around a set of diodes protecting against transient voltage spikes.
        """

        anode: F.Electrical
        cathode: F.Electrical

        clamping_diodes = L.list_field(2, F.Diode)
        tvs: F.TVS

        @L.rt_field
        def can_bridge(self):
            return F.can_bridge_defined(self.anode, self.cathode)

        def __preinit__(self):
            # ----------------------------------------
            #            parametrization
            # ----------------------------------------
            self.tvs.reverse_working_voltage.constrain_subset(
                L.Range.from_center_rel(8.5 * P.V, 0.05)
            )
            # self.tvs.max_current.merge(F.Range.from_center_rel(41.7*P.A, 0.05))
            # self.tvs.forward_voltage.merge(F.Range(9.44*P.V, 10.40*P.V))

            for diode in self.clamping_diodes:
                diode.forward_voltage.constrain_subset(
                    L.Range.from_center_rel(1.1 * P.V, 0.05)
                )
                diode.max_current.constrain_subset(
                    L.Range.from_center_rel(1 * P.A, 0.05)
                )
                diode.reverse_working_voltage.constrain_subset(
                    L.Range.from_center_rel(1 * P.kV, 0.05)
                )

            # ----------------------------------------
            #               Connections
            # ----------------------------------------
            self.anode.connect_via(
                [
                    self.tvs,
                    self.clamping_diodes[0],
                ],
                self.cathode,
            )
            self.clamping_diodes[0].cathode.connect_via(
                self.clamping_diodes[1],
                self.clamping_diodes[0].anode,
            )

    def __init__(self, termination: bool = True, polarization: bool = True) -> None:
        super().__init__()
        self._termination = termination
        self._polarization = polarization

    current_limmiter_resistors = L.list_field(2, F.Resistor)
    common_mode_filter: F.Common_Mode_Filter
    gnd_couple_resistor: F.Resistor
    gnd_couple_capacitor: F.Capacitor
    gdt: F.GDT
    composite_tvs: CompositeTVS

    power: F.ElectricPower
    rs485_dfp: F.RS485
    rs485_ufp: F.RS485
    earth: F.Electrical

    @L.rt_field
    def has_defined_layout(self):
        # PCB layout
        Point = F.has_pcb_position.Point
        L = F.has_pcb_position.layer_type
        LVL = LayoutTypeHierarchy.Level
        self.gnd_couple_resistor.add(
            F.has_pcb_layout_defined(
                LayoutAbsolute(
                    Point((-10, 0, 90, L.NONE)),
                )
            )
        )
        layouts = [
            LVL(
                mod_type=F.GDT,
                layout=LayoutAbsolute(
                    Point((0, 0, 0, L.NONE)),
                ),
            ),
            LVL(
                mod_type=F.Resistor,
                layout=LayoutExtrude(
                    base=Point((-4, -7, 0, L.NONE)),
                    vector=(4, 0, 90),
                ),
            ),
            LVL(
                mod_type=self.CompositeTVS,
                layout=LayoutAbsolute(Point((0, -14.5, 0, L.NONE))),
                children_layout=LayoutTypeHierarchy(
                    layouts=[
                        LVL(
                            mod_type=F.Diode,
                            layout=LayoutExtrude(
                                base=Point((-3.5, 0, 90, L.NONE)),
                                vector=(3.5, 0, 0),
                            ),
                        ),
                    ]
                ),
            ),
            LVL(
                mod_type=F.Common_Mode_Filter,
                layout=LayoutAbsolute(
                    Point((0, -20, 90, L.NONE)),
                ),
            ),
            # LVL(
            #    mod_type=F.Capacitor,
            #    layout=LayoutAbsolute(
            #        Point((10, 0, 90, L.NONE)),
            #    ),
            # ),
        ]
        return F.has_pcb_layout_defined(LayoutTypeHierarchy(layouts))

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.rs485_dfp, self.rs485_ufp)

    def __preinit__(self):
        if self._termination:
            termination_resistor = self.add(F.Resistor(), name="termination_resistor")
            termination_resistor.resistance.constrain_subset(
                L.Range.from_center_rel(120 * P.ohm, 0.05)
            )
            self.rs485_ufp.diff_pair.p.connect_via(
                termination_resistor, self.rs485_ufp.diff_pair.n
            )
        if self._polarization:
            polarization_resistors = self.add_to_container(2, F.Resistor)

            polarization_resistors[0].resistance.constrain_subset(
                L.Range(380 * P.ohm, 420 * P.ohm)
            )
            polarization_resistors[1].resistance.constrain_subset(
                L.Range(380 * P.ohm, 420 * P.ohm)
            )
            self.rs485_dfp.diff_pair.p.signal.connect_via(
                polarization_resistors[0], self.power.hv
            )
            self.rs485_dfp.diff_pair.n.signal.connect_via(
                polarization_resistors[1], self.power.lv
            )

        # ----------------------------------------
        #            parametrization
        # ----------------------------------------
        self.current_limmiter_resistors[0].resistance.constrain_subset(
            L.Range.from_center_rel(2.7 * P.ohm, 0.05)
        )
        self.current_limmiter_resistors[0].rated_power.constrain_subset(
            F.Range.lower_bound(500 * P.mW)
        )
        self.current_limmiter_resistors[1].resistance.constrain_subset(
            L.Range.from_center_rel(2.7 * P.ohm, 0.05)
        )
        self.current_limmiter_resistors[1].rated_power.constrain_ge(
            L.Single(500 * P.mW)
        )

        self.gnd_couple_resistor.resistance.constrain_subset(
            L.Range.from_center_rel(1 * P.Mohm, 0.05)
        )
        self.gnd_couple_capacitor.capacitance.constrain_subset(
            L.Range.from_center_rel(1 * P.uF, 0.05)
        )
        self.gnd_couple_capacitor.rated_voltage.constrain_ge(L.Single(2 * P.kV))

        # ----------------------------------------
        #               Connections
        # ----------------------------------------
        # rs485_in/out connections
        self.rs485_dfp.diff_pair.n.signal.connect_via(
            [self.common_mode_filter.coil_a, self.current_limmiter_resistors[0]],
            self.rs485_ufp.diff_pair.n.signal,
        )
        self.rs485_dfp.diff_pair.p.signal.connect_via(
            [self.common_mode_filter.coil_b, self.current_limmiter_resistors[1]],
            self.rs485_ufp.diff_pair.p.signal,
        )

        # gdt connections
        self.rs485_ufp.diff_pair.p.signal.connect(self.gdt.tube_1)
        self.rs485_ufp.diff_pair.n.signal.connect(self.gdt.tube_2)

        # earth connections
        self.power.lv.connect_via(self.gnd_couple_resistor, self.earth)
        self.power.lv.connect_via(self.gnd_couple_capacitor, self.earth)
        self.gdt.common.connect(self.earth)

        # tvs connections
        self.common_mode_filter.coil_a.unnamed[1].connect_via(
            self.composite_tvs, self.common_mode_filter.coil_b.unnamed[1]
        )
