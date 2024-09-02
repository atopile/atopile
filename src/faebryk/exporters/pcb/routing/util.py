# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable, Sequence

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.node import Node
from faebryk.libs.geometry.basic import Geometry

if TYPE_CHECKING:
    from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer

# logging settings
logger = logging.getLogger(__name__)


# TODO remove
DEFAULT_TRACE_WIDTH = 0.1
DEFAULT_VIA_SIZE_DRILL = (0.45, 0.25)


class Path:
    @dataclass
    class Obj: ...

    @dataclass
    class Trace(Obj):
        width: float
        layer: int | str

    @dataclass
    class Line(Trace):
        start: Geometry.Point
        end: Geometry.Point

    @dataclass
    class Track(Trace):
        points: Sequence[Geometry.Point]

    @dataclass
    class Via(Obj):
        pos: Geometry.Point
        size_drill: tuple[float, float]

    @dataclass
    class Zone(Obj):
        layer: int | str
        polygon: list[Geometry.Point2D]

    def __init__(self, path: Sequence[Obj] | None = None) -> None:
        self.path = list(path or [])

    def abs_pos(self, vec: Geometry.Point):
        def _abs_pos_obj(obj: Path.Obj) -> Path.Obj:
            if isinstance(obj, Path.Trace):
                if isinstance(obj, Path.Track):
                    return Path.Track(
                        width=obj.width,
                        layer=obj.layer,
                        points=[Geometry.abs_pos(vec, p) for p in obj.points],
                    )
                elif isinstance(obj, Path.Line):
                    return Path.Line(
                        width=obj.width,
                        layer=obj.layer,
                        start=Geometry.abs_pos(vec, obj.start),
                        end=Geometry.abs_pos(vec, obj.end),
                    )
            elif isinstance(obj, Path.Via):
                return Path.Via(
                    pos=Geometry.abs_pos(vec, obj.pos),
                    size_drill=obj.size_drill,
                )
            raise NotImplementedError()

        self.path = [_abs_pos_obj(obj) for obj in self.path]

    def add(self, obj: Obj):
        self.path.append(obj)

    def __add__(self, other: "Path"):
        return Path(path=self.path + other.path)


class Route(Module):
    net_: F.Electrical
    pcb: ModuleInterface

    def __init__(
        self,
        pads: Iterable[F.Pad],
        path: Path | None = None,
    ):
        super().__init__()
        self.path = path or Path()
        self._pads = pads

    def __preinit__(self):
        for pad in self._pads:
            self.pcb.connect(pad.pcb)
            self.net_.connect(pad.net)

    def add(self, obj: Path.Obj):
        self.path.add(obj)

    @property
    def net(self):
        from faebryk.core.util import get_net

        net = get_net(self.net_)
        assert net
        return net


def apply_route_in_pcb(route: Route, transformer: "PCB_Transformer"):
    pcb_net = transformer.get_net(route.net)

    logger.debug(f"Insert tracks for net {pcb_net.name}, {pcb_net.number}, {route}")

    for obj in route.path.path:
        if isinstance(obj, Path.Trace):
            if isinstance(obj, Path.Track):
                path = [(round(p[0], 2), round(p[1], 2)) for p in obj.points]
            elif isinstance(obj, Path.Line):
                path = [
                    (round(obj.start[0], 2), round(obj.start[1], 2)),
                    (round(obj.end[0], 2), round(obj.end[1], 2)),
                ]

            layer_name = (
                obj.layer
                if isinstance(obj.layer, str)
                else transformer.get_layer_name(obj.layer)
            )

            transformer.insert_track(
                net_id=pcb_net.number,
                points=path,
                width=obj.width,
                layer=layer_name,
                arc=False,
            )

        elif isinstance(obj, Path.Via):
            coord = round(obj.pos[0], 2), round(obj.pos[1], 2)

            transformer.insert_via(
                net=pcb_net.name,
                coord=coord,
                size_drill=obj.size_drill,
            )

        elif isinstance(obj, Path.Zone):
            layer_name = (
                obj.layer
                if isinstance(obj.layer, str)
                else transformer.get_layer_name(obj.layer)
            )

            transformer.insert_zone(
                net=pcb_net,
                layer=layer_name,
                polygon=obj.polygon,
            )


def get_internal_nets_of_node(
    node: Node,
) -> dict[F.Net | None, Iterable[ModuleInterface]]:
    """
    Returns all Nets occuring (at least partially) within Node
    and returns for each of those the corresponding mifs
    For Nets returns all connected mifs
    """

    from faebryk.core.util import (
        get_all_nodes,
        get_connected_mifs,
        get_net,
    )
    from faebryk.libs.util import groupby

    if isinstance(node, F.Net):
        return {node: get_connected_mifs(node.part_of.connected)}

    mifs = {n for n in get_all_nodes(node) + [node] if isinstance(n, F.Electrical)}
    nets = groupby(mifs, lambda mif: get_net(mif))

    return nets


def get_pads_pos_of_mifs(mifs: Sequence[F.Electrical]):
    from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer

    return {
        pad_pos[0]: pad_pos[1]
        for mif in mifs
        for pad_pos in PCB_Transformer.get_pad_pos_any(mif)
    }


def group_pads_that_are_connected_already(
    pads: Iterable[F.Pad],
) -> list[set[F.Pad]]:
    out: list[set[F.Pad]] = []
    for pad in pads:
        for group in out:
            # Only need to check first, because transitively connected
            if pad.pcb.is_connected_to(next(iter(group)).pcb):
                group.add(pad)
                break
        else:
            out.append({pad})
    return out


def get_routes_of_pad(pad: F.Pad):
    from faebryk.core.util import get_parent_of_type

    return {
        route
        for mif in pad.pcb.get_direct_connections()
        if (route := get_parent_of_type(mif, Route))
    }
