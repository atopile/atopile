# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
This file contains a faebryk sample.
"""

import logging

import faebryk.library._F as F
import typer
from faebryk.core.core import Module
from faebryk.exporters.pcb.layout.extrude import LayoutExtrude
from faebryk.exporters.pcb.layout.typehierarchy import LayoutTypeHierarchy
from faebryk.exporters.pcb.routing.util import Path
from faebryk.library.Electrical import Electrical
from faebryk.library.has_pcb_layout_defined import has_pcb_layout_defined
from faebryk.library.has_pcb_position import has_pcb_position
from faebryk.library.has_pcb_position_defined import has_pcb_position_defined
from faebryk.library.has_pcb_routing_strategy_greedy_direct_line import (
    has_pcb_routing_strategy_greedy_direct_line,
)
from faebryk.library.has_pcb_routing_strategy_manual import (
    has_pcb_routing_strategy_manual,
)
from faebryk.libs.examples.buildutil import (
    apply_design_to_pcb,
)
from faebryk.libs.logging import setup_basic_logging
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


class SubArray(Module):
    def __init__(self, extrude_y: float):
        super().__init__()

        class _IFs(Module.IFS()):
            unnamed = times(2, Electrical)

        self.IFs = _IFs(self)

        class _NODES(Module.NODES()):
            resistors = times(2, F.Resistor)

        self.NODEs = _NODES(self)

        for resistor in self.NODEs.resistors:
            resistor.PARAMs.resistance.merge(F.Constant(1000))
            resistor.IFs.unnamed[0].connect(self.IFs.unnamed[0])
            resistor.IFs.unnamed[1].connect(self.IFs.unnamed[1])

        self.add_trait(
            has_pcb_layout_defined(
                LayoutTypeHierarchy(
                    layouts=[
                        LayoutTypeHierarchy.Level(
                            mod_type=F.Resistor,
                            layout=LayoutExtrude((0, extrude_y)),
                        ),
                    ]
                )
            )
        )

        self.add_trait(
            has_pcb_routing_strategy_greedy_direct_line(
                has_pcb_routing_strategy_greedy_direct_line.Topology.DIRECT
            )
        )

        self.add_trait(
            has_pcb_routing_strategy_manual(
                [
                    (
                        [r.IFs.unnamed[1] for r in self.NODEs.resistors],
                        Path(
                            [
                                Path.Track(
                                    0.1,
                                    "F.Cu",
                                    [
                                        (0, 0),
                                        (2.5, 0),
                                        (2.5, extrude_y),
                                        (0, extrude_y),
                                    ],
                                ),
                            ]
                        ),
                    ),
                    (
                        [r.IFs.unnamed[0] for r in self.NODEs.resistors],
                        Path(
                            [
                                Path.Track(
                                    0.1,
                                    "F.Cu",
                                    [
                                        (0, 0),
                                        (-2.5, 0),
                                        (-2.5, extrude_y),
                                        (0, extrude_y),
                                    ],
                                ),
                            ]
                        ),
                    ),
                ]
            )
        )


class ResistorArray(Module):
    def __init__(self, count: int, extrude_y: tuple[float, float]):
        super().__init__()

        class _IFs(Module.IFS()):
            unnamed = times(2, Electrical)

        self.IFs = _IFs(self)

        class _NODES(Module.NODES()):
            resistors = times(count, lambda: SubArray(extrude_y[1]))

        self.NODEs = _NODES(self)

        for resistor in self.NODEs.resistors:
            resistor.IFs.unnamed[0].connect(self.IFs.unnamed[0])
            resistor.IFs.unnamed[1].connect(self.IFs.unnamed[1])

        self.add_trait(
            has_pcb_layout_defined(
                LayoutTypeHierarchy(
                    layouts=[
                        LayoutTypeHierarchy.Level(
                            mod_type=SubArray,
                            layout=LayoutExtrude((0, extrude_y[0])),
                        ),
                    ]
                )
            )
        )

        self.add_trait(
            has_pcb_routing_strategy_greedy_direct_line(
                has_pcb_routing_strategy_greedy_direct_line.Topology.DIRECT
            )
        )


class App(Module):
    def __init__(self, count: int, extrude_y: tuple[float, float]) -> None:
        super().__init__()

        class _NODES(Module.NODES()):
            arrays = times(2, lambda: ResistorArray(count, extrude_y))

        self.NODEs = _NODES(self)

        self.NODEs.arrays[0].IFs.unnamed[1].connect(self.NODEs.arrays[1].IFs.unnamed[0])

        # Layout
        Point = has_pcb_position.Point
        L = has_pcb_position.layer_type

        layout = LayoutTypeHierarchy(
            layouts=[
                LayoutTypeHierarchy.Level(
                    mod_type=ResistorArray,
                    layout=LayoutExtrude((10, 0)),
                ),
            ]
        )
        self.add_trait(has_pcb_layout_defined(layout))
        self.add_trait(has_pcb_position_defined(Point((20, 20, 0, L.TOP_LAYER))))

        self.add_trait(
            has_pcb_routing_strategy_greedy_direct_line(
                has_pcb_routing_strategy_greedy_direct_line.Topology.STAR
            )
        )


# Boilerplate -----------------------------------------------------------------


def main(count: int = 2, extrude_y: tuple[float, float] = (15, 5)):
    logger.info("Building app")
    app = App(count, extrude_y)

    logger.info("Export")
    apply_design_to_pcb(app)


if __name__ == "__main__":
    setup_basic_logging()
    logger.info("Running example")

    typer.run(main)
