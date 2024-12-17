# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
This file contains a faebryk sample.
"""

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.exporters.pcb.layout.extrude import LayoutExtrude
from faebryk.exporters.pcb.layout.typehierarchy import LayoutTypeHierarchy
from faebryk.exporters.pcb.routing.util import Path
from faebryk.libs.library import L
from faebryk.libs.units import P
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


class SubArray(Module):
    unnamed = L.list_field(2, F.Electrical)
    resistors = L.list_field(2, F.Resistor)

    def __init__(self, extrude_y: float):
        super().__init__()
        self._extrude_y = extrude_y

    def __preinit__(self):
        for resistor in self.resistors:
            resistor.resistance.constrain_subset(
                L.Range.from_center_rel(1000 * P.ohm, 0.05)
            )
            resistor.unnamed[0].connect(self.unnamed[0])
            resistor.unnamed[1].connect(self.unnamed[1])

    @L.rt_field
    def pcb_layout(self):
        return F.has_pcb_layout_defined(
            LayoutTypeHierarchy(
                layouts=[
                    LayoutTypeHierarchy.Level(
                        mod_type=F.Resistor,
                        layout=LayoutExtrude((0, self._extrude_y)),
                    ),
                ]
            )
        )

    pcb_routing_strategy = L.f_field(F.has_pcb_routing_strategy_greedy_direct_line)(
        F.has_pcb_routing_strategy_greedy_direct_line.Topology.DIRECT
    )

    @L.rt_field
    def pcb_routing_stategy_manual(self):
        return F.has_pcb_routing_strategy_manual(
            [
                (
                    [r.unnamed[1] for r in self.resistors],
                    Path(
                        [
                            Path.Track(
                                0.1,
                                "F.Cu",
                                [
                                    (0, 0),
                                    (2.5, 0),
                                    (2.5, self._extrude_y),
                                    (0, self._extrude_y),
                                ],
                            ),
                        ]
                    ),
                ),
                (
                    [r.unnamed[0] for r in self.resistors],
                    Path(
                        [
                            Path.Track(
                                0.1,
                                "F.Cu",
                                [
                                    (0, 0),
                                    (-2.5, 0),
                                    (-2.5, self._extrude_y),
                                    (0, self._extrude_y),
                                ],
                            ),
                        ]
                    ),
                ),
            ]
        )


class ResistorArray(Module):
    unnamed = L.list_field(2, F.Electrical)

    @L.rt_field
    def resistors(self):
        return times(self._count, lambda: SubArray(self._extrude_y[1]))

    def __init__(self, count: int, extrude_y: tuple[float, float]):
        super().__init__()

        self._count = count
        self._extrude_y = extrude_y

    def __preinit__(self):
        for resistor in self.resistors:
            resistor.unnamed[0].connect(self.unnamed[0])
            resistor.unnamed[1].connect(self.unnamed[1])

    @L.rt_field
    def pcb_layout(self):
        return F.has_pcb_layout_defined(
            LayoutTypeHierarchy(
                layouts=[
                    LayoutTypeHierarchy.Level(
                        mod_type=SubArray,
                        layout=LayoutExtrude((0, self._extrude_y[0])),
                    ),
                ]
            )
        )

    pcb_routing_strategy = L.f_field(F.has_pcb_routing_strategy_greedy_direct_line)(
        F.has_pcb_routing_strategy_greedy_direct_line.Topology.DIRECT
    )


class App(Module):
    @L.rt_field
    def arrays(self):
        return times(2, lambda: ResistorArray(self._count, self._extrude_y))

    def __init__(
        self, count: int = 2, extrude_y: tuple[float, float] = (15, 5)
    ) -> None:
        super().__init__()
        self._count = count
        self._extrude_y = extrude_y

    def __preinit__(self):
        self.arrays[0].unnamed[1].connect(self.arrays[1].unnamed[0])

    pcb_layout = L.f_field(F.has_pcb_layout_defined)(
        LayoutTypeHierarchy(
            layouts=[
                LayoutTypeHierarchy.Level(
                    mod_type=ResistorArray,
                    layout=LayoutExtrude((10, 0)),
                ),
            ]
        )
    )

    pcb_position = L.f_field(F.has_pcb_position_defined)(
        F.has_pcb_position.Point((20, 20, 0, F.has_pcb_position.layer_type.TOP_LAYER))
    )

    pcb_routing_strategy = L.f_field(F.has_pcb_routing_strategy_greedy_direct_line)(
        F.has_pcb_routing_strategy_greedy_direct_line.Topology.STAR
    )
