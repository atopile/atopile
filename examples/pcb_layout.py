# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
This file contains a faebryk sample.
"""

import logging
from pathlib import Path

import faebryk.library._F as F
import typer
from faebryk.core.core import Module
from faebryk.exporters.pcb.layout.absolute import LayoutAbsolute
from faebryk.exporters.pcb.layout.font import FontLayout
from faebryk.exporters.pcb.layout.typehierarchy import LayoutTypeHierarchy
from faebryk.library.has_pcb_layout_defined import has_pcb_layout_defined
from faebryk.library.has_pcb_position import has_pcb_position
from faebryk.library.has_pcb_position_defined import has_pcb_position_defined
from faebryk.libs.examples.buildutil import (
    apply_design_to_pcb,
)
from faebryk.libs.font import Font
from faebryk.libs.logging import setup_basic_logging
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


class LEDText(Module):
    def __init__(self) -> None:
        super().__init__()

        led_layout = FontLayout(
            font=Font(Path("/tmp/Minecraftia-Regular.ttf")),
            text="FAEBRYK",
            char_dimensions=(10, 14),
            resolution=(4.5, 1.1 * 2),
            kerning=5,
        )

        num_leds = led_layout.get_count()

        class _IFs(Module.IFS()):
            power = F.ElectricPower()

        self.IFs = _IFs(self)

        class _NODES(Module.NODES()):
            leds = times(
                num_leds,
                F.PoweredLED,
            )

        self.NODEs = _NODES(self)

        for led in self.NODEs.leds:
            led.IFs.power.connect(self.IFs.power)
            # Parametrize
            led.NODEs.led.PARAMs.color.merge(F.LED.Color.YELLOW)

        # Resistor relative to LED layout
        for led in self.NODEs.leds:
            led.add_trait(
                has_pcb_layout_defined(
                    LayoutTypeHierarchy(
                        layouts=[
                            LayoutTypeHierarchy.Level(
                                mod_type=F.LED,
                                layout=LayoutAbsolute(
                                    has_pcb_position.Point(
                                        (0, 0, 0, has_pcb_position.layer_type.NONE)
                                    )
                                ),
                            ),
                            LayoutTypeHierarchy.Level(
                                mod_type=F.Resistor,
                                layout=LayoutAbsolute(
                                    has_pcb_position.Point(
                                        (2, 0, 0, has_pcb_position.layer_type.NONE)
                                    )
                                ),
                            ),
                        ]
                    )
                )
            )

        led_layout.apply(*self.NODEs.leds)


class App(Module):
    def __init__(self) -> None:
        super().__init__()

        class _NODES(Module.NODES()):
            leds = LEDText()
            battery = F.Battery()

        self.NODEs = _NODES(self)

        self.NODEs.leds.IFs.power.connect(self.NODEs.battery.IFs.power)

        # Layout
        Point = has_pcb_position.Point
        L = has_pcb_position.layer_type

        layout = LayoutTypeHierarchy(
            layouts=[
                LayoutTypeHierarchy.Level(
                    mod_type=LEDText,
                    layout=LayoutAbsolute(Point((0, 0, 0, L.TOP_LAYER))),
                ),
                LayoutTypeHierarchy.Level(
                    mod_type=F.Battery,
                    layout=LayoutAbsolute(Point((0, 20, 0, L.BOTTOM_LAYER))),
                ),
            ]
        )
        self.add_trait(has_pcb_layout_defined(layout))
        self.add_trait(has_pcb_position_defined(Point((0, 0, 0, L.NONE))))


# Boilerplate -----------------------------------------------------------------


def main():
    logger.info("Building app")
    app = App()

    logger.info("Export")
    apply_design_to_pcb(app)


if __name__ == "__main__":
    setup_basic_logging()
    logger.info("Running example")

    typer.run(main)
