# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Module
from faebryk.exporters.pcb.layout.absolute import LayoutAbsolute
from faebryk.exporters.pcb.layout.extrude import LayoutExtrude
from faebryk.exporters.pcb.layout.typehierarchy import LayoutTypeHierarchy
from faebryk.library.can_bridge_defined import can_bridge_defined
from faebryk.library.Capacitor import Capacitor
from faebryk.library.Common_Mode_Filter import Common_Mode_Filter
from faebryk.library.Constant import Constant
from faebryk.library.Diode import Diode
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.GDT import GDT
from faebryk.library.has_pcb_layout_defined import has_pcb_layout_defined
from faebryk.library.has_pcb_position import has_pcb_position
from faebryk.library.Range import Range
from faebryk.library.Resistor import Resistor
from faebryk.library.RS485 import RS485
from faebryk.library.TVS import TVS
from faebryk.libs.util import times

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

        class _NODEs(Module.NODES()):
            gdt = GDT()
            tvs = TVS()
            current_limmiter_resistors = times(2, Resistor)
            common_mode_filter = Common_Mode_Filter()
            gnd_couple_resistor = Resistor()
            gnd_couple_capacitor = Capacitor()
            clamping_diodes = times(2, Diode)
            if termination:
                termination_resistor = Resistor()
            if polarization:
                polarization_resistors = times(2, Resistor)

        self.NODEs = _NODEs(self)

        class _IFs(Module.IFS()):
            power = ElectricPower()
            rs485_in = RS485()
            rs485_out = RS485()
            earth = Electrical()

        self.IFs = _IFs(self)

        class _PARAMs(Module.PARAMS()): ...

        self.PARAMs = _PARAMs(self)

        if termination:
            self.NODEs.termination_resistor.PARAMs.resistance.merge(Constant(120))
            self.IFs.rs485_out.IFs.diff_pair.IFs.p.connect_via(
                self.NODEs.termination_resistor, self.IFs.rs485_out.IFs.diff_pair.IFs.n
            )
        if polarization:
            self.NODEs.polarization_resistors[0].PARAMs.resistance.merge(
                Range(380, 420)
            )
            self.NODEs.polarization_resistors[1].PARAMs.resistance.merge(
                Range(380, 420)
            )
            self.IFs.rs485_in.IFs.diff_pair.IFs.p.connect_via(
                self.NODEs.polarization_resistors[0], self.IFs.power.IFs.hv
            )
            self.IFs.rs485_in.IFs.diff_pair.IFs.n.connect_via(
                self.NODEs.polarization_resistors[1], self.IFs.power.IFs.lv
            )

        self.NODEs.current_limmiter_resistors[0].PARAMs.resistance.merge(Constant(2.7))
        # TODO: set power dissipation of resistor to 2W
        self.NODEs.current_limmiter_resistors[1].PARAMs.resistance.merge(Constant(2.7))
        # TODO: set power dissipation of resistor to 2W

        self.NODEs.gnd_couple_resistor.PARAMs.resistance.merge(Constant(1e6))
        self.NODEs.gnd_couple_capacitor.PARAMs.capacitance.merge(Constant(1e-6))
        self.NODEs.gnd_couple_capacitor.PARAMs.rated_voltage.merge(Constant(2e3))

        self.NODEs.tvs.PARAMs.reverse_working_voltage.merge(Constant(8.5))
        # self.NODEs.tvs.PARAMs.max_current.merge(Constant(41.7))
        # self.NODEs.tvs.PARAMs.forward_voltage.merge(Range(9.44, 10.40))

        for diode in self.NODEs.clamping_diodes:
            diode.PARAMs.forward_voltage.merge(Constant(1.1))
            diode.PARAMs.max_current.merge(Constant(1))
            diode.PARAMs.reverse_working_voltage.merge(Constant(1e3))

        # connections
        # earth connections
        self.IFs.power.IFs.lv.connect_via(
            self.NODEs.gnd_couple_resistor, self.IFs.earth
        )
        self.IFs.power.IFs.lv.connect_via(
            self.NODEs.gnd_couple_capacitor, self.IFs.earth
        )
        self.NODEs.gdt.IFs.common.connect(self.IFs.earth)

        # rs485_in connections
        self.IFs.rs485_in.IFs.diff_pair.IFs.p.connect(
            self.NODEs.common_mode_filter.IFs.c_a[0]
        )
        self.IFs.rs485_in.IFs.diff_pair.IFs.n.connect(
            self.NODEs.common_mode_filter.IFs.c_b[0]
        )

        # rs485_out connections
        self.NODEs.common_mode_filter.IFs.c_a[1].connect_via(
            self.NODEs.current_limmiter_resistors[0],
            self.IFs.rs485_out.IFs.diff_pair.IFs.p,
        )
        self.NODEs.common_mode_filter.IFs.c_b[1].connect_via(
            self.NODEs.current_limmiter_resistors[1],
            self.IFs.rs485_out.IFs.diff_pair.IFs.n,
        )
        self.IFs.rs485_out.IFs.diff_pair.IFs.n.connect_via(
            self.NODEs.gdt, self.IFs.rs485_out.IFs.diff_pair.IFs.p
        )

        # tvs connections
        # TODO: fix this, super ugly....
        diode_junction = self.NODEs.clamping_diodes[0].IFs.anode
        diode_junction.connect(self.NODEs.clamping_diodes[1].IFs.cathode)
        self.NODEs.common_mode_filter.IFs.c_a[1].connect_via(
            self.NODEs.tvs, diode_junction
        )
        self.NODEs.common_mode_filter.IFs.c_b[1].connect_via(
            self.NODEs.clamping_diodes[0], diode_junction
        )
        self.NODEs.common_mode_filter.IFs.c_b[1].connect(
            self.NODEs.clamping_diodes[1].IFs.cathode
        )
        self.NODEs.clamping_diodes[1].IFs.anode.connect(diode_junction)

        self.add_trait(can_bridge_defined(self.IFs.rs485_in, self.IFs.rs485_out))

        # TODO: layout is only working when bbox is implemented or
        # when using specific components

        # PCB layout
        Point = has_pcb_position.Point
        L = has_pcb_position.layer_type
        self.NODEs.gnd_couple_resistor.add_trait(
            has_pcb_layout_defined(
                LayoutAbsolute(
                    Point((-10, 0, 90, L.NONE)),
                )
            )
        )
        self.add_trait(
            has_pcb_layout_defined(
                LayoutTypeHierarchy(
                    layouts=[
                        LayoutTypeHierarchy.Level(
                            mod_type=GDT,
                            layout=LayoutAbsolute(
                                Point((0, 0, 0, L.NONE)),
                            ),
                        ),
                        # TODO: fix
                        # LayoutTypeHierarchy.Level(
                        #    mod_type=TVS,
                        #    layout=LayoutAbsolute(
                        #        Point((0, 11, 0, L.NONE)),
                        #    ),
                        # ),
                        LayoutTypeHierarchy.Level(
                            mod_type=Common_Mode_Filter,
                            layout=LayoutAbsolute(
                                Point((0, 25.5, 90, L.NONE)),
                            ),
                        ),
                        LayoutTypeHierarchy.Level(
                            mod_type=Diode,
                            layout=LayoutExtrude(
                                base=Point((0, 14.5, 0, L.NONE)),
                                vector=(0, 3.5, 0),
                            ),
                        ),
                        LayoutTypeHierarchy.Level(
                            mod_type=Resistor,
                            layout=LayoutExtrude(
                                base=Point((-2, 8, 90, L.NONE)),
                                vector=(0, 4, 0),
                            ),
                        ),
                        LayoutTypeHierarchy.Level(
                            mod_type=Capacitor,
                            layout=LayoutAbsolute(
                                Point((10, 0, 90, L.NONE)),
                            ),
                        ),
                    ]
                ),
            )
        )
