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

    def __init__(self, termination: bool = True, polarization: bool = True) -> None:
        super().__init__()
        self._termination = termination
        self._polarization = polarization

    gdt: F.GDT
    tvs: F.TVS
    current_limmiter_resistors = L.list_field(2, F.Resistor)
    common_mode_filter: F.Common_Mode_Filter
    gnd_couple_resistor: F.Resistor
    gnd_couple_capacitor: F.Capacitor
    clamping_diodes = L.list_field(2, F.Diode)
    power: F.ElectricPower
    rs485_in: F.RS485
    rs485_out: F.RS485
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
            # TODO: fix
            # LVL(
            #    mod_type=F.TVS,
            #    layout=LayoutAbsolute(
            #        Point((0, 11, 0, L.NONE)),
            #    ),
            # ),
            LVL(
                mod_type=F.Common_Mode_Filter,
                layout=LayoutAbsolute(
                    Point((0, 19, 90, L.NONE)),
                ),
            ),
            LVL(
                mod_type=F.Diode,
                layout=LayoutExtrude(
                    base=Point((-3.5, 14.5, 90, L.NONE)),
                    vector=(0, 3.5, 0),
                ),
            ),
            LVL(
                mod_type=F.Resistor,
                layout=LayoutExtrude(
                    base=Point((-2, 7, 90, L.NONE)),
                    vector=(0, 4, 0),
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
        return F.can_bridge_defined(self.rs485_in, self.rs485_out)

    def __preinit__(self):
        if self._termination:
            termination_resistor = self.add(F.Resistor(), name="termination_resistor")
            termination_resistor.resistance.merge(
                F.Range.from_center_rel(120 * P.ohm, 0.05)
            )
            self.rs485_out.diff_pair.p.connect_via(
                termination_resistor, self.rs485_out.diff_pair.n
            )
        if self._polarization:
            polarization_resistors = self.add_to_container(2, F.Resistor)

            polarization_resistors[0].resistance.merge(
                F.Range(380 * P.ohm, 420 * P.ohm)
            )
            polarization_resistors[1].resistance.merge(
                F.Range(380 * P.ohm, 420 * P.ohm)
            )
            self.rs485_in.diff_pair.p.connect_via(
                polarization_resistors[0], self.power.hv
            )
            self.rs485_in.diff_pair.n.connect_via(
                polarization_resistors[1], self.power.lv
            )

        self.current_limmiter_resistors[0].resistance.merge(
            F.Range.from_center_rel(2.7 * P.ohm, 0.05)
        )
        # TODO: set power dissipation of resistor to 2W
        self.current_limmiter_resistors[1].resistance.merge(
            F.Range.from_center_rel(2.7 * P.ohm, 0.05)
        )
        # TODO: set power dissipation of resistor to 2W

        self.gnd_couple_resistor.resistance.merge(
            F.Range.from_center_rel(1 * P.Mohm, 0.05)
        )
        self.gnd_couple_capacitor.capacitance.merge(
            F.Range.from_center_rel(1 * P.uF, 0.05)
        )
        self.gnd_couple_capacitor.rated_voltage.merge(F.Range.lower_bound(2 * P.kV))

        self.tvs.reverse_working_voltage.merge(F.Range.from_center_rel(8.5 * P.V, 0.05))
        # self.tvs.max_current.merge(F.Range.from_center_rel(41.7*P.A, 0.05))
        # self.tvs.forward_voltage.merge(F.Range(9.44*P.V, 10.40*P.V))

        for diode in self.clamping_diodes:
            diode.forward_voltage.merge(F.Range.from_center_rel(1.1 * P.V, 0.05))
            diode.max_current.merge(F.Range.from_center_rel(1 * P.A, 0.05))
            diode.reverse_working_voltage.merge(F.Range.from_center_rel(1 * P.kV, 0.05))

        # connections
        # earth connections
        self.power.lv.connect_via(self.gnd_couple_resistor, self.earth)
        self.power.lv.connect_via(self.gnd_couple_capacitor, self.earth)
        self.gdt.common.connect(self.earth)

        # rs485_in connections
        self.rs485_in.diff_pair.n.connect(self.common_mode_filter.c_a[0])
        self.rs485_in.diff_pair.p.connect(self.common_mode_filter.c_b[0])

        # rs485_out connections
        self.common_mode_filter.c_a[1].connect_via(
            self.current_limmiter_resistors[0],
            self.rs485_out.diff_pair.n,
        )
        self.common_mode_filter.c_b[1].connect_via(
            self.current_limmiter_resistors[1],
            self.rs485_out.diff_pair.p,
        )
        self.rs485_out.diff_pair.n.connect_via(self.gdt, self.rs485_out.diff_pair.p)

        # tvs connections
        # TODO: fix this, super ugly....
        diode_junction = self.clamping_diodes[0].anode
        diode_junction.connect(self.clamping_diodes[1].cathode)
        self.common_mode_filter.c_a[1].connect_via(self.tvs, diode_junction)
        self.common_mode_filter.c_b[1].connect_via(
            self.clamping_diodes[0], diode_junction
        )
        self.common_mode_filter.c_b[1].connect(self.clamping_diodes[1].cathode)
        self.clamping_diodes[1].anode.connect(diode_junction)

        # TODO: layout is only working when bbox is implemented or
        # when using specific components
