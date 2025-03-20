# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
This file contains a faebryk sample.
"""

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
from faebryk.exporters.pcb.layout.absolute import LayoutAbsolute
from faebryk.exporters.pcb.layout.typehierarchy import LayoutTypeHierarchy
from faebryk.libs.brightness import TypicalLuminousIntensity
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)

# App --------------------------------------------------------------------------


class App(Module):
    class PowerButton(Module):
        switch = L.f_field(F.Switch(F.Electrical))()
        power_in: F.ElectricPower
        power_switched: F.ElectricPower

        @L.rt_field
        def can_bridge(self):
            return F.can_bridge_defined(self.power_in, self.power_switched)

        def __preinit__(self):
            self.power_in.hv.connect_via(self.switch, self.power_switched.hv)
            self.power_in.lv.connect(self.power_switched.lv)
            self.power_in.connect_shallow(self.power_switched)

            self.switch.add(
                F.has_explicit_part.by_supplier(
                    "C318884",
                    pinmap={
                        "1": self.switch.unnamed[0],
                        "2": self.switch.unnamed[0],
                        "3": self.switch.unnamed[1],
                        "4": self.switch.unnamed[1],
                    },
                )
            )

    led: F.PoweredLED
    battery: F.Battery
    power_button: PowerButton

    @L.rt_field
    def transform_pcb(self):
        return F.has_layout_transform(transform_pcb)

    def __preinit__(self) -> None:
        self.led.power.connect_via(self.power_button, self.battery.power)

        # Parametrize
        self.led.led.color.constrain_subset(F.LED.Color.YELLOW)
        self.led.led.brightness.constrain_subset(
            TypicalLuminousIntensity.APPLICATION_LED_INDICATOR_INSIDE.value
        )

        # TODO: remove when we have a LED picker
        self.led.led.add(F.has_explicit_part.by_supplier("C965802"))
        self.led.led.forward_voltage.alias_is(2.4 * P.V)
        self.led.led.max_brightness.alias_is(435 * P.millicandela)
        self.led.led.max_current.alias_is(20 * P.mA)
        self.led.led.color.alias_is(F.LED.Color.YELLOW)

        # TODO remove when we have a battery picker
        self.battery.add(
            F.has_explicit_part.by_supplier(
                "C5239862",
                pinmap={
                    "1": self.battery.power.lv,
                    "2": self.battery.power.hv,
                },
            )
        )
        self.battery.power.voltage.alias_is(3 * P.V)


# PCB layout etc ---------------------------------------------------------------


def transform_pcb(transformer: PCB_Transformer):
    app = transformer.app
    assert isinstance(app, App)

    # Layout
    Point = F.has_pcb_position.Point
    L = F.has_pcb_position.layer_type

    layout = LayoutTypeHierarchy(
        layouts=[
            LayoutTypeHierarchy.Level(
                mod_type=F.PoweredLED,
                layout=LayoutAbsolute(Point((25, 5, 0, L.TOP_LAYER))),
                children_layout=LayoutTypeHierarchy(
                    layouts=[
                        LayoutTypeHierarchy.Level(
                            mod_type=F.LED, layout=LayoutAbsolute(Point((0, 0)))
                        ),
                        LayoutTypeHierarchy.Level(
                            mod_type=F.Resistor,
                            layout=LayoutAbsolute(Point((-5, 0, 180))),
                        ),
                    ]
                ),
            ),
            LayoutTypeHierarchy.Level(
                mod_type=F.Battery,
                layout=LayoutAbsolute(Point((25, 35, 0, L.TOP_LAYER))),
            ),
            LayoutTypeHierarchy.Level(
                mod_type=F.Switch(F.Electrical),
                layout=LayoutAbsolute(Point((35, 10, 45, L.TOP_LAYER))),
            ),
        ]
    )
    app.add(F.has_pcb_layout_defined(layout))
    app.add(F.has_pcb_position_defined(Point((50, 50, 0, L.NONE))))

    app.add(
        F.has_pcb_routing_strategy_greedy_direct_line(
            F.has_pcb_routing_strategy_greedy_direct_line.Topology.DIRECT
        )
    )

    transformer.set_pcb_outline_complex(
        geometry=transformer.create_rectangular_edgecut(
            width_mm=50,
            height_mm=50,
            origin=(50, 50),
        ),
        remove_existing_outline=True,
    )
