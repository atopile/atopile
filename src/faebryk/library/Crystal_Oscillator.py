# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P


class Crystal_Oscillator(Module):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    crystal: F.Crystal
    capacitors = L.list_field(2, F.Capacitor)
    current_limiting_resistor: F.Resistor

    xtal_if: F.XtalIF

    # ----------------------------------------
    #               parameters
    # ----------------------------------------
    # https://blog.adafruit.com/2012/01/24/choosing-the-right-crystal-and-caps-for-your-design/
    # http://www.st.com/internet/com/TECHNICAL_RESOURCES/TECHNICAL_LITERATURE/APPLICATION_NOTE/CD00221665.pdf
    _STRAY_CAPACITANCE = L.Range(1 * P.pF, 5 * P.pF)

    @L.rt_field
    def capacitance(self):
        return (self.crystal.load_capacitance - self._STRAY_CAPACITANCE) * 2

    def __preinit__(self):
        for cap in self.capacitors:
            cap.capacitance.alias_is(self.capacitance)

        self.current_limiting_resistor.allow_removal_if_zero()

        # ----------------------------------------
        #                traits
        # ----------------------------------------

        # ----------------------------------------
        #                aliases
        # ----------------------------------------

        # ----------------------------------------
        #                connections
        # ----------------------------------------
        self.crystal.gnd.connect(self.xtal_if.gnd)
        self.crystal.unnamed[0].connect_via(self.capacitors[0], self.xtal_if.gnd)
        self.crystal.unnamed[1].connect_via(self.capacitors[1], self.xtal_if.gnd)

        self.crystal.unnamed[0].connect_via(
            self.current_limiting_resistor, self.xtal_if.xout
        )
        self.crystal.unnamed[1].connect(self.xtal_if.xin)

    @L.rt_field
    def pcb_layout(self):
        from faebryk.exporters.pcb.layout.absolute import LayoutAbsolute
        from faebryk.exporters.pcb.layout.heuristic_decoupling import Params
        from faebryk.exporters.pcb.layout.next_to import LayoutNextTo
        from faebryk.exporters.pcb.layout.typehierarchy import LayoutTypeHierarchy

        Point = F.has_pcb_position.Point
        L = F.has_pcb_position.layer_type

        self.capacitors[0].add_trait(
            F.has_pcb_layout_defined(
                layout=LayoutNextTo(
                    target=self.crystal.unnamed[0],
                    params=Params(
                        distance_between_pad_edges=1.25, extra_rotation_of_footprint=90
                    ),
                )
            )
        )
        self.capacitors[1].add_trait(
            F.has_pcb_layout_defined(
                layout=LayoutNextTo(
                    target=self.crystal.unnamed[1],
                    params=Params(
                        distance_between_pad_edges=1.25, extra_rotation_of_footprint=90
                    ),
                )
            )
        )

        return F.has_pcb_layout_defined(
            LayoutTypeHierarchy(
                layouts=[
                    LayoutTypeHierarchy.Level(
                        mod_type=F.Crystal,
                        layout=LayoutAbsolute(
                            Point((0, 0, 0, L.NONE)),
                        ),
                    ),
                    # LayoutTypeHierarchy.Level(
                    #    mod_type=F.Capacitor,
                    #    layout=LayoutExtrude(
                    #        base=Point((-3, 0, 0, L.NONE)),
                    #        vector=(0, 6, 180),
                    #        dynamic_rotation=True,
                    #    ),
                    # ),
                    LayoutTypeHierarchy.Level(
                        mod_type=F.Resistor,
                        layout=LayoutAbsolute(Point((-3, -3, 0, L.NONE))),
                    ),
                ]
            ),
        )

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.xtal_if.xin, self.xtal_if.xout)
