# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import math
from dataclasses import dataclass
from enum import IntEnum

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.node import Node
from faebryk.core.trait import TraitNotFound
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
from faebryk.exporters.pcb.layout.layout import Layout
from faebryk.libs.kicad.fileformats_latest import (
    C_kicad_pcb_file,
    C_wh,
)
from faebryk.libs.util import KeyErrorNotFound, find, not_none

logger = logging.getLogger(__name__)


KFootprint = C_kicad_pcb_file.C_kicad_pcb.C_pcb_footprint
KPad = KFootprint.C_pad

# TODO move all those helpers and make them more general and precise


@dataclass
class Params:
    distance_between_pad_edges: float = 1
    extra_rotation_of_footprint: float = 0


class Side(IntEnum):
    Right = 0
    Bottom = 90
    Left = 180
    Top = 270

    def rot(self, angle=90):
        return type(self)((self + angle) % 360)

    def rot_vector(self, vec: tuple[float, float]):
        x, y = vec
        if self == Side.Right:
            return x, y
        elif self == Side.Bottom:
            return -y, x
        elif self == Side.Left:
            return -x, -y
        elif self == Side.Top:
            return y, -x
        else:
            assert False


def _get_pad_side(fp: KFootprint, pad: KPad) -> Side:
    # TODO this is just a heuristic
    # we better need to check for the bbox

    # relative to fp center
    hyst = 1.1
    right_nleft = Side.Right if pad.at.x > 0 else Side.Left
    bottom_ntop = Side.Bottom if pad.at.y > 0 else Side.Top
    if abs(pad.at.x) > abs(pad.at.y) * hyst:
        pos_side = [right_nleft]
    elif abs(pad.at.y) > abs(pad.at.x) * hyst:
        pos_side = [bottom_ntop]
    else:
        # corner
        if abs(pad.at.x) > abs(pad.at.y):
            pos_side = [right_nleft, bottom_ntop]
        else:
            pos_side = [bottom_ntop, right_nleft]

    # pad size as heuristic
    rot = (fp.at.r - pad.at.r) % 360
    assert rot in (0, 90, 180, 270)
    assert pad.size.h is not None
    if (pad.size.h > pad.size.w) == (rot in (0, 180)):
        pos_rot = {Side.Top, Side.Bottom}
    else:
        pos_rot = {Side.Right, Side.Left}

    match = set(pos_side) & pos_rot
    if match:
        assert len(match) == 1
        return next(iter(match))

    logger.warning(
        f"Uncertain about pad position of `{fp.name}"
        f"|{fp.propertys['Reference'].value}.{pad.name}`: "
        f"Heuristic at: `{pos_side}`, "
        f"Heuristic size: `{pos_rot} ||| {rot=} {pad.at=} {pad.size=}`",
        extra={"markdown": True},
    )
    return pos_side[0]


type V2D = tuple[float, float]


def _vec_pad_center_to_edge(size: C_wh, side: Side):
    assert size.h is not None
    if side == Side.Top:
        return 0, 0 - size.h / 2
    elif side == Side.Bottom:
        return 0, 0 + size.h / 2
    elif side == Side.Left:
        return 0 - size.w / 2, 0
    else:
        return 0 + size.w / 2, 0


def _next_to_pad(
    fp: KFootprint, spad: KPad, dfp: KFootprint, dpad: KPad, params: Params
):
    # TODO determine distance based on pads & footprint size
    distance = params.distance_between_pad_edges
    dfp_bbox = PCB_Transformer.get_footprint_silkscreen_bbox(dfp)
    assert dfp_bbox is not None
    dfp_w = dfp_bbox[1][0] - dfp_bbox[0][0]

    # heuristic
    # TODO use pad pitch instead
    assert spad.size.h
    assert dpad.size.h
    hs = spad.size.h
    hd = dpad.size.h
    # TODO rotation
    if hs < hd:
        no = fp.pads.index(spad)
        tol = 1.1
        extra_distance = dfp_w * tol
        steps = int(math.ceil(hd / hs))
        distance += (no % steps) * extra_distance

    def _add(v1: V2D, v2: V2D) -> V2D:
        return v1[0] + v2[0], v1[1] + v2[1]

    def _sub(v1: V2D, v2: V2D) -> V2D:
        return v1[0] - v2[0], v1[1] - v2[1]

    side = _get_pad_side(fp, spad)

    # rotate fp to let pads face each other (+extra rotation)
    dside = _get_pad_side(dfp, dpad)
    fp_rot_rel_to_source = (
        side.rot() - dside.rot() - 180 + params.extra_rotation_of_footprint
    ) % 360

    vec_distance_directed = side.rot_vector((distance, 0))
    vec_distance_from_pad_center = _add(vec_distance_directed, (spad.at.x, spad.at.y))

    # make vec distance between edges instead of center
    _spad_edge_vec = _vec_pad_center_to_edge(spad.size, side)
    _dpad_edge_vec = Side(fp_rot_rel_to_source).rot_vector(
        _vec_pad_center_to_edge(dpad.size, dside)
    )
    vec_distance_from_pad_edge = _sub(
        _add(vec_distance_from_pad_center, _spad_edge_vec), _dpad_edge_vec
    )

    # get vector to fp center (instead of pad center)
    _vec_pad_to_fp = Side(fp_rot_rel_to_source).rot_vector((-dpad.at.x, -dpad.at.y))
    vec_to_fp_center = _add(vec_distance_from_pad_edge, _vec_pad_to_fp)

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Next to pad: {fp.name}|{fp.propertys['Reference'].value}.{spad.name}"
            f" with {dfp.name}|{dfp.propertys['Reference'].value}.{dpad.name}:"
            f"\n     {fp.at=}"
            f"\n     {spad.at=} | {spad.size=}"
            f"\n     {dpad.at=} | {dpad.size=}"
            f"\n     {side=}"
            f"\n     {dside=}"
            f"\n     {fp_rot_rel_to_source=}"
            f"\n     {vec_distance_directed=}"
            f"\n     {vec_distance_from_pad_center=}"
            f"\n     {_spad_edge_vec=} | {_dpad_edge_vec=}"
            f"\n     {vec_distance_from_pad_edge=}"
            f"\n     {vec_to_fp_center=}"
        )

    # in fp system clockwise, in pcb counter clockwise
    rot_pcb_coord_system = (-fp_rot_rel_to_source) % 360

    return (*vec_to_fp_center, rot_pcb_coord_system)


def place_next_to_pad(
    module: Module,
    pad: F.Pad,
    params: Params,
):
    kfp, kpad = pad.get_trait(PCB_Transformer.has_linked_kicad_pad).get_pad()
    if len(kpad) != 1:
        raise NotImplementedError()
    kpad = kpad[0]

    nfp = module.get_trait(F.has_footprint).get_footprint()
    npad = find(
        nfp.get_children(direct_only=True, types=F.Pad),
        lambda p: p.net.is_connected_to(pad.net),
    )
    nkfp, nkpad = npad.get_trait(PCB_Transformer.has_linked_kicad_pad).get_pad()
    if len(nkpad) != 1:
        raise NotImplementedError()
    nkpad = nkpad[0]

    pos = _next_to_pad(kfp, kpad, nkfp, nkpad, params)

    module.add(
        F.has_pcb_position_defined_relative_to_parent(
            (
                *pos,
                F.has_pcb_position.layer_type.NONE,
            )
        )
    )


def place_next_to(
    parent_intf: F.Electrical,
    module: Module,
    params: Params,
    route: bool = False,
):
    try:
        pads_intf = parent_intf.get_trait(F.has_linked_pad).get_pads()
    except TraitNotFound:
        logger.warning(
            f"No linked pads found for interface {parent_intf}."
            " Make sure the footprint is properly attached."
            " And that the component is attached "
            "to an interface of a module with a footprint."
        )
        return

    if len(pads_intf) == 0:
        raise KeyErrorNotFound()

    children = module.get_children_modules(
        direct_only=False,
        types=Module,
        f_filter=lambda m: m.has_trait(F.has_footprint)
        and not m.has_trait(F.has_pcb_position),
        include_root=True,
    )

    for parent_pad, child in zip(pads_intf, children):
        intf = find(
            child.get_children(direct_only=True, types=F.Electrical),
            lambda x: x.is_connected_to(parent_intf),
        )

        logger.debug(f"Placing {intf} next to {parent_pad}")
        place_next_to_pad(child, parent_pad, params)

        if route:
            intf.add(
                F.has_pcb_routing_strategy_greedy_direct_line(extra_pads=[parent_pad])
            )


class LayoutHeuristicElectricalClosenessDecouplingCaps(Layout):
    Parameters = Params

    def __init__(self, params: Params | None = None):
        super().__init__()
        self._params = params or Params()

    def apply(self, *node: Node):
        # Remove nodes that have a position defined
        node = tuple(n for n in node if not n.has_trait(F.has_pcb_position))

        for n in node:
            assert isinstance(n, F.Capacitor)
            power = not_none(n.get_parent_of_type(F.ElectricPower))

            place_next_to(power.hv, n, route=True, params=self._params)

    @staticmethod
    def find_module_candidates(node: Node):
        return Module.get_children_modules(
            node,
            direct_only=False,
            types=F.Capacitor,
            f_filter=lambda c: c.get_parent_of_type(
                F.ElectricPower, direct_only=True, include_root=False
            )
            is not None,
        )

    @classmethod
    def add_to_all_suitable_modules(cls, node: Node, params: Params | None = None):
        layout = cls(params)
        candidates = cls.find_module_candidates(node)
        for c in candidates:
            logger.debug(f"Adding {cls.__name__} to {c}")
            c.add(F.has_pcb_layout_defined(layout))
        return candidates
